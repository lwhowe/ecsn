import calendar
from datetime import datetime, timedelta
from flask import flash, session
from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, PasswordField, SubmitField, SelectField
from wtforms import DateField, DateTimeField
from wtforms.validators import DataRequired, ValidationError
from . import db
from .models import Site, BusinessUnit, ProductFamily, Project, Machine, Controller, Hypervisor


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(message='Enter your username')])
    password = PasswordField('Password', validators=[DataRequired(message='Enter your password')])
    remember_me = BooleanField('Remember Me', default=False)
    submit = SubmitField('ENTER')


class ControllerForm(FlaskForm):
    hostname = StringField('Hostname')
    ip = StringField('IP Address', validators=[DataRequired(message='IP address required')])
    username = StringField('Username', validators=[DataRequired(message='Username required')])
    password = StringField('Password', validators=[DataRequired(message='Password required')])
    submit = SubmitField('Add New')

    def __init__(self, *args, **kwargs):
        FlaskForm.__init__(self, *args, **kwargs)

    def validate(self, extra_validators=None):
        if not super(ControllerForm, self).validate():  # Or use, Form.validate(self):
            return False
        # Add custom validation here
        return True

    @staticmethod
    def validate_hostname(form, field):
        """ Custom inline validator for hostname field that checks for any duplicates

        :param cls form: required by wtforms but can be ignore
        :param obj field: info from form's hostname input
        :return:
        """
        try:
            check_host(field.data.strip())
        except ValueError, e:
            raise ValidationError(str(e))

    @staticmethod
    def validate_ip(form, field):
        """ Custom inline validator for ip field that checks for any duplicates

        :param cls form: required by wtforms but can be ignore
        :param obj field: info from form's ip input
        :return:
        """
        try:
            check_ip(field.data.strip())
        except ValueError, e:
            raise ValidationError(str(e))

    def add_entry(self):
        if self.hostname.data.strip():
            obj = Controller(self.ip.data.strip(), self.username.data.strip(), self.password.data.strip(),
                             hostname=self.hostname.data.strip())
        else:
            obj = Controller(self.ip.data.strip(), self.username.data.strip(), self.password.data.strip())
        db.session.add(obj)
        db.session.commit()
        flash('Entry added successfully')


class HypervisorForm(FlaskForm):
    hostname = StringField('Hostname')
    ip = StringField('IP Address', validators=[DataRequired(message='IP address required')])
    username = StringField('Username', validators=[DataRequired(message='Username required')])
    password = StringField('Password', validators=[DataRequired(message='Password required')])
    submit = SubmitField('Add New')

    def __init__(self, *args, **kwargs):
        FlaskForm.__init__(self, *args, **kwargs)

    def validate(self, extra_validators=None):
        if not super(HypervisorForm, self).validate():  # Or use, Form.validate(self):
            return False
        # Add custom validation here
        return True

    @staticmethod
    def validate_hostname(form, field):
        """ Custom inline validator for hostname field that checks for any duplicates

        :param cls form: required by wtforms but can be ignore
        :param obj field: info from form's hostname input
        :return:
        """
        try:
            check_host(field.data.strip())
        except ValueError, e:
            raise ValidationError(str(e))

    @staticmethod
    def validate_ip(form, field):
        """ Custom inline validator for ip field that checks for any duplicates

        :param cls form: required by wtforms but can be ignore
        :param obj field: info from form's ip input
        :return:
        """
        try:
            check_ip(field.data.strip())
        except ValueError, e:
            raise ValidationError(str(e))

    def add_entry(self):
        if self.hostname.data.strip():
            obj = Hypervisor(self.ip.data.strip(), self.username.data.strip(), self.password.data.strip(),
                             hostname=self.hostname.data.strip())
        else:
            obj = Hypervisor(self.ip.data.strip(), self.username.data.strip(), self.password.data.strip())
        db.session.add(obj)
        db.session.commit()
        flash('Entry added successfully')


