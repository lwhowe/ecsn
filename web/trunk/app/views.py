import bcrypt
import socket
import urllib2
import logging
from copy import deepcopy
from flask import g, flash, url_for, redirect, request, session, render_template, jsonify
from flask_login import current_user, login_user, logout_user, login_required
from lxml.html import parse, submit_form, tostring
from . import app, db
from forms import LoginForm, ConfigForm, ProjectForm, ControllerForm, HypervisorForm, MachineForm
from forms import IdleOccurrenceForm, IdleSchedulerForm
from models import User, Site, BusinessUnit, ProductFamily, Project, Machine, Controller, Hypervisor
from models import DataState, Tasks
from libs import lib
from libs.lib import StandalonePower, VirtualPower

log = logging.getLogger(__name__)


@app.before_request
def before_request():
    g.user = current_user

    # for script use and query only once throughout users session
    if 'site_dict' not in session:
        session['site_dict'] = dict()
        for site in Site.query.all():
            session['site_dict'][site.id] = dict(name=site.name, description=site.description)
    elif 'unit_dict' not in session:
        session['unit_dict'] = dict()
        for unit in BusinessUnit.query.all():
            session['unit_dict'][unit.id] = dict(name=unit.name, description=unit.description)
    elif 'family_dict' not in session:
        session['family_dict'] = dict()
        for family in ProductFamily.query.all():
            session['family_dict'][family.id] = dict(name=family.name, description=family.description)


@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html', userdict=dict(title='Error {}'.format(error))), 404


@app.route('/index')
@login_required
def redirect_index():
    return redirect(url_for('index'))


