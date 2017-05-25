import auth
from . import db


# Define a base model for other database tables to inherit
class Base(db.Model):
    __abstract__ = True

    id = db.Column(db.Integer, primary_key=True)
    date_created = db.Column(db.DateTime, default=db.func.current_timestamp())
    date_modified = db.Column(db.DateTime, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    date_deleted = db.Column(db.DateTime)


class User(Base):
    __tablename__ = 'user'

    username = db.Column(db.String(32), index=True, nullable=False)
    password = db.Column(db.String(64), nullable=False)
    email = db.Column(db.String(64), index=True)
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))
    session_key = db.Column(db.String(64))
    type = db.Column(db.String(32))
    role = db.Column(db.SmallInteger)
    status = db.Column(db.SmallInteger)
    tasks = db.relationship('Tasks', backref='freeze', lazy='dynamic')
    idle = db.relationship('IdleLimit', backref='time', lazy='dynamic')

    # Reference by script
    role_dict = {'0': 'root', '1': 'superuser', '2': 'admin', '10': 'user', '11': 'operator'}
    status_dict = {'0': 'inactive', '1': 'active'}

    def __init__(self, user, password, account_type, **kwargs):
        self.username = user
        self.password = password
        self.email = kwargs.get('email', None)
        self.first_name = kwargs.get('first_name', None)
        self.last_name = kwargs.get('last_name', None)
        self.session_key = auth.generate_uuid()  # random 32 characters
        self.type = account_type
        self.role = 10  # default to viewer only
        self.status = 1  # default to active, may be use for inactive or deleted user in the future

    def __repr__(self):
        return '<ID: %r, Username: %r>' % (self.id, self.username)

    # Use by flask-login manager
    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def get_id(self):
        try:
            return unicode(self.id)  # python 2
        except NameError:
            return str(self.id)  # python 3

    # Use by @lm.token_loader decorator to retrieve stored user data from our server
    def get_auth_token(self):
        """ Function used by @lm.token_loader decorator to retrieve stored cookie user data from client.
        It is important to note that the Flask Session Cookie and the Flask-Login Cookie are vulnerable
        to attack. Although the cookies are encrypted and relatively safe from attack a user who is
        sniffing network traffic can easily copy the cookies and impersonate the user.
            The only way to prevent this kind of attack is to use secure sockets (https) when sending
        back and forth the cookies.
            Purpose of storing the password hash so that if a user is logged in on multiple computers/browsers
        and changes their password, it will invalidate the cookie token. It is important to never store a users
        plain text password, that way if your system is ever compromised someone can still not access users data
        even with the stored password hash.

        :return:
        """
        data = [str(self.id), self.session_key]
        return auth.login_serializer().dumps(data)


class Site(Base):
    __tablename__ = 'site'

    name = db.Column(db.String(64), index=True, unique=True, nullable=False)
    description = db.Column(db.String(128), nullable=False)
    users = db.relationship('Project', backref='location', lazy='dynamic')

    def __init__(self, name, desc):
        self.name = name
        self.description = desc

    def __repr__(self):
        return "<Site id: {}, name:{}>".format(self.id, self.name)


class BusinessUnit(Base):
    __tablename__ = 'unit'

    name = db.Column(db.String(64), index=True, unique=True, nullable=False)
    description = db.Column(db.String(128), nullable=False)
    users = db.relationship('Project', backref='business', lazy='dynamic')

    def __init__(self, name, desc):
        self.name = name
        self.description = desc

    def __repr__(self):
        return "<BusinessUnit id: {}, name:{}>".format(self.id, self.name)


class ProductFamily(Base):
    __tablename__ = 'family'

    name = db.Column(db.String(64), index=True, unique=True, nullable=False)
    description = db.Column(db.String(128), nullable=False)
    users = db.relationship('Project', backref='family', lazy='dynamic')

    def __init__(self, name, desc):
        self.name = name
        self.description = desc

    def __repr__(self):
        return "<ProductFamily id: {}, name:{}>".format(self.id, self.name)


class Project(Base):
    __tablename__ = 'project'

    site_id = db.Column(db.Integer, db.ForeignKey('site.id'))
    unit_id = db.Column(db.Integer, db.ForeignKey('unit.id'))
    family_id = db.Column(db.Integer, db.ForeignKey('family.id'))
    machines = db.relationship('Machine', backref='server', lazy='dynamic')

    def __init__(self, site, unit, family):
        self.site_id = site
        self.unit_id = unit
        self.family_id = family

    def __repr__(self):
        return "<Project id: %r, Registry:%r-%r-%r>" % (self.id, self.site_id, self.unit_id, self.family_id)


