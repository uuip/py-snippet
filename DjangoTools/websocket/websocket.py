import json
import traceback

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from utils.async_yield import sync_generator_to_async

from .tasks.nft import calc_nft_rate, group_name


class AsyncPublish(AsyncJsonWebsocketConsumer):
    groups = [group_name]

    async def connect(self):
        # self.room_name = self.scope['url_route']['kwargs']['room_name']
        # await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()
        try:
            async for data in sync_generator_to_async(calc_nft_rate)():
                await self.send_json(data)
        except BaseException:
            traceback.print_exc()

    async def disconnect(self, close_code):
        pass
        # await self.channel_layer.group_discard(self.group, self.channel_name)

    async def receive_json(self, content, **kwargs):
        pass
        # assert isinstance(self.channel_layer, RedisChannelLayer)
        # await self.channel_layer.group_send(
        #     self.group,
        #     {
        #         'type': 'broadcast_message',
        #         'channel': self.group,
        #         'message': {"time": time.time()}
        #     }
        # )

    async def broadcast_message(self, event):
        await self.send_json(event["message"])

    @classmethod
    async def decode_json(cls, text_data):
        try:
            return json.loads(text_data)
        except:
            return {"data": ""}
