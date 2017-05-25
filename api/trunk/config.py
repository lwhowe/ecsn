import os

basedir = os.path.abspath(os.path.dirname(__file__))
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, '../..', 'data.db')  # database path and type
SQLALCHEMY_TRACK_MODIFICATIONS = False  # http://flask-sqlalchemy.pocoo.org/2.1/config/

# Cross Site Request Forgery security for Flask-WTF (not applicable to api services)
WTF_CSRF_SECRET_KEY = '4cnq%8#;4Rs[}3w2LG-eAaawB]fw[-?2x\j2)kD@Vg6J68'
SECRET_KEY = '4cnq%8#;4Rs[}3w2LG-eAaawB]fw[-?2x\j2)kD@Vg6J68'
