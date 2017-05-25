#!flask/bin/python
from app.api import app_api

app_api.debug = True
app_api.run(host='0.0.0.0', port=8080, threaded=True)