@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    userdict = dict(title='ECSN')
    if request.method == 'POST':
        if request.form['mtype'] == 'standalone-cimc' or request.form['mtype'] == 'virtual-cimc':
            obj = Machine.query.filter_by(host=request.form['mname']).join(Controller)\
                .add_columns(Controller.ip, Controller.user, Controller.password)\
                .filter(Machine.cimc_id == Controller.id).first()
            if obj:
                ip_address, username, password = obj[1], obj[2], obj[3]
                try:
                    xml_cookie = StandalonePower.controller_login(ip_address, username, password)
                    if request.form['state'].strip() in ('up', 'soft-shut-down'):
                        status = StandalonePower.controller_status(ip_address, xml_cookie)
                        if request.form['state'] == 'up' and status == 'on':
                            obj[0].state = 1  # set machine state to on
                            db.session.commit()
                            return jsonify(status='error', message='Error: CIMC already powered on')
                        elif request.form['state'] == 'soft-shut-down' and status == 'off':
                            obj[0].state = 0  # set machine state to off
                            db.session.commit()
                            return jsonify(status='error', message='Error: CIMC already powered off')
                        StandalonePower.controller_power(ip_address, xml_cookie, request.form['state'].strip())
                        if request.form['state'] == 'up':
                            obj[0].state = 1  # set machine state to on
                            db.session.commit()
                        elif request.form['state'] == 'soft-shut-down':
                            obj[0].state = 0  # set machine state to off
                            db.session.commit()
                    else:
                        message = "Error: '{}' state value not recognize".format(request.form['state'].strip())
                        return jsonify(status='error', message=message)
                    StandalonePower.controller_logout(ip_address, xml_cookie)

                except urllib2.URLError, e:
                    return jsonify(status='error', message='Error: {}'.format(e.reason))
                except ValueError, e:
                    return jsonify(status='error', message='Error: {}'.format(e))
                except Exception, e:
                    template = "An exception of type {0} occured.\nError: {1!r}"
                    message = template.format(type(e).__name__, e.args)
                    return jsonify(status='error', message=message)
            return jsonify(status='success', message='')
        elif request.form['mtype'] == 'virtual-host':
            obj = Machine.query.filter_by(host=request.form['mname']).join(Hypervisor)\
                .add_columns(Hypervisor.ip, Hypervisor.user, Hypervisor.password)\
                .filter(Machine.esxi_id == Hypervisor.id).first()
            if obj:
                ip_address, username, password = obj[1], obj[2], obj[3]
                try:
                    ssh = VirtualPower.ssh_connect(ip_address, username, password)
                    stdout, stderr = VirtualPower.ssh_run_readlines(ssh, 'vim-cmd vmsvc/getallvms')
                    for line in stdout:
                        if obj[0].vm_name in line:
                            vmid = line.strip().split()[0]
                            break
                    else:
                        return jsonify(status='error', message='Error: vmid not found due to incorrect VM Name')

                    # check if already powered on or off
                    stdout, stderr = VirtualPower.ssh_run_read(ssh, 'vim-cmd vmsvc/power.getstate {}'.format(vmid))
                    if request.form['state'] == 'up' and 'Powered on' in stdout:
                        obj[0].state = 1  # set machine state to on
                        db.session.commit()
                        return jsonify(status='error', message='Error: VM already powered on')
                    elif request.form['state'] == 'soft-shut-down' and 'Powered off' in stdout:
                        obj[0].state = 0  # set machine state to off
                        db.session.commit()
                        return jsonify(status='error', message='Error: VM already powered off')
                    else:
                        if request.form['state'] == 'up':
                            VirtualPower.ssh_run_read(ssh, 'vim-cmd vmsvc/power.on {}'.format(vmid))
                            obj[0].state = 1  # set machine state to on
                            db.session.commit()
                        elif request.form['state'] == 'soft-shut-down':
                            # need vmware tools to enable graceful shutdown
                            stdout, stderr = VirtualPower.ssh_run_readlines(ssh, 'vim-cmd vmsvc/get.guest {}'
                                                                            .format(vmid))
                            for line in stdout:
                                if 'toolsStatus =' in line and 'toolsNotInstalled' in line \
                                        and request.form['state'] == 'soft-shut-down':
                                    return jsonify(status='error', message='Error: VMware Tools not installed')

                            VirtualPower.ssh_run_read(ssh, 'vim-cmd vmsvc/power.shutdown {}'.format(vmid))
                            obj[0].state = 0  # set machine state to off
                            db.session.commit()
                    ssh.close()
                except ValueError, e:
                    return jsonify(status='error', message='Error: {}'.format(e))
                except IOError, e:
                    return jsonify(status='error', message='Error: {}'.format(e))
                except socket.timeout, e:
                    return jsonify(status='error', message='Error: {}'.format(e))
            return jsonify(status='success', message='')
        elif request.form['mtype'] == 'virtual-esxi':
            obj = Machine.query.filter_by(host=request.form['mname']).join(Hypervisor) \
                .add_columns(Hypervisor.ip, Hypervisor.user, Hypervisor.password) \
                .filter(Machine.esxi_id == Hypervisor.id).first()
            if obj:
                ip_address, username, password = obj[1], obj[2], obj[3]
                try:
                    ssh = VirtualPower.ssh_connect(ip_address, username, password)
                    VirtualPower.ssh_run_read(ssh, 'poweroff')
                    ssh.close()
                except ValueError, e:
                    return jsonify(status='error', message='Error: {}'.format(e))
                except IOError, e:
                    return jsonify(status='error', message='Error: {}'.format(e))
                except socket.timeout, e:
                    return jsonify(status='error', message='Error: {}'.format(e))
            return jsonify(status='success', message='')

    # create a controller dict
    controller_ip = dict()
    hold = db.session.query(Controller.id, Controller.ip).all()
    for (uid, ip_address) in hold:
        controller_ip[uid] = ip_address
    userdict.update(controller_dict=controller_ip)

    # create a hypervisor dict
    hypervisor_ip = dict()
    hold = db.session.query(Hypervisor.id, Hypervisor.ip).all()
    for (uid, ip_address) in hold:
        hypervisor_ip[uid] = ip_address
    userdict.update(hypervisor_dict=hypervisor_ip)

    # create the standalone and virtual machine dict
    machines = Machine.query.filter_by(type='virtual', date_deleted=None).all()
    virtual_dict = dict()
    if machines:
        for m in machines:
            if m.esxi_id:
                if not virtual_dict.get(str(m.esxi_id)):
                    virtual_dict[str(m.esxi_id)] = [m]
                else:
                    virtual_dict[str(m.esxi_id)].append(m)
            else:
                virtual_dict[str(m.id)] = m
    userdict.update(virtual_dict=virtual_dict)
    userdict.update(standalone_list=Machine.query.filter_by(type='standalone', date_deleted=None).all())

    # use for dashboard summary
    project_dict = Project.query.all()
    project_stat = dict()
    for project in project_dict:
        project_stat[project.id] = dict(total=0, active=0, idle=0, on=0, off=0)
        machines = Machine.query.filter_by(project_id=project.id, date_deleted=None).all()
        for server in machines:
            # refer to state_dict and status_dict from Machine class in models
            if server.state == 1:
                project_stat[project.id]['on'] += 1
            elif server.state == 0 or server.state == 2:
                project_stat[project.id]['off'] += 1
            if server.status == 1:
                project_stat[project.id]['active'] += 1
            elif server.status == 2:
                project_stat[project.id]['idle'] += 1
    userdict.update(project_stat=project_stat)
    userdict.update(project_dict=project_dict)
    userdict.update(site_dict=session.get('site_dict', dict()))
    userdict.update(unit_dict=session.get('unit_dict', dict()))
    userdict.update(family_dict=session.get('family_dict', dict()))

    return render_template('index.html', userdict=userdict)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if g.user and g.user.is_authenticated:
        return redirect(request.args.get('next') or url_for('index'))

    userdict = dict(title='ECSN | Login')
    userdict.update(login_form=LoginForm(prefix='login'))

    if userdict['login_form'].validate_on_submit():
        try:
            page = parse(urllib2.urlopen('https://pwreset.cisco.com/')).getroot()
            form = page.forms[0]
            form.fields['USER_IDENT'] = userdict['login_form'].username.data
            form.fields['_MYPW'] = userdict['login_form'].password.data
            next_page = parse(submit_form(form)).getroot()
            result = tostring(next_page)

            if 'Change passwords' in result and 'Update security questions' in result:
                obj = User.query.filter_by(username=userdict['login_form'].username.data).first()
                if not obj:
                    # First time user log in with CEC acc
                    password = b"{}".format(userdict['login_form'].password.data)  # convert to bytes
                    hashed_password = bcrypt.hashpw(password, bcrypt.gensalt())  # hashing with bcrypt
                    hold = User(userdict['login_form'].username.data, hashed_password, 'CEC',
                                email=userdict['login_form'].username.data+'@cisco.com')
                    db.session.add(hold)
                    db.session.commit()
                    login_user(hold, remember=userdict['login_form'].remember_me.data)
                    return redirect(request.args.get('next') or url_for('index'))

                password = b"{}".format(userdict['login_form'].password.data)  # convert to bytes
                obj_password = b"{}".format(obj.password)  # convert to bytes
                if obj.username == userdict['login_form'].username.data:
                    if bcrypt.checkpw(password, obj_password):
                        login_user(obj, remember=userdict['login_form'].remember_me.data)
                    else:
                        # Detected different CEC password and update the User.password
                        hashed_password = bcrypt.hashpw(password, bcrypt.gensalt())  # hashing with bcrypt
                        obj.password = hashed_password
                        db.session.commit()
                        login_user(obj, remember=userdict['login_form'].remember_me.data)
                    log.info("User '{}' logged in and authenticated from pwreset.cisco.com".format(obj.username))
                return redirect(request.args.get('next') or url_for('index'))
            elif 'locked out of the system' in result:
                flash('Invalid Username or Password.')
                flash('You are locked out of the system due to too many invalid login attempts.')
                log.info("User '{}' locked out of the system due to too many invalid login attempts"
                         .format(userdict['login_form'].username.data))
                return redirect(url_for('login'))
            else:
                flash('Invalid Username or Password.')
                return redirect(url_for('login'))
        except urllib2.URLError:
            # https://pwreset.cisco.com/ is unreachable due to page down or network issue
            obj = User.query.filter_by(username=userdict['login_form'].username.data).first()
            if obj:
                password = b"{}".format(userdict['login_form'].password.data)  # convert to bytes
                obj_password = b"{}".format(obj.password)  # convert to bytes
                if obj.username == userdict['login_form'].username.data and bcrypt.checkpw(password, obj_password):
                    login_user(obj, remember=userdict['login_form'].remember_me.data)
                    log.info("User '{}' logged in and offline authenticated".format(obj.username))
                    return redirect(request.args.get('next') or url_for('index'))
                else:
                    flash('Invalid Username or Password.')
                    return redirect(url_for('login'))

    return render_template('login.html', userdict=userdict)