class Machine(Base):
    __tablename__ = 'machine'

    host = db.Column(db.String(32), index=True, nullable=False, unique=True)
    ip = db.Column(db.String(64), index=True, nullable=False, unique=True)
    type = db.Column(db.String(16), nullable=False)
    state = db.Column(db.SmallInteger)
    status = db.Column(db.SmallInteger)
    vm_name = db.Column(db.String(32), unique=True)
    cimc_id = db.Column(db.Integer, db.ForeignKey('controller.id'))
    esxi_id = db.Column(db.Integer, db.ForeignKey('hypervisor.id'))
    project_id = db.Column(db.Integer, db.ForeignKey('project.id'))
    tasks = db.relationship('Tasks', backref='job', lazy='dynamic')
    idle = db.relationship('IdleLimit', backref='limit', lazy='dynamic')

    # Reference by script
    type_tuple = ('standalone', 'virtual')
    state_dict = {'0': 'off', '1': 'on', '2': 'suspend', '3': 'shutdown', '4': 'restart'}
    status_dict = {'0': 'idle', '1': 'active', '2': 'unreachable'}

    def __init__(self, hostname, ip_address, machine_type, **kwargs):
        self.host = hostname
        self.ip = ip_address
        self.type = machine_type
        self.state = 0  # default off
        self.status = 0  # default idle
        self.vm_name = kwargs.get('vm_name', None)
        self.cimc_id = kwargs.get('cimc', None)
        self.esxi_id = kwargs.get('esxi', None)
        self.project_id = kwargs.get('project', None)

    def __repr__(self):
        return '<Machine: {} {}>'.format(self.host, self.ip)


class Controller(Base):
    __tablename__ = 'controller'

    host = db.Column(db.String(32), index=True, unique=True)
    ip = db.Column(db.String(64), index=True, nullable=False, unique=True)
    user = db.Column(db.String(32), nullable=False)
    password = db.Column(db.String(32), nullable=False)
    state = db.Column(db.SmallInteger)
    status = db.Column(db.SmallInteger)
    machines = db.relationship('Machine', backref='cimc', lazy='dynamic')

    # Reference by script
    state_dict = {'0': 'off', '1': 'on', '2': 'suspend', '3': 'shutdown', '4': 'restart'}
    status_dict = {'0': 'unreachable', '1': 'unverified', '2': 'verified'}

    def __init__(self, ip_address, username, password, **kwargs):
        self.host = kwargs.get('hostname', None)
        self.ip = ip_address
        self.user = username
        self.password = password
        self.state = kwargs.get('state', None)
        self.status = 1  # default unverified

    def __repr__(self):
        return '<Integrated Management Controller: {} {} {}'\
            .format(self.host, self.ip, self.status_dict[str(self.status)])


class Hypervisor(Base):
    __tablename__ = 'hypervisor'

    host = db.Column(db.String(32), index=True, unique=True)
    ip = db.Column(db.String(64), index=True, nullable=False, unique=True)
    user = db.Column(db.String(32), nullable=False)
    password = db.Column(db.String(32), nullable=False)
    state = db.Column(db.SmallInteger)
    status = db.Column(db.SmallInteger)
    machines = db.relationship('Machine', backref='esxi', lazy='dynamic')

    # Reference by script
    state_dict = {'0': 'off', '1': 'on', '2': 'suspend', '3': 'shutdown', '4': 'restart'}
    status_dict = {'0': 'unreachable', '1': 'unverified', '2': 'verified'}

    def __init__(self, ip_address, username, password, **kwargs):
        self.host = kwargs.get('hostname', None)
        self.ip = ip_address
        self.user = username
        self.password = password
        self.state = kwargs.get('state', None)
        self.status = 1  # default unverified

    def __repr__(self):
        return '<vSphere Hypervisor: {} {}: {}'.format(self.host, self.ip, self.status_dict[str(self.status)])


class DataState(Base):
    __tablename__ = 'data_state'

    date_entry = db.Column(db.DateTime, nullable=False)
    state = db.Column(db.String(32), nullable=False)
    machine_id = db.Column(db.Integer, db.ForeignKey('machine.id'), nullable=False)

    def __init__(self, uid, date, state):
        self.date_entry = date
        self.state = state
        self.machine_id = uid


class Tasks(Base):
    __tablename__ = 'tasks'

    date_assign = db.Column(db.DateTime, nullable=False)
    name = db.Column(db.String(64), index=True, nullable=False)
    type = db.Column(db.String(32), nullable=False)
    status = db.Column(db.String(32))
    machine_id = db.Column(db.Integer, db.ForeignKey('machine.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    # Reference by script
    task_tuple = ('auto-shut', 'freeze')

    def __init__(self, name, task_type, machine, date_time, **kwargs):
        self.name = name
        if task_type not in self.task_tuple:
            raise ValueError("Input task type '{}' are not a valid options".format(type))
        self.type = task_type
        self.machine_id = machine
        self.status = kwargs.get('status', None)
        self.user_id = kwargs.get('user_id', None)
        self.date_assign = date_time


class IdleLimit(Base):
    __tablename__ = 'idle_limit'

    date_assign = db.Column(db.DateTime, nullable=False)
    duration = db.Column(db.Float, nullable=False)
    idle_limit = db.Column(db.Float, nullable=False)
    idle_default = db.Column(db.Float)
    type = db.Column(db.String(32), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    machine_id = db.Column(db.Integer, db.ForeignKey('machine.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))

    # Reference by script
    type_tuple = ('occurrence', 'scheduled')

    def __init__(self, datetime, duration, limit, type, machine_id=None, user_id=None, **kwargs):
        self.date_assign = datetime
        self.duration = duration
        self.idle_limit = limit
        self.idle_default = kwargs.get('default', None)
        self.type = type
        if not machine_id:
            if not isinstance(machine_id, int):
                raise ValueError('machine id only accept integer')
            raise ValueError('machine id is None')
        self.machine_id = machine_id
        self.user_id = user_id
