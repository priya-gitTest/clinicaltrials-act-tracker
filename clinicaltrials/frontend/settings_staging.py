"""
Django settings for clinicaltrials project.

Generated by 'django-admin startproject' using Django 1.10.5.

For more information on this file, see
https://docs.djangoproject.com/en/1.10/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.10/ref/settings/
"""
from frontend.settings import *

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'formatters': {
        'verbose': {
            'format': ('%(asctime)s %(levelname)s [%(name)s:%(lineno)s] '
                       '%(module)s %(process)d %(thread)d %(message)s')
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'applogfile': {
            'level':'DEBUG',
            'class':'logging.handlers.RotatingFileHandler',
            'formatter': 'verbose',
            'filename': os.path.join(PROJECT_ROOT, 'clinicialtrials.log'),
            'maxBytes': 1024*1024*15, # 15MB
            'backupCount': 10,
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins', 'applogfile'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'clinicaltrials': {
            'handlers': ['applogfile'],
            'level': 'DEBUG',
        },
    }
}
