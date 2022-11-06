from nextcord.ext import commands

from utils.settings import settings


def has_admin_role():
    def predicate(ctx: commands.Context):
        if guild := ctx.guild:
            admin_role = guild.get_role(settings.get('ADMIN_ROLE_ID'))
            return admin_role in ctx.author.roles
        return False
    return commands.check(predicate)


def is_bot_channel():
    def predicate(ctx: commands.Context):
        if guild := ctx.guild:
            bot_channel = guild.get_channel(settings.get('BOT_CHANNEL_ID'))
            return bot_channel == ctx.channel
        return False
    return commands.check(predicate)


def is_channel(*setting_names):
    def predicate(ctx: commands.Context):
        for setting_name in setting_names:
            id = settings.get(setting_name)
            if ctx.guild.get_channel(id) == ctx.channel:
                return True
        return False
    return commands.check(predicate)
