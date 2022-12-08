from nextcord.ext import commands

from ..bingo_settings import BingoSettings
from ..bingo import Bingo


_SETTINGS = BingoSettings(
    folder_name='rpis',
    cell_colour='#5FC377',
    cell_colour_checked='#999999',
    index_colour='#696969',
    index_colour_checked='#A0A000',
    dim_cols=4,
    dim_rows=4
)


class BingoRPiSCog(Bingo):
    pass


def setup(bot: commands.Bot):
    bot.add_cog(BingoRPiSCog(bot, _SETTINGS))
