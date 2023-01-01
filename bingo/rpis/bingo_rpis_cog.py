from nextcord.ext import commands

from ..bingo_settings import *
from ..bingo import Bingo


_SETTINGS = BingoSettings(
    folder_name='rpis',
    cell_colour='#5FC377',
    cell_colour_checked='#999999',
    index_colour='#696969',
    win_colour='#A0A000',
    dim_cols=5,
    dim_rows=5,
    way_to_win=WayToWinBingo.ONELINE
)


class BingoRPiSCog(Bingo):
    pass


def setup(bot: commands.Bot):
    bot.add_cog(BingoRPiSCog(bot, _SETTINGS))
