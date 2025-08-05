import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import AnonymousUser
from .models import Order
from .serializers import OrderSerializer
from asgiref.sync import sync_to_async
from django.contrib.auth.models import User

class OrderTrackingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.order_id = self.scope['url_route']['kwargs']['order_id']
        self.room_group_name = f'order_{self.order_id}'

        # Get token from query string
        query_string = self.scope.get('query_string', b'').decode()
        token = None
        if query_string:
            params = dict(param.split('=') for param in query_string.split('&'))
            token = params.get('token')

        if token:
            # Verify token and get user
            user = await self.get_user_from_token(token)
            if user:
                # Join room group
                await self.channel_layer.group_add(
                    self.room_group_name,
                    self.channel_name
                )
                await self.accept()
                return

        # If no valid token, close connection
        await self.close()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """
        Receive message from WebSocket.
        """
        try:
            text_data_json = json.loads(text_data)
            message = text_data_json['message']

            # Send message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'order_status_update',
                    'message': message
                }
            )
        except json.JSONDecodeError:
            print(f"Error decoding JSON: {text_data}")
        except KeyError:
            print(f"Missing 'message' key in data: {text_data}")

    async def order_status_update(self, event):
        """
        Receive message from room group and send to WebSocket.
        """
        message = event['message']

        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message
        }))

    @sync_to_async
    def get_user_from_token(self, token_key):
        try:
            token = Token.objects.get(key=token_key)
            return token.user
        except Token.DoesNotExist:
            return None

    @database_sync_to_async
    def get_order(self, order_id):
        try:
            order = Order.objects.get(id=order_id)
            serializer = OrderSerializer(order)
            return serializer.data
        except Order.DoesNotExist:
            return None 