from matplotlib.table import Cell
from abc import ABC
import textwrap

from nextcord.message import Message
import nextcord


class BingoUtils(ABC):

    @staticmethod
    def split_words(text: str, *, max_chars: int = 13) -> str:
        """Wrap words spliting it by max_chars."""
        return '\n'.join(textwrap.wrap(text, max_chars))

    @staticmethod
    def get_text_from_cell(cell: Cell, *, add_bslsh_bfr_strsk: bool = False) -> str:
        """Return text from cell, where new lines have been replaced by space.

        Parameters
        ----------
        add_bslsh_bfr_strsk: `bool` - Add backslash before asterisk.
            It is usefull if the text will be sending on in a Discord message.

        """
        text = cell.get_text().get_text().replace('\n', ' ')

        if add_bslsh_bfr_strsk:
            text = text.replace('*', '\\*')

        return text

    @staticmethod
    async def get_message_to_load(message: Message) -> int | None:
        """|coro|

        Get message_id where the bingo table was sent.

        The message_id can be obtained from message reference
        or sent as message content.

        If message_id is wrong, returns None.
        """

        ref_message = message.reference
        if ref_message is not None:
            return ref_message.message_id

        try:
            message_id = int(message.content)
        except ValueError:
            return None

        try:
            message = await message.channel.fetch_message(message_id)
        except nextcord.errors:
            return None

        return message_id
