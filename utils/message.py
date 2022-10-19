from abc import ABC

from nextcord.channel import TextChannel
from nextcord.message import Message
from nextcord.ext import commands

from utils.settings import settings


class MainMessageUtils(ABC):

    @staticmethod
    async def fetch_channel_n_msg(ctx: commands.Context, json_msg_name: str) -> tuple[TextChannel, Message]:
        """Raise Excpetion if channel or message not exists."""

        msg_settings: dict = settings.get(json_msg_name)
        message_id = msg_settings.get('MSG_ID')
        channel_id = msg_settings.get('CHANNEL_ID')
        channel = ctx.guild.get_channel(channel_id)
        msg = await channel.fetch_message(message_id)
        return (channel, msg)
