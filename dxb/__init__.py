from __future__ import absolute_import, unicode_literals

# Import the Celery application so it gets registered when Django starts
from .celery import app as celery_app

__all__ = ('celery_app',)