class MachineForm(FlaskForm):
    hostname = StringField('Hostname', validators=[DataRequired(message='Hostname required')])
    vmname = StringField('VM Name')
    ip = StringField('IP Address', validators=[DataRequired(message='IP address required')])
    cimc = SelectField('CIMC', choices=[])
    esxi = SelectField('ESXI', choices=[])
    project = SelectField('Project', choices=[])
    submit = SubmitField('Add New')

    def __init__(self, request, *args, **kwargs):
        FlaskForm.__init__(self, *args, **kwargs)
        self.request = request
        self.esxi.choices = self.get_esxi_choices()
        self.project.choices = self.get_proj_choices()

    @staticmethod
    def get_cimc_choices(category=None, required=None):
        cimc_used = list()
        if category == 'standalone':
            hold = db.session.query(Machine.cimc_id).filter(Machine.cimc_id.isnot(None)).all()
            if hold:
                cimc_used = set(zip(*hold)[0])
        elif category == 'virtual':
            hold = db.session.query(Machine.cimc_id).filter(Machine.cimc_id.isnot(None),
                                                            Machine.type.is_('standalone')).all()
            if hold:
                cimc_used = set(zip(*hold)[0])
        cimc_choices = [('', 'Select CIMC')]
        cimc_choices.extend([(str(x.id), "{} {}".format(x.ip, x.host))
                             for x in Controller.query.all() if x.id not in cimc_used or x.id is required])
        return cimc_choices

    @staticmethod
    def get_esxi_choices():
        esxi_choices = [('', 'Select ESXI')]
        esxi_choices.extend([(str(x.id), "{} {}".format(x.ip, x.host)) for x in Hypervisor.query.all()])
        return esxi_choices

    @staticmethod
    def get_proj_choices():
        site_dict = dict()
        unit_dict = dict()
        family_dict = dict()
        for obj in Site.query.all():
            site_dict[obj.id] = obj.name
        for obj in BusinessUnit.query.all():
            unit_dict[obj.id] = obj.name
        for obj in ProductFamily.query.all():
            family_dict[obj.id] = obj.name
        project_choices = [('', 'Select a Project')]
        project_choices.extend([(str(x.id), "{}: {}: {}".format(
            site_dict[x.site_id], unit_dict[x.unit_id], family_dict[x.family_id])) for x in Project.query.all()])
        return project_choices

    def validate(self, extra_validators=None):
        if not super(MachineForm, self).validate():  # Or use, Form.validate(self):
            return False

        # validate cimc and esxi field for virtual machine
        if self.cimc.data.strip() and self.esxi.data.strip():
            cimc_field = int(self.cimc.data.strip())
            esxi_field = int(self.esxi.data.strip())

            cimc_list = db.session.query(Machine.cimc_id, Machine.esxi_id)\
                .filter(Machine.cimc_id.is_(cimc_field), Machine.esxi_id.isnot(None)).all()
            for (cimc_id, esxi_id) in cimc_list:
                if cimc_id != cimc_field or esxi_id != esxi_field:
                    flash('Error: Cannot associate CIMC and ESXI due to existing record[s]')
                    return False

            esxi_list = db.session.query(Machine.cimc_id, Machine.esxi_id) \
                .filter(Machine.cimc_id.isnot(None), Machine.esxi_id.is_(esxi_field)).all()
            for (cimc_id, esxi_id) in esxi_list:
                if cimc_id != cimc_field or esxi_id != esxi_field:
                    flash('Error: Cannot associate CIMC and ESXI due to existing record[s]')
                    return False
        return True

    @staticmethod
    def validate_hostname(form, field):
        """ Custom inline validator for hostname field that checks for any duplicates

        :param cls form: required by wtforms but can be ignore
        :param obj field: info from form's hostname input
        :return:
        """
        try:
            if form.request.form[form.submit.id] == 'Add New':
                check_host(field.data.strip())
            elif form.request.form[form.submit.id] == 'Save Changes':
                if field.data.strip() != form.request.args['edit']:
                    check_host(field.data.strip())
        except ValueError, e:
            raise ValidationError(str(e))

    @staticmethod
    def validate_vmname(form, field):
        if form.request.args.get('m') == 'virtual':
            if not field.data.strip():
                raise ValueError('VM Name required')
            else:
                if form.request.form[form.submit.id] == 'Add New':
                    if Machine.query.filter_by(vm_name=field.data.strip()).first():
                        raise ValueError('VM Name taken')
                elif form.request.form[form.submit.id] == 'Save Changes':
                    hold = db.session.query(Machine.host).filter_by(vm_name=field.data.strip(),
                                                                    type=form.request.args['m']).first()
                    if hold and hold[0] != form.request.args['edit']:
                        raise ValidationError('VM Name taken')

    @staticmethod
    def validate_ip(form, field):
        """ Custom inline validator for ip field that checks for any duplicates

        :param cls form: required by wtforms but can be ignore
        :param obj field: info from form's ip input
        :return:
        """
        try:
            if form.request.form['cfg-submit'] == 'Add New':
                check_ip(field.data.strip())
            elif form.request.form['cfg-submit'] == 'Save Changes':
                hold = db.session.query(Machine.ip).filter_by(host=form.request.args['edit'],
                                                              type=form.request.args['m']).first()
                if hold and hold[0] != field.data.strip():
                    check_ip(field.data.strip())
        except ValueError, e:
            raise ValidationError(str(e))

    @staticmethod
    def validate_project(form, field):
        if not field.data.strip():
            raise ValidationError('Project required')

    def add_entry(self, host_type):
        vm_name = self.vmname.data.strip() if self.vmname.data.strip() else None
        cimc_id = int(self.cimc.data.strip()) if self.cimc.data.strip() else None
        proj_id = int(self.project.data.strip()) if self.project.data.strip() else None
        if host_type == 'standalone':
            obj = Machine(self.hostname.data.strip(), self.ip.data.strip(), 'standalone',
                          vm_name=vm_name, cimc=cimc_id, project=proj_id)
        else:
            esxi_id = int(self.esxi.data.strip()) if self.esxi.data.strip() else None
            obj = Machine(self.hostname.data.strip(), self.ip.data.strip(), 'virtual',
                          vm_name=vm_name, cimc=cimc_id, esxi=esxi_id, project=proj_id)
        db.session.add(obj)
        db.session.commit()
        flash('Entry added successfully')

    def edit_entry(self):
        obj = Machine.query.filter_by(host=self.request.args['edit'], type=self.request.args['m']).first()
        obj.host = self.hostname.data.strip()
        obj.vm_name = None
        if self.request.args['m'] == 'virtual':
            obj.vm_name = self.vmname.data.strip()
        obj.ip = self.ip.data.strip()
        obj.project_id = int(self.project.data.strip()) if self.project.data.strip() else None
        obj.cimc_id = int(self.cimc.data.strip()) if self.cimc.data.strip() else None
        obj.esxi_id = int(self.esxi.data.strip()) if self.esxi.data.strip() else None
        db.session.commit()
        flash('Entry saved successfully')

    @staticmethod
    def delete_entry(hostname=None):
        obj = Machine.query.filter_by(host=hostname).first()
        if obj:
            current_utctime = datetime.utcnow()
            obj.date_deleted = current_utctime
            obj.host = current_utctime.strftime('%Y%m%d%H%M%S_{}'.format(obj.host))
            obj.ip = current_utctime.strftime('%Y%m%d%H%M%S_{}'.format(obj.ip))
            if obj.vm_name:
                obj.vm_name = current_utctime.strftime('%Y%m%d%H%M%S_{}'.format(obj.vm_name))
            obj.cimc_id = None
            obj.esxi_id = None
            db.session.commit()
            flash('Entry deleted successfully')


class ConfigForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(message='Name is required')])
    desc = StringField('Description', validators=[DataRequired(message='Description is required')])
    submit = SubmitField('Add New')

    def __init__(self, request, *args, **kwargs):
        FlaskForm.__init__(self, *args, **kwargs)
        self.request = request

    def validate(self, extra_validators=None):
        if not super(ConfigForm, self).validate():  # Or use, Form.validate(self):
            return False
        # Add custom validation here
        return True

    @staticmethod
    def validate_name(form, field):
        """ Custom inline validator for name field that checks for any duplicates

        :param cls form: required by wtforms but can be ignore
        :param obj field: info from form's hostname input
        :return:
        """
        if form.request.args.get('m') == 'site':
            if Site.query.filter_by(name=field.data.strip()).first():
                raise ValidationError('Site name taken')
        elif form.request.args.get('m') == 'unit':
            if BusinessUnit.query.filter_by(name=field.data.strip()).first():
                raise ValidationError('Business Unit name taken')
        elif form.request.args.get('m') == 'family':
            if ProductFamily.query.filter_by(name=field.data.strip()).first():
                raise ValidationError('Product Family name taken')

    def add_entry(self, mode):
        if mode == 'site':
            db.session.add(Site(self.name.data.strip(), self.desc.data.strip()))
            db.session.commit()
            session['site_dict'] = dict()
            for site in Site.query.all():
                session['site_dict'][site.id] = dict(name=site.name, description=site.description)
        elif mode == 'unit':
            db.session.add(BusinessUnit(self.name.data.strip(), self.desc.data.strip()))
            db.session.commit()
            session['unit_dict'] = dict()
            for unit in BusinessUnit.query.all():
                session['unit_dict'][unit.id] = dict(name=unit.name, description=unit.description)
        elif mode == 'family':
            db.session.add(ProductFamily(self.name.data.strip(), self.desc.data.strip()))
            db.session.commit()
            session['family_dict'] = dict()
            for family in ProductFamily.query.all():
                session['family_dict'][family.id] = dict(name=family.name, description=family.description)
        flash('Entry added successfully')


