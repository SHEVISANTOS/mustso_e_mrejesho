import json
from channels.generic.websocket import AsyncWebsocketConsumer

DASHBOARD_GROUP = "dashboard_broadcast"


class DashboardConsumer(AsyncWebsocketConsumer):
    """Objective 1: pushes a 'something changed' signal to every connected
    dashboard the instant a Feedback item is created/escalated/resolved/etc.
    The client reacts by re-fetching /feedback/data/ (role-scoped, so the
    consumer itself never needs to know who's allowed to see what)."""

    async def connect(self):
        if not self.scope["user"].is_authenticated:
            await self.close()
            return
        await self.channel_layer.group_add(DASHBOARD_GROUP, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(DASHBOARD_GROUP, self.channel_name)

    async def dashboard_message(self, event):
        await self.send(text_data=json.dumps({"type": "refresh"}))


class NotificationConsumer(AsyncWebsocketConsumer):
    """Objective 3: pushes an instant unread-count update to one specific user."""

    async def connect(self):
        user = self.scope["user"]
        if not user.is_authenticated:
            await self.close()
            return
        self.group_name = f"notify_user_{user.id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def notify_message(self, event):
        await self.send(text_data=json.dumps({
            "type": "notification",
            "unread_count": event["unread_count"],
        }))
