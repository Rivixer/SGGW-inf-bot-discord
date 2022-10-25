import matplotlib.pyplot as plt
import textwrap
import random


from nextcord.ext import commands
import nextcord

from utils.checks import is_bot_channel_or
from utils.console import Console


_TABLE_PNG_PATH = 'bingo.png'


class BingoRPiSCog(commands.Cog):

    __slots__ = '__bot',

    __bot: commands.Bot

    def __init__(self, bot: commands.Bot) -> None:
        self.__bot = bot

    def __generate_bingo(self) -> nextcord.File:
        try:
            with open('files/bingo.txt', encoding='utf-8') as f:
                words = f.readlines()
        except Exception as e:
            Console.error(
                'Nie udało się załadować pliku files/bingo.txt',
                exception=e
            )
            table = plt.table(
                cellText=(('Coś',), ('poszło',), ('nie',), ('tak!',)),
                cellLoc='center',
                loc='center'
            )
        else:
            random.shuffle(words)

            def wrap_text(words: list) -> list:
                return ['\n'.join(textwrap.wrap(i, 12)) for i in words]

            table = plt.table(
                cellText=(
                    (wrap_text(words[:4])),
                    (wrap_text(words[4:8])),
                    (wrap_text(words[8:12])),
                    (wrap_text(words[12:16]))
                ),
                cellLoc='center',
                loc='center'
            )

        table.scale(1.5, 5.5)

        plt.axis('off')
        plt.grid('off')
        plt.title('R P i S', fontsize=25)

        plt.savefig(
            _TABLE_PNG_PATH,
            bbox_inches="tight",
            dpi=300
        )

        return nextcord.File(_TABLE_PNG_PATH)

    @commands.group(name='bingo')
    @is_bot_channel_or('RPIS_CHANNEL_ID')
    async def _bingo(self, *args) -> None:
        if len(args) > 1:
            return

        ctx: commands.Context = args[0]

        bingo_png = self.__generate_bingo()
        await ctx.send(file=bingo_png)


def setup(bot: commands.Bot):
    bot.add_cog(BingoRPiSCog(bot))
