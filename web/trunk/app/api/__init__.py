from flask import Flask
import os, sys

dir_path = os.path.dirname(os.path.realpath(__file__))
root_path = os.path.abspath(os.path.join(dir_path, '../../..'))
sys.path.insert(0, root_path)

app_api = Flask(__name__)
app_api.config.from_object('config')

import views
