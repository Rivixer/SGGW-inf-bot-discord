from dataclasses import dataclass
import re

from nextcord.ext import commands
from nextcord.message import Message

from sggw_bot import BOT_PREFIX

from .bingo_table_controller import BingoTableController
from .bingo_settings import BingoSettings
from .bingo_table_exceptions import *


@dataclass(slots=True)
class BingoInputController:

    __table_ctrl: BingoTableController
    __settings: BingoSettings

    async def on_message(self, message: Message) -> None:
        """|coro|"""

        if message.content.lower() in ('new', 'new+'):
            return await self.__new(message)

        if re.match(self.__is_field_regex, message.content):
            return await self.__mark_phrase(message)
        if re.match('-' + self.__is_field_regex, message.content):
            return await self.__unmark_phrase(message)

    async def bingo_command(self, ctx: commands.Context, arg: str) -> None:
        """|coro|

        Reply to the message, that bingo command is deprecated.
        """

        await ctx.message.reply(
            f'Aby ułatwić pisanie komend, '
            f'usunęliśmy przedrostek `{BOT_PREFIX}bingo`.\n'
            f'Napisz po prostu: `{arg}`'
        )

    @property
    def __is_field_regex(self) -> str:
        """Get regex to validate if message content is a field."""

        dim_rows = self.__settings.dim_rows
        col_index = chr(self.__settings.dim_cols + 64)
        return f'[A-{col_index}a-{col_index.lower()}][1-{dim_rows}]'

    async def reply_png(self, message: Message) -> None:
        """|coro|

        Save bingo image as png.

        Reply on the message by sending a bingo image with content as last action.

        Do not ping the author in message.

        Serialize TableController.
        """

        self.__table_ctrl.save_png()
        file = self.__table_ctrl.dc_file_png

        msg = await message.reply(
            self.__table_ctrl.last_action,
            mention_author=False,
            file=file,
        )

        self.__table_ctrl.serialize(msg.id)

    async def __new(self, message: Message) -> ...:
        """|coro|"""

        if not self.__table_ctrl.can_generate_new and message.content.lower() != 'new+':
            return await message.reply(
                'Ostatnie bingo było używane mniej niż 15 min temu.\n'
                'Jeśli mimo to chcesz wygenerować nowe, napisz `new+`'
            )

        self.__table_ctrl.new()
        self.__table_ctrl.generate()
        await self.reply_png(message)

    async def __mark_phrase(self, message: Message) -> ...:
        """|coro|"""

        field = message.content

        try:
            self.__table_ctrl.mark_phrase(field)
        except CellIsMarked:
            return await message.reply(
                'To pole jest już zaznaczone.\n'
                f'Aby je odznaczyć napisz `-{field}`'
            )
        except KeyError:
            ...

        await self.reply_png(message)

    async def __unmark_phrase(self, message: Message) -> ...:
        """|coro|"""

        field = message.content[1:]

        try:
            self.__table_ctrl.unmark_phrase(field)
        except CellIsNotMarked:
            return await message.reply(
                'To pole nie jest zaznaczone.\n'
                f'Aby je zaznaczyć napisz `{field}`'
            )
        except KeyError:
            ...

        await self.reply_png(message)
