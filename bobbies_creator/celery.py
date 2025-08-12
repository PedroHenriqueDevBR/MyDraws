import os

from celery import Celery
from decouple import config

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bobbies_creator.settings")

app = Celery("bobbies_creator")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

app.conf.broker_url = config("CELERY_BROKER_URL")  # type: ignore
app.conf.result_backend = config("CELERY_RESULT_BACKEND")  # type: ignore
