#-*- coding: utf-8 -*-
"""
Django settings for HyperKitty.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.8/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'change-this-on-your-production-server'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ADMINS = (
     ('HyperKitty Admin', 'root@localhost'),
)

# Hosts/domain names that are valid for this site; required if DEBUG is False
# See https://docs.djangoproject.com/en/1.8/ref/settings/#allowed-hosts
ALLOWED_HOSTS = [
    "localhost", # Archiving API from Mailman, keep it.
    "lists.your-domain.org",
    # Add here all production URLs you may have.
]

# And for BrowserID too, see
# http://django-browserid.rtfd.org/page/user/settings.html#django.conf.settings.BROWSERID_AUDIENCES
BROWSERID_AUDIENCES = [
    "http://localhost",               # Only useful in debug mode
    "http://localhost:8000",          # Only useful in debug mode
    "https://lists.your-domain.org",  # Your production URL
    # Add here all production URLs you may have.
]

# Mailman API credentials
MAILMAN_REST_API_URL = 'http://localhost:8001'
MAILMAN_REST_API_USER = 'restadmin'
MAILMAN_REST_API_PASS = 'restpass'
MAILMAN_ARCHIVER_KEY = 'SecretArchiverAPIKey'
MAILMAN_ARCHIVER_FROM = ('127.0.0.1', '::1')

# Application definition

INSTALLED_APPS = (
    'hyperkitty',
    # Uncomment the next line to enable the admin:
    'django.contrib.admin',
    # Uncomment the next line to enable admin documentation:
    # 'django.contrib.admindocs',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    #'django.contrib.sites',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'social.apps.django_app.default',
    'rest_framework',
    'django_gravatar',
    'crispy_forms',
    'paintstore',
    'compressor',
    'django_browserid',
    'haystack',
    'django_extensions',
)


MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    #'hyperkitty.middleware.SSLRedirect',
    'hyperkitty.middleware.TimezoneMiddleware',
)

ROOT_URLCONF = 'urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.static',
                'django.template.context_processors.tz',
                'django.template.context_processors.csrf',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'social.apps.django_app.context_processors.backends',
                'social.apps.django_app.context_processors.login_redirect',
                'hyperkitty.context_processors.common',
            ],
        },
    },
]

WSGI_APPLICATION = 'wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.8/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3', # Add 'postgresql_psycopg2', 'mysql', 'sqlite3' or 'oracle'.
        'NAME': os.path.join(BASE_DIR, 'hyperkitty.db'),  # DB name or path to database file if using sqlite3.
        # The following settings are not used with sqlite3:
        'USER': 'hyperkitty',
        'PASSWORD': 'hkpass',
        'HOST': '',                      # Empty for localhost through domain sockets or '127.0.0.1' for localhost through TCP.
        'PORT': '',                      # Set to empty string for default.
    }
    # Example for PostgreSQL (recommanded for production):
    #'default': {
    #    'ENGINE': 'django.db.backends.postgresql_psycopg2',
    #    'NAME': 'database_name',
    #    'USER': 'database_user',
    #    'PASSWORD': 'database_password',
    #    'HOST': 'localhost',
    #}
}


# If you're behind a proxy, use the X-Forwarded-Host header
# See https://docs.djangoproject.com/en/1.8/ref/settings/#use-x-forwarded-host
#USE_X_FORWARDED_HOST = True

# And if your proxy does your SSL encoding for you, set SECURE_PROXY_SSL_HEADER
# see https://docs.djangoproject.com/en/1.8/ref/settings/#secure-proxy-ssl-header
#SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
#SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_SCHEME', 'https')


# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/


# Absolute path to the directory static files should be collected to.
# Don't put anything in this directory yourself; store your static files
# in apps' "static/" subdirectories and in STATICFILES_DIRS.
# Example: "/var/www/example.com/static/"
#STATIC_ROOT = ''
STATIC_ROOT = BASE_DIR + '/static/'

# URL prefix for static files.
# Example: "http://example.com/static/", "http://static.example.com/"
STATIC_URL = '/static/'

# Additional locations of static files
STATICFILES_DIRS = (
    # Put strings here, like "/home/html/static" or "C:/www/django/static".
    # Always use forward slashes, even on Windows.
    # Don't forget to use absolute paths, not relative paths.
    #BASE_DIR + '/static/',
)

# List of finder classes that know how to find static files in
# various locations.
STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
    'compressor.finders.CompressorFinder',
)

# Django 1.6+ defaults to a JSON serializer, but it won't work with django-openid, see
# https://bugs.launchpad.net/django-openid-auth/+bug/1252826
SESSION_SERIALIZER = 'django.contrib.sessions.serializers.PickleSerializer'


LOGIN_URL          = 'hk_user_login'
LOGIN_REDIRECT_URL = 'hk_root'
LOGOUT_URL         = 'hk_user_logout'

# Use the email username as identifier, but truncate it because
# the User.username field is only 30 chars long.
def username(email):
    return email.rsplit('@', 1)[0][:30]
BROWSERID_USERNAME_ALGO = username
BROWSERID_VERIFY_CLASS = "django_browserid.views.Verify"


# If you enable internal authentication, this is the address that the emails
# will appear to be coming from. Make sure you set a valid domain name,
# otherwise the emails may get rejected.
# https://docs.djangoproject.com/en/1.8/ref/settings/#default-from-email
#DEFAULT_FROM_EMAIL = "mailing-lists@you-domain.org"

# If you enable email reporting for error messages, this is where those emails
# will appear to be coming from. Make sure you set a valid domain name,
# otherwise the emails may get rejected.
# https://docs.djangoproject.com/en/1.8/ref/settings/#std:setting-SERVER_EMAIL
#SERVER_EMAIL = 'root@your-domain.org'


# Compatibility with Bootstrap 3
from django.contrib.messages import constants as messages
MESSAGE_TAGS = {
    messages.ERROR: 'danger'
}

# Django Crispy Forms
CRISPY_TEMPLATE_PACK = 'bootstrap3'
CRISPY_FAIL_SILENTLY = not DEBUG


#
# Social auth
#
AUTHENTICATION_BACKENDS = (
    #'social.backends.open_id.OpenIdAuth',
    # http://python-social-auth.readthedocs.org/en/latest/backends/google.html
    #'social.backends.google.GoogleOpenId',
    #'social.backends.google.GoogleOAuth2',
    #'social.backends.twitter.TwitterOAuth',
    'social.backends.yahoo.YahooOpenId',
    'django_browserid.auth.BrowserIDBackend',
    'django.contrib.auth.backends.ModelBackend',
)

# http://python-social-auth.readthedocs.org/en/latest/pipeline.html#authentication-pipeline
SOCIAL_AUTH_PIPELINE = (
    'social.pipeline.social_auth.social_details',
    'social.pipeline.social_auth.social_uid',
    'social.pipeline.social_auth.auth_allowed',
    'social.pipeline.social_auth.social_user',
    'social.pipeline.user.get_username',
    # Associates the current social details with another user account with
    # a similar email address. Disabled by default, enable with care:
    # http://python-social-auth.readthedocs.org/en/latest/use_cases.html#associate-users-by-email
    #'social.pipeline.social_auth.associate_by_email',
    'social.pipeline.user.create_user',
    'social.pipeline.social_auth.associate_user',
    'social.pipeline.social_auth.load_extra_data',
    'social.pipeline.user.user_details',
    'hyperkitty.lib.mailman.add_user_to_mailman',
)



#
# Gravatar
# https://github.com/twaddington/django-gravatar
#
# Gravatar base url.
#GRAVATAR_URL = 'http://cdn.libravatar.org/'
# Gravatar base secure https url.
#GRAVATAR_SECURE_URL = 'https://seccdn.libravatar.org/'
# Gravatar size in pixels.
#GRAVATAR_DEFAULT_SIZE = '80'
# An image url or one of the following: 'mm', 'identicon', 'monsterid', 'wavatar', 'retro'.
#GRAVATAR_DEFAULT_IMAGE = 'mm'
# One of the following: 'g', 'pg', 'r', 'x'.
#GRAVATAR_DEFAULT_RATING = 'g'
# True to use https by default, False for plain http.
#GRAVATAR_DEFAULT_SECURE = True

#
# django-compressor
# https://pypi.python.org/pypi/django_compressor
#
COMPRESS_PRECOMPILERS = (
   ('text/less', 'lessc {infile} {outfile}'),
   ('text/x-scss', 'sassc -t compressed {infile} {outfile}'),
   ('text/x-sass', 'sassc -t compressed {infile} {outfile}'),
)
# On a production setup, setting COMPRESS_OFFLINE to True will bring a
# significant performance improvement, as CSS files will not need to be
# recompiled on each requests. It means running an additional "compress"
# management command after each code upgrade.
# http://django-compressor.readthedocs.io/en/latest/usage/#offline-compression
#COMPRESS_OFFLINE = True

# Needed for debug mode
#INTERNAL_IPS = ('127.0.0.1',)


#
# Full-text search engine
#
HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.whoosh_backend.WhooshEngine',
        'PATH': os.path.join(BASE_DIR, "fulltext_index"),
        # You can also use the Xapian engine, it's faster and more accurate,
        # but requires another library.
        # http://django-haystack.readthedocs.io/en/v2.4.1/installing_search_engines.html#xapian
        # Example configuration for Xapian:
        #'ENGINE': 'xapian_backend.XapianEngine',
    },
}


# A sample logging configuration. The only tangible logging
# performed by this configuration is to send an email to
# the site admins on every HTTP 500 error when DEBUG=False.
# See http://docs.djangoproject.com/en/dev/topics/logging for
# more details on how to customize your logging configuration.
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'mail_admins': {
            'level': 'ERROR',
            'filters': ['require_debug_false'],
            'class': 'django.utils.log.AdminEmailHandler'
        },
        'file':{
            'level': 'INFO',
            #'class': 'logging.handlers.RotatingFileHandler',
            'class': 'logging.handlers.WatchedFileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'hyperkitty.log'),
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django.request': {
            'handlers': ['mail_admins', 'file'],
            'level': 'ERROR',
            'propagate': True,
        },
        'django': {
            'handlers': ['file'],
            'level': 'ERROR',
            'propagate': True,
        },
        'hyperkitty': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        },
    },
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(process)d %(name)s %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    #'root': {
    #    'handlers': ['file'],
    #    'level': 'INFO',
    #},
}


# Using the cache infrastructure can significantly improve performance on a
# production setup. This is an example with a local Memcached server.
#CACHES = {
#    'default': {
#        'BACKEND': 'django.core.cache.backends.memcached.PyLibMCCache',
#        'LOCATION': '127.0.0.1:11211',
#    }
#}


# When DEBUG is True, don't actually send emails to the SMTP server, just store
# them in a directory. This way you won't accidentally spam your mailing-lists
# while you're fiddling with the code.
if DEBUG == True:
    EMAIL_BACKEND = 'django.core.mail.backends.filebased.EmailBackend'
    EMAIL_FILE_PATH = os.path.join(BASE_DIR, 'emails')


#
# HyperKitty-specific
#

APP_NAME = 'List Archives'

# Allow authentication with the internal user database?
# By default, only a login through Persona or your email provider is allowed.
USE_INTERNAL_AUTH = False

# Use SSL when logged in. You need to enable the SSLRedirect middleware for
# this feature to work.
#USE_SSL = True

# Only display mailing-lists from the same virtual host as the webserver
FILTER_VHOST = False


try:
    from settings_local import *
except ImportError:
    pass