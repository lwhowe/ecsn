setting = {
    'version': 1,
    'disable_existing_loggers': False,  # fixes if module are imported before logging.config
    'formatters': {
        'standard': {
            'format': '%(asctime)s: [%(levelname)s]: %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
        'celery': {
            'format': '[%(asctime)s: %(levelname)s]: %(message)s',
        },
    },
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'standard',
            'filename': 'app/logs/app.log',
            'mode': 'a',
            'maxBytes': 2097152,
            'backupCount': 10,
        },
        'file_api': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'standard',
            'filename': 'app/api/logs/api.log',
            'mode': 'a',
            'maxBytes': 2097152,
            'backupCount': 10,
        },
        'file_scheduler': {
            'level': 'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'celery',
            'filename': 'app/scheduler/logs/celery.log',
            'mode': 'a',
            'maxBytes': 2097152,
            'backupCount': 10,
        },
    },
    'loggers': {
        'app': {
            'handlers': ['file'],
            'level': 'DEBUG',
        },
        'app.api': {
            'handlers': ['file_api'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'app.scheduler': {
            'handlers': ['file_scheduler'],
            'level': 'DEBUG',
            'propagate': False,
        }
    }
}
