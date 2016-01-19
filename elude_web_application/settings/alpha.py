from elude_web_application.settings.base import *

DEBUG = False
INSTALLED_APPS += (

)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': DATABASE_NAME,
        'USER': ALPHA_DATABASE_USER_NAME,
        'PASSWORD': ALPHA_DATABASE_PASSWORD,
        'HOST': MYSQL_HOST_NAME,
    }
}