@app.route('/logout')
def logout():
    log.info("User '{}' logged out".format(g.user.username))
    del g.user
    session.clear()
    logout_user()
    return redirect(url_for('index'))


@app.route('/config', methods=['GET', 'POST'])
@login_required
def config():
    userdict = dict()
    config_form = ConfigForm(request)

    if request.args.get('m') == 'site':
        if request.method == 'POST':
            if config_form.validate():
                config_form.add_entry(request.args.get('m'))
                return redirect(request.url)
        userdict.update(title='ECSN | Site Config')
        userdict.update(h1='Site Configuration')
        userdict.update(config_list=Site.query.all())
    elif request.args.get('m') == 'unit':
        if request.method == 'POST':
            if config_form.validate():
                config_form.add_entry(request.args.get('m'))
                return redirect(request.url)
        userdict.update(title='ECSN | Business Unit Config')
        userdict.update(h1='Business Unit Configuration')
        userdict.update(config_list=BusinessUnit.query.all())
    elif request.args.get('m') == 'family':
        if request.method == 'POST':
            if config_form.validate():
                config_form.add_entry(request.args.get('m'))
                return redirect(request.url)
        userdict.update(title='ECSN | Product Family Config')
        userdict.update(h1='Product Family Configuration')
        userdict.update(config_list=ProductFamily.query.all())
    elif request.args.get('m') == 'project':
        project_form = ProjectForm()
        if request.method == 'POST':
            if project_form.validate():
                project_form.add_entry()
                return redirect(request.url)

        userdict.update(title='ECSN | Project Config')
        userdict.update(project_form=project_form)
        userdict.update(project_list=Project.query.all())
        userdict.update(site_dict=session['site_dict'])
        userdict.update(unit_dict=session['unit_dict'])
        userdict.update(family_dict=session['family_dict'])
        return render_template('project.html', userdict=userdict)
    else:
        return redirect(404)

    userdict.update(config_form=config_form)
    return render_template('config.html', userdict=userdict)


