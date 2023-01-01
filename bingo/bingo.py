from nextcord.message import Message
from nextcord.ext import commands

from utils.checks import has_admin_role
from utils.console import Console

from .bingo_table_controller import BingoTableController
from .bingo_input_controller import BingoInputController
from .bingo_settings import BingoSettings
from .bingo_utils import BingoUtils


class Bingo(commands.Cog):

    __slots__ = (
        '__bot',
        '__settings',
        '__channel_id',
        '__controller',
        '__input_ctrl',
    )

    __bot: commands.Bot
    __settings: BingoSettings
    __channel_id: int
    __controller: BingoTableController
    __input_ctrl: BingoInputController

    def __init__(self, bot: commands.Bot, settings: BingoSettings) -> None:
        self.__bot = bot
        self.__settings = settings

        with open(settings.dir_path / 'channel_id.txt', 'r') as f:
            self.__channel_id = int(f.read())

        try:
            self.__controller = BingoTableController.load(
                settings.dir_path
            )
        except Exception as e:
            Console.error(
                'Nie udało się załadować bingo.',
                exception=e
            )
            self.__controller = BingoTableController(settings)

        self.__input_ctrl = BingoInputController(
            self.__controller, settings
        )

    @commands.Cog.listener()
    async def on_message(self, message: Message) -> None:
        await self.__input_ctrl.on_message(message)

    @commands.command(name='bingo')
    async def _bingo(self, ctx: commands.Context, *, arg) -> None:
        if ctx.channel.id == self.__channel_id:
            await self.__input_ctrl.bingo_command(ctx, arg)

    @has_admin_role()
    @commands.command(name='bingo_load')
    async def _bingo_load(self, ctx: commands.Context, *_) -> ...:
        msg_id = await BingoUtils.get_message_to_load(ctx.message)

        if msg_id is None:
            return await ctx.reply('Niepoprawne id wiadomości.')

        ctrl = BingoTableController.load_from_msg(
            msg_id, self.__settings.dir_path
        )

        if ctrl is None:
            return await ctx.reply('Błąd podczas ładowania.')

        self.__controller = ctrl
        self.__input_ctrl = BingoInputController(
            self.__controller, self.__settings
        )

        await self.__input_ctrl.reply_png(ctx.message)
