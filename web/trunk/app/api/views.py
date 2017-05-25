import logging
from datetime import datetime
from flask import request, json
from .. import db
from ..models import Machine, DataState
from . import app_api

log = logging.getLogger(__name__)


@app_api.route('/api/state/add', methods=['POST'])
def api_state_add():
    if request.headers['Content-Type'] == 'application/json':
        if not all(key in request.json for key in ('date_entry', 'hostname', 'state')):
            return json.dumps(dict(message="json data incomplete", code=400)), 400

        machine = Machine.query.filter_by(host=request.json['hostname'].strip()).first()
        if machine:
            try:
                time_format = "%Y-%m-%d %H:%M:%S.%f" if '.' in request.json['date_entry'] else "%Y-%m-%d %H:%M:%S"
                timestamp = datetime.strptime(request.json['date_entry'].strip(), time_format)
                status = request.json['state'].strip().lower()
                entry = DataState(machine.id, timestamp, status)  # add new entry
                if status == '0' or status == '1':
                    machine.state = 1  # machine state set to on
                    machine.status = int(status)  # machine status update real time
                db.session.add(entry)
                db.session.commit()
                # log.info('Added entry: {}: {}: {}'.format(timestamp, machine.host, request.json['state'].lower()))
                return json.dumps(dict(message="Entry added successfully", code=200)), 200
            except ValueError, e:
                return json.dumps(dict(message="{}".format(str(e)), code=400)), 400
        else:
            """
            def __init__(self, hostname, ip_address, machine_type, **kwargs):
                self.host = hostname
                self.ip = ip_address
                self.type = machine_type
                self.state = 0  # off
                self.status = 0  # disconnect
                self.vm_name = kwargs.get('vm_name', None)
                self.cimc_id = kwargs.get('cimc', None)
                self.esxi_id = kwargs.get('esxi', None)
                self.project_id = kwargs.get('project', None)

            new_machine = Machine('speziyiyeap', '10.1.1.1', 'standalone', cimc=5)  # be careful with cimc_id :)
            db.session.add(new_machine)
            db.session.commit()
            """
            return json.dumps(dict(message="Machine not found", code=400)), 400
    else:
        return json.dumps(dict(message="Unsupported Media Type", code=415)), 415
