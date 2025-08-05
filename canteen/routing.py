from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/admin/notifications/$', consumers.AdminNotificationConsumer.as_asgi()),
    re_path(r'ws/user/notifications/(?P<user_id>\\d+)/$', consumers.UserNotificationConsumer.as_asgi()),
]
