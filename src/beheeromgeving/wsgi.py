"""
WSGI config for Beheeromgeving Catalogus project.

It exposes the WSGI callable as a module-level variable named ``application``.
"""

import os

from django.conf import settings
from django.core.wsgi import get_wsgi_application
from whitenoise import WhiteNoise

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "beheeromgeving.settings")

application = get_wsgi_application()
application = WhiteNoise(application, root=settings.STATIC_ROOT)
