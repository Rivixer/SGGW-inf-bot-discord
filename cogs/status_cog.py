from nextcord import Activity, ActivityType
from nextcord.ext import commands


class StatusCog(commands.Cog):

    __slots__ = '__bot',

    __bot: commands.Bot

    def __init__(self, bot: commands.Bot) -> None:
        self.__bot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        try:
            with open('status.txt', encoding='utf-8') as f:
                status = f.read()
        except Exception:
            return

        await self.__bot.change_presence(
            activity=Activity(
                name=status,
                type=ActivityType.playing
            )
        )

    @commands.command(name='status')
    async def _status(self, ctx: commands.Context, *text) -> None:
        await ctx.message.delete()

        try:
            with open('status.txt', 'w', encoding='utf-8') as f:
                f.write(' '.join(text))
        except Exception as e:
            return await ctx.send(
                f'{ctx.author.mention} Something went wrong!\n{e}',
                delete_after=15
            )

        await self.__bot.change_presence(
            activity=Activity(
                name=' '.join(text),
                type=ActivityType.playing
            )
        )


def setup(bot: commands.Bot):
    bot.add_cog(StatusCog(bot))
