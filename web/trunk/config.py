import os
from datetime import timedelta
from celery.schedules import crontab

basedir = os.path.abspath(os.path.dirname(__file__))
SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(basedir, '../..', 'data.db')  # database path and type
SQLALCHEMY_TRACK_MODIFICATIONS = False  # http://flask-sqlalchemy.pocoo.org/2.1/config/

# Cross Site Request Forgery security for Flask-WTF
WTF_CSRF_SECRET_KEY = '4cnq%8#;4Rs[}3w2LG-eAaawB]fw[-?2x\j2)kD@Vg6J68'
SECRET_KEY = '4cnq%8#;4Rs[}3w2LG-eAaawB]fw[-?2x\j2)kD@Vg6J68'

REMEMBER_COOKIE_NAME = 'ecsn_token'
REMEMBER_COOKIE_DURATION = timedelta(days=14)

# Celery asynchronous task queue
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'

CELERY_IMPORTS = ('app.scheduler.works',)
CELERYBEAT_SCHEDULE = {
    'every-five-minute': {
        'task': 'app.scheduler.works.runit_queue',
        'schedule': crontab(minute='*/5'),
    },
    'every-minute': {
        'task': 'app.scheduler.works.runit_shutdown',
        'schedule': crontab(minute='*/1'),
    },
}
