from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.core.exceptions import ObjectDoesNotExist

from django.contrib.auth import get_user_model
from event.models import Event, EventAttendance, EventComment, EventMedia
from event.serializers import EventSerializer

from profiles . models import Profile

from notification.models import NotificationType

from notification.utils import create_notification, send_notification_email

import logging


logger = logging.getLogger(__name__)




