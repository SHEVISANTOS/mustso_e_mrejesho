"""
ASGI config for must_mrejesho project.

Serves plain HTTP through Django as usual, and WebSocket connections
(for the live dashboard + notification bell) through Channels.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'must_mrejesho.settings')

# Must be created before importing anything that touches models/routing,
# so Django's app registry is ready first.
django_asgi_app = get_asgi_application()

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

import notifications.routing

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(notifications.routing.websocket_urlpatterns)
        )
    ),
})
