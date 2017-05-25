from app import app
from app.libs import lib
from datetime import datetime
from flask_script import Manager
from flask_migrate import MigrateCommand
from app.scheduler import works

manager = Manager(app)
manager.add_command('db', MigrateCommand)


@manager.command
def run_runit_queue():
    """ Dummy test and validation for runit_queue scheduler function

    :return:
    """
    machine_list = works.get_valid_machines()
    print machine_list
    idle_list = works.check_for_idle(machine_list, current_time=datetime(2017, 01, 10, 2, 53, 00))
    print idle_list
    machines = list(lib.chunks(idle_list, 10))  # break list to smaller chunks of 10 for concurrency
    for hold in machines:
        works.queue_shutdown_jobs.apply_async(kwargs=dict(machines=hold))

if __name__ == '__main__':
    manager.run()