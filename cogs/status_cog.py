from nextcord import Activity, ActivityType
from nextcord.ext import commands
from utils.checks import has_admin_role, is_bot_channel

from utils.console import Console


class StatusCog(commands.Cog):

    __slots__ = '__bot',

    __bot: commands.Bot

    def __init__(self, bot: commands.Bot) -> None:
        self.__bot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        file_path = 'status.txt'

        try:
            with open(file_path, encoding='utf-8') as f:
                status = f.read()
        except Exception as e:
            Console.error(
                f'Nie udało się wczytać pliku {file_path}',
                exception=e
            )

        await self.__bot.change_presence(
            activity=Activity(
                name=status,
                type=ActivityType.playing
            )
        )

    @is_bot_channel()
    @has_admin_role()
    @commands.command(
        name='status',
        brief='Change bot status',
        description='Only on the bot-channel.'
    )
    async def _status(self, ctx: commands.Context, *text) -> None:
        try:
            with open('status.txt', 'w', encoding='utf-8') as f:
                f.write(' '.join(text))
        except Exception as e:
            return await ctx.send(
                f'{ctx.author.mention} Coś poszło nie tak!\n{e}'
            )

        await self.__bot.change_presence(
            activity=Activity(
                name=' '.join(text),
                type=ActivityType.playing
            )
        )


def setup(bot: commands.Bot):
    bot.add_cog(StatusCog(bot))