@app.route('/host', methods=['GET', 'POST'])
@login_required
def host():
    userdict = dict()

    if request.args.get('m') == 'controller':
        cimc_form = ControllerForm(prefix='cimc')
        if request.method == 'POST':
            if cimc_form.validate():
                cimc_form.add_entry()
                return redirect(request.url)

        userdict.update(title='ECSN | CIMC Config')
        userdict.update(cimc_form=cimc_form)
        userdict.update(cimc_list=Controller.query.all())
        return render_template('controller.html', userdict=userdict)
    elif request.args.get('m') == 'hypervisor':
        esxi_form = HypervisorForm(prefix='esxi')
        if request.method == 'POST':
            if esxi_form.validate():
                esxi_form.add_entry()
                return redirect(request.url)

        userdict.update(title='ECSN | ESXi Config')
        userdict.update(esxi_form=esxi_form)
        userdict.update(esxi_list=Hypervisor.query.all())
        return render_template('hypervisor.html', userdict=userdict)
    else:
        return redirect(404)


@app.route('/machine', methods=['GET', 'POST'])
@login_required
def machine():
    userdict = dict()
    machine_form = MachineForm(request, prefix='cfg')

    if request.args.get('m') == 'standalone':
        machine_form.cimc.choices = machine_form.get_cimc_choices('standalone')
        if request.args.get('edit'):
            mach = Machine.query.filter_by(host=request.args['edit'], date_deleted=None).first()
            if mach:
                machine_form.cimc.choices = machine_form.get_cimc_choices('standalone', mach.cimc_id)
                if machine_form.submit.data:
                    # continue to display the form data input by user even if we have error prompt
                    machine_form.submit.label.text = 'Save Changes'
                else:
                    # populate the form in edit page
                    machine_form.cimc.default = mach.cimc_id
                    machine_form.project.default = mach.project_id
                    machine_form.process()  # change select field default
                    machine_form.hostname.data = mach.host
                    machine_form.ip.data = mach.ip
                    machine_form.submit.label.text = 'Save Changes'
            else:
                return redirect(url_for('machine', m=request.args['m']))
        if request.method == 'POST':
            if machine_form.validate():
                if request.form['cfg-submit'] == 'Add New':
                    machine_form.add_entry(request.args.get('m'))
                elif request.form['cfg-submit'] == 'Save Changes':
                    machine_form.edit_entry()
                    return redirect(url_for('machine', m=request.args['m']))
                elif request.form['cfg-submit'] == 'Delete Entry':
                    if request.args.get('edit'):
                        machine_form.delete_entry(request.args['edit'])
                        return redirect(url_for('machine', m=request.args['m']))
                return redirect(request.url)

        userdict.update(title='ECSN | Standalone Config')
        userdict.update(h1='Standalone Machine (Bare Metal)')
        userdict.update(machine_list=Machine.query.filter_by(type='standalone', date_deleted=None).all())
    elif request.args.get('m') == 'virtual':
        machine_form.cimc.choices = machine_form.get_cimc_choices('virtual')
        if request.method == 'POST':
            if machine_form.validate():
                if request.form['cfg-submit'] == 'Add New':
                    machine_form.add_entry(request.args.get('m'))
                elif request.form['cfg-submit'] == 'Save Changes':
                    machine_form.edit_entry()
                    return redirect(url_for('machine', m=request.args['m']))
                elif request.form['cfg-submit'] == 'Delete Entry':
                    if request.args.get('edit'):
                        machine_form.delete_entry(request.args['edit'])
                        return redirect(url_for('machine', m=request.args['m']))
                return redirect(request.url)
        if request.args.get('edit'):
            if machine_form.submit.data:
                # continue to display the form data input by user even if we have error prompt
                machine_form.submit.label.text = 'Save Changes'
            else:
                # default display to populate the forms
                mach = Machine.query.filter_by(host=request.args['edit'], date_deleted=None).first()
                if mach:
                    machine_form.cimc.default = mach.cimc_id
                    machine_form.esxi.default = mach.esxi_id
                    machine_form.project.default = mach.project_id
                    machine_form.process()  # change select field default
                    machine_form.hostname.data = mach.host
                    machine_form.vmname.data = mach.vm_name
                    machine_form.ip.data = mach.ip
                    machine_form.submit.label.text = 'Save Changes'
                else:
                    return redirect(url_for('machine', m=request.args['m']))

        userdict.update(title='ECSN | Virtual Config')
        userdict.update(h1='Virtual Machine')
        userdict.update(machine_list=Machine.query.filter_by(type='virtual', date_deleted=None).all())
    else:
        return redirect(404)

    controller = dict()
    hypervisor = dict()
    hold = db.session.query(Controller.id, Controller.host, Controller.ip).all()
    for (uid, hostname, ip_address) in hold:
        controller[uid] = "{} {}".format(ip_address, hostname)
    hold = db.session.query(Hypervisor.id, Hypervisor.host, Hypervisor.ip).all()
    for (uid, hostname, ip_address) in hold:
        hypervisor[uid] = "{} {}".format(ip_address, hostname)

    hold = deepcopy(machine_form.project.choices)
    hold.pop(0)  # remove the first element
    project_dict = dict(hold)  # convert list of tuples to dict

    userdict.update(controller_dict=controller)
    userdict.update(hypervisor_dict=hypervisor)
    userdict.update(project_dict=project_dict)
    userdict.update(machine_form=machine_form)
    return render_template('machine.html', userdict=userdict)


