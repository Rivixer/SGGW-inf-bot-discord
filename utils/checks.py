from typing import Any
import json

from nextcord.ext import commands


try:
    with open('settings.json') as f:
        settings: dict[str, Any] = json.load(f)
except Exception as e:
    settings = dict()
    print(e)


def has_admin_role():
    def predicate(ctx: commands.Context):
        admin_role = ctx.guild.get_role(settings.get('ADMIN_ROLE_ID'))
        return admin_role in ctx.author.roles
    return commands.check(predicate)


def is_bot_channel():
    def predicate(ctx: commands.Context):
        bot_channel = ctx.guild.get_channel(settings.get('BOT_CHANNEL_ID'))
        return bot_channel == ctx.channel
    return commands.check(predicate)
