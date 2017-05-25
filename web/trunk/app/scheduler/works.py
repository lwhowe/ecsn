import logging
import multiprocessing
from datetime import datetime, timedelta
from sqlalchemy import and_, or_
from .. import db, celery
from ..libs import lib
from ..libs.lib import StandalonePower
from ..models import Controller, Machine, DataState, Tasks

log = logging.getLogger(__name__)


@celery.task(bind=True)
def runit_queue(self):
    # idle machines goes to waiting list for shutdown
    log.info(get_task_info(self))
    machine_list = get_valid_machines()
    idle_list = check_for_idle(machine_list)
    machines = list(lib.chunks(idle_list, 10))  # break list to smaller chunks of 10 for concurrency
    for hold in machines:
        queue_shutdown_jobs.apply_async(kwargs=dict(machines=hold))


@celery.task(bind=True)
def runit_shutdown(self):
    log.info(get_task_info(self))
    tasks = Tasks.query.filter(and_(Tasks.type == 'auto-shut', Tasks.date_deleted.is_(None),
                                    Tasks.date_assign <= datetime.utcnow(),
                                    Tasks.date_assign > datetime.utcnow() - timedelta(minutes=30))).all()
    for task in tasks:
        shutdown_jobs.apply_async(args=[task.name, task.machine_id])


@celery.task(bind=True)
def queue_shutdown_jobs(self, machines=None, delay=timedelta(hours=1)):
    """Add and queue shutdown task into database to allow 1 hour early notification to the servers"""
    log.info(get_task_info(self))
    for machine_id, hostname in machines:
        # cleanup expired tasks that did not get executed properly after 60 minutes
        tasks = Tasks.query.filter(and_(Tasks.type == 'auto-shut', Tasks.machine_id == machine_id,
                                        Tasks.date_assign < datetime.utcnow() - timedelta(hours=1),
                                        Tasks.date_deleted.is_(None))).all()
        if tasks:
            for task in tasks:
                task.date_deleted = datetime.utcnow()
                task.status = 'expired'
            db.session.commit()
            log.debug(get_worker_info() + "{}(id:{}): Found and cancelled {} expired tasks"
                      .format(hostname, machine_id, len(tasks)))

        # add new shutdown task if non pending
        if not Tasks.query.filter(and_(Tasks.type == 'auto-shut', Tasks.machine_id == machine_id,
                                       Tasks.date_assign >= datetime.utcnow() - timedelta(hours=1),
                                       Tasks.date_deleted.is_(None))).first():
            # ensure there are no active freeze task by user
            if not Tasks.query.order_by(Tasks.date_created.desc()) \
                    .filter(and_(Tasks.machine_id == machine_id, Tasks.type == 'freeze',
                                 Tasks.date_deleted.is_(None), Tasks.date_assign >= datetime.utcnow())).first():
                db.session.add(Tasks(self.request.id, 'auto-shut', machine_id, datetime.utcnow() + delay,
                                     status='waiting'))
                db.session.commit()
                log.debug(get_worker_info() + "{}(id:{}): Added new 'auto-shut' task".format(hostname, machine_id))
        else:
            log.debug(get_worker_info() + "{}(id:{}): Already has a pending task".format(hostname, machine_id))