@app.route('/activity', methods=['GET', 'POST'])
@login_required
def activity():
    userdict = dict()
    if request.args.get('machine'):
        mach = Machine.query.filter_by(host=request.args['machine']).first()
        if mach:
            userdict.update(act_list=DataState.query.filter_by(machine_id=mach.id)
                            .order_by(DataState.date_created.desc()).limit(100))
        else:
            return redirect(url_for('activity'))
    elif request.args.get('state'):
        obj_list = DataState.query.filter_by(state=request.args['state'])\
            .order_by(DataState.date_created.desc()).limit(200)
        userdict.update(act_list=[])
        if obj_list:
            hold = list()
            for data in obj_list:
                hold.append(data.machine_id)
            if hold:
                machine_id = list(set(hold))
                act_list = list()
                for uid in machine_id:
                    for obj in obj_list:
                        if uid == obj.machine_id:
                            act_list.append(obj)
                userdict.update(act_list=act_list)
    else:
        obj_list = DataState.query.order_by(DataState.date_created.desc()).limit(200)
        userdict.update(act_list=[])
        if obj_list:
            hold = list()
            for data in obj_list:
                hold.append(data.machine_id)
            if hold:
                machine_id = list(set(hold))
                act_list = list()
                for uid in machine_id:
                    for obj in obj_list:
                        if uid == obj.machine_id:
                            act_list.append(obj)
                userdict.update(act_list=act_list)

    machines = dict()
    hold = db.session.query(Machine.id, Machine.host).all()
    for (uid, hostname) in hold:
        machines[uid] = hostname
    userdict.update(machine_dict=machines)

    return render_template('activity.html', userdict=userdict)


@app.route('/tasks', methods=['GET', 'POST'])
@login_required
def tasks():
    userdict = dict()
    userdict.update(task_list=Tasks.query.order_by(Tasks.date_created.desc()).limit(100))

    machines = dict()
    hold = db.session.query(Machine.id, Machine.host).all()
    for (uid, hostname) in hold:
        machines[uid] = hostname
    userdict.update(machine_dict=machines)

    users = dict()
    hold = db.session.query(User.id, User.username).all()
    for (uid, name) in hold:
        users[uid] = name
    userdict.update(user_dict=users)

    return render_template('tasks.html', userdict=userdict)


@app.route('/idle', methods=['GET', 'POST'])
@login_required
def machine_idle():
    userdict = dict()
    userdict.update(occurrence_form=IdleOccurrenceForm(), scheduler_form=IdleSchedulerForm())

    return render_template('idle.html', userdict=userdict)
