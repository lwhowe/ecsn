from datetime import datetime
from flask import request, json
from . import app, db
from web.trunk.app.models import Machine, DataState


@app.route('/api/test', methods=['POST'])
def api_test():
    if request.headers['Content-Type'] == 'application/json':
        return "JSON: " + json.dumps(request.json) + "\n"
    else:
        return "415 Unsupported Media Type\n"


@app.route('/api/state/add', methods=['POST'])
def api_state_add():
    if request.headers['Content-Type'] == 'application/json':
        if not all(key in request.json for key in ('date_entry', 'hostname', 'state')):
            return json.dumps(dict(message="json data incomplete", code=400)), 400

        machine = Machine.query.filter_by(host=request.json['hostname']).first()
        if machine:
            try:
                time_format = "%Y-%m-%d %H:%M:%S.%f" if '.' in request.json['date_entry'] else "%Y-%m-%d %H:%M:%S"
                timestamp = datetime.strptime(request.json['date_entry'], time_format)
                entry = DataState(machine.id, timestamp, request.json['state'].lower())
                db.session.add(entry)
                db.session.commit()
                return json.dumps(dict(message="Entry added successfully", code=200)), 200
            except ValueError, e:
                return json.dumps(dict(message="{}".format(str(e)), code=400)), 400
        else:
            return json.dumps(dict(message="Machine not found", code=400)), 400
    else:
        return json.dumps(dict(message="Unsupported Media Type", code=415)), 415