@celery.task(bind=True)
def shutdown_jobs(self, name, machine_id):
    """Go through the Tasks db and look for machine to shutdown after the queue time expires"""
    log.info(get_task_info(self))
    tasks = Tasks.query.filter_by(name=name, machine_id=machine_id)\
        .filter(and_(Tasks.date_deleted.is_(None), or_(Tasks.type.is_('auto-shut'), Tasks.type.is_('freeze')))) \
        .order_by(Tasks.date_created.desc()).limit(2)
    if tasks:
        for task in tasks:
            if task.type == 'freeze' and task.date_assign >= datetime.utcnow():
                break
        else:
            # tasks will have both auto-shut and freeze task
            for task in tasks:
                if task.type == 'auto-shut':
                    machine = Machine.query.get(task.machine_id)
                    if machine.type == 'standalone':
                        controller = Controller.query.get(machine.cimc_id)
                        try:
                            message = "Connecting to cimc ip '{}'".format(controller.ip)
                            log.debug(get_worker_info() + 'Machine-{}: '.format(machine.id) + message)
                            standalone = StandalonePower(controller.ip, controller.user, controller.password)
                            standalone.cookie = standalone.controller_login(standalone.host, standalone.username,
                                                                            standalone.password)
                            if standalone.cookie:
                                state = standalone.controller_status(standalone.host, standalone.cookie)
                                if state == 'on':
                                    # standalone.controller_power(standalone.host, standalone.cookie, 'soft-shut-down')
                                    machine.state = 0  # change to power off state
                                    machine.status = 0  # change to idle status
                                    task.status = 'success'  # update task status
                                    # add auto-shut state
                                    db.session.add(DataState(machine.id, db.func.current_timestamp(), '10'))
                                    message = 'Shutdown succeeded'
                                    log.debug(get_worker_info() + 'Machine-{}: '.format(machine.id) + message)
                                elif state == 'off':
                                    machine.state = 0  # change to power off state
                                    machine.status = 0  # change to idle status
                                    task.status = 'skip'  # update task status
                                    message = 'Already powered off'.format(machine_id)
                                    log.debug(get_worker_info() + 'Machine-{}: '.format(machine.id) + message)
                                else:
                                    task.status = 'error'  # update task status
                                    message = "Error: Unknown state '{}'".format(state)
                                    log.debug(get_worker_info() + 'Machine-{}: '.format(machine.id) + message)
                                standalone.controller_logout(standalone.host, standalone.cookie)
                            else:
                                task.status = 'error'  # update task status
                                message = 'Error: Retrieving xml cookie'.format(machine_id)
                                log.debug(get_worker_info() + 'Machine-{}: '.format(machine.id) + message)
                        except Exception, e:
                            task.status = 'error'  # update task status
                            log.debug(get_worker_info() + 'Machine-{}: '.format(machine.id) + str(e))
                    else:
                        task.status = 'error'  # update task status
                        message = "Error: Unknown machine type '{}'".format(machine.type)
                        log.debug(get_worker_info() + 'Machine-{}: '.format(machine.id) + message)
                    task.date_deleted = db.func.current_timestamp()
                    db.session.commit()
                    break  # only for auto-shut task


def get_task_info(obj, prefix=None):
    if prefix:
        return get_worker_info() + "{} Task {}[{}]".format(prefix, obj.request.task.split('.')[-1], obj.request.id)
    else:
        return get_worker_info() + "Task {}[{}]".format(obj.request.task.split('.')[-1], obj.request.id)


def get_worker_info():
    return "{}: ".format(multiprocessing.current_process().name)


def get_valid_machines():
    standalone_list = db.session.query(Machine.id, Machine.host) \
        .filter(and_(Machine.type == 'standalone', Machine.cimc_id.isnot(None),
                     Machine.date_deleted.is_(None))).all()
    virtual_list = db.session.query(Machine.id, Machine.host) \
        .filter(and_(Machine.type == 'virtual', Machine.cimc_id.isnot(None),
                     Machine.esxi_id.isnot(None), Machine.date_deleted.is_(None))).all()
    return standalone_list + virtual_list


def check_for_idle(machines, current_time=None, duration=timedelta(hours=12), interval=timedelta(minutes=5)):
    idle_list = list()
    current_time = current_time if current_time else datetime.utcnow()
    for (machine_id, hostname) in machines:
        dataset = DataState.query.filter_by(machine_id=machine_id)\
            .filter(DataState.date_entry >= current_time - duration)\
            .order_by(DataState.date_entry.desc()).all()
        if dataset:
            dataset_datetime = list()
            for data in dataset:
                if data.state == '0':
                    dataset_datetime.append(data.date_entry)
                else:
                    break
            else:
                # subtract current and next element to get the minimum time gap
                dataset_timedelta = [dataset_datetime[i - 1] - x for i, x in enumerate(dataset_datetime)][1:]

                current_interval = min(dataset_timedelta)
                if current_interval > interval+timedelta(minutes=5):
                    continue
                elif current_interval > interval:
                    interval = current_interval

                # calculate the expected percentage
                total_num = duration.total_seconds() / interval.total_seconds()
                total_pct = len(dataset_datetime) / total_num
                log.debug(get_worker_info() + "{}: Percentage {}% from {}/{} of record[s] in {} minutes"
                          .format(hostname, round(total_pct * 100, 2), len(dataset_datetime), int(total_num),
                                  duration.seconds/60))
                if total_pct <= 0.9:
                    continue

                # finalize the idle machine list
                idle_list.append((machine_id, hostname))
    return idle_list