class ProjectForm(FlaskForm):
    site = SelectField('Site', choices=[])
    unit = SelectField('Business Unit', choices=[])
    family = SelectField('Product Family', choices=[])
    submit = SubmitField('Add New')

    def __init__(self, *args, **kwargs):
        FlaskForm.__init__(self, *args, **kwargs)

        self.site.choices = [('', 'Select a Site')] + \
                            [(str(x.id), "{}: {}".format(x.name, x.description)) for x in Site.query.all()]
        self.unit.choices = [('', 'Select a Business Unit')] + \
                            [(str(x.id), "{}: {}".format(x.name, x.description)) for x in BusinessUnit.query.all()]
        self.family.choices = [('', 'Select a Product Family')] + \
                              [(str(x.id), "{}: {}".format(x.name, x.description)) for x in ProductFamily.query.all()]

    def validate(self, extra_validators=None):
        if not super(ProjectForm, self).validate():  # Or use, Form.validate(self):
            return False
        # Add custom validation here
        if Project.query.filter_by(site_id=int(self.site.data.strip()),
                                   unit_id=int(self.unit.data.strip()),
                                   family_id=int(self.family.data.strip())).first():
            flash('Error: Entry already existed')
            return False
        return True

    @staticmethod
    def validate_site(form, field):
        if not field.data.strip():
            raise ValidationError('Choose a Site')

    @staticmethod
    def validate_unit(form, field):
        if not field.data.strip():
            raise ValidationError('Choose a Business Unit')

    @staticmethod
    def validate_family(form, field):
        if not field.data.strip():
            raise ValidationError('Choose a Product Family')

    def add_entry(self):
        obj = Project(self.site.data, self.unit.data, self.family.data)
        db.session.add(obj)
        db.session.commit()
        flash('Entry added successfully')


class IdleSchedulerForm(FlaskForm):
    date_start = DateField('Starts: ', format='%m/%d/%Y', default=datetime.today())
    date_end = DateField('Ends: ', format='%m/%d/%Y', default=datetime.today())
    time_start = DateTimeField(format='%I:%M %p', default=datetime.today())
    time_end = DateTimeField(format='%I:%M %p', default=datetime.today()+timedelta(minutes=30))
    submit = SubmitField('Add New')

    def validate(self, extra_validators=None):
        if not super(IdleSchedulerForm, self).validate():  # Or use, Form.validate(self):
            return False
        return True


class IdleOccurrenceForm(FlaskForm):
    weekday = SelectField('Day: ', choices=[])
    time_start = DateTimeField(format='%I:%M %p', default=datetime.today())
    time_end = DateTimeField(format='%I:%M %p', default=datetime.today()+timedelta(minutes=30))
    submit = SubmitField('Add New')

    def __init__(self, *args, **kwargs):
        FlaskForm.__init__(self, *args, **kwargs)
        self.weekday.choices = [(str(num), day) for num, day in enumerate(list(calendar.day_name))]

    def validate(self, extra_validators=None):
        if not super(IdleOccurrenceForm, self).validate():  # Or use, Form.validate(self):
            return False
        return True


def check_ip(ip_addr):
    if Controller.query.filter_by(ip=ip_addr).first():
        raise ValueError('Found duplicate in CIMC')
    elif Hypervisor.query.filter_by(ip=ip_addr).first():
        raise ValidationError('Found duplicate in ESXi')
    obj = Machine.query.filter_by(ip=ip_addr).first()
    if obj:
        raise ValidationError('Found duplicate in {} Machine'.format(obj.type.title()))


def check_host(hostname):
    if Controller.query.filter_by(host=hostname).first():
        raise ValueError('Found duplicate in CIMC')
    elif Hypervisor.query.filter_by(host=hostname).first():
        raise ValidationError('Found duplicate in ESXi')
    obj = Machine.query.filter_by(host=hostname).first()
    if obj:
        raise ValidationError('Found duplicate in {} Machine'.format(obj.type.title()))
