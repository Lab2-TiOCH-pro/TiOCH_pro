import os
from celery import Celery
from dotenv import load_dotenv, find_dotenv

# Load environment variables
load_dotenv(find_dotenv())

# Celery broker and backend configuration
broker = os.getenv("CELERY_BROKER_URL", "amqp://guest:guest@localhost:5672//")
backend = os.getenv("CELERY_RESULT_BACKEND", "rpc://")

# Initialize Celery app and include the tasks module so tasks are registered
celery = Celery(__name__, broker=broker, backend=backend, include=['app.tasks'])
# Track task start events
celery.conf.task_track_started = True
# Automatically discover tasks from the included modules
celery.autodiscover_tasks(['app.tasks']) 