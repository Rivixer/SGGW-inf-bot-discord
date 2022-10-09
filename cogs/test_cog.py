from nextcord.ext import commands

from utils.checks import has_admin_role, is_bot_channel


class TestCog(commands.Cog):
    __slots__ = '__bot'

    def __init__(self, bot: commands.Bot) -> None:
        self.__bot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        print('Bot załadowany!')

    @has_admin_role()
    @is_bot_channel()
    @commands.command(name='print')
    async def _print(self, _, *args):
        print('\n'.join(args))


def setup(bot: commands.Bot):
    bot.add_cog(TestCog(bot))
