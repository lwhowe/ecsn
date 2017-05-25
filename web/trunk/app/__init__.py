from celery import Celery
from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

import logging.config
from loggers import setting
logging.config.dictConfig(setting)

# Flask init
app = Flask(__name__)
app.config.from_object('config')

# Database init & version control with migrate
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Flask login manager
lm = LoginManager()
lm.init_app(app)
lm.next_url = 'index'  # default login redirect
lm.login_view = 'login'  # default login view
lm.login_message = 'Please log in using CEC account.'

# Celery asynchronous task queue init
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)  # any config options can be passed from Flask config

from . import auth, views, models
