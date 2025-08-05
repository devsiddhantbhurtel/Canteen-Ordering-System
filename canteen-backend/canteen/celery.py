import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'canteen.settings')

app = Celery('canteen')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()

# Configure periodic tasks
app.conf.beat_schedule = {
    'process-order-queue': {
        'task': 'orders.tasks.process_order_queue',
        'schedule': 60.0,  # Run every minute
    },
    'update-order-priorities': {
        'task': 'orders.tasks.update_order_priorities',
        'schedule': 300.0,  # Run every 5 minutes
    },
    'cleanup-acknowledged-orders': {
        'task': 'orders.tasks.cleanup_acknowledged_orders',
        'schedule': crontab(hour=0, minute=0),  # Run daily at midnight
    },
} 