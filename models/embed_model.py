from abc import ABC, abstractmethod
from datetime import datetime

from nextcord.colour import Colour
from nextcord.embeds import Embed
from nextcord.emoji import Emoji

from .model import Model


class EmbedModel(ABC):

    __slots__ = (
        '_model',
    )

    _model: Model

    def __init__(self, model: Model) -> None:
        self._model = model

    @abstractmethod
    def generate_embed(self) -> Embed:
        """Generates embed."""

        title = self._model.data.get('embed', {}).get('title')
        description = self._model.data.get('embed', {}).get('description')

        if isinstance(description, str):
            description = description.format(CURRENT_TIME=self._current_time)

        colour = self._model.data.get('embed', {}).get('colour')

        if colour is not None:
            try:
                colour = tuple(int(colour[i:i+2], 16) for i in (0, 2, 4))
            except:
                colour = None

        embed = Embed(
            title=title or 'Brak tytułu',
            description=description or 'Brak opisu',
            color=Colour.from_rgb(*colour) if colour else Colour.dark_grey()
        )

        for key, value in self._model.data.get('embed', {}).get('fields', {}).items():
            embed.add_field(name=key, value=value, inline=False)

        thumbnail = self._model.data.get('embed', {}).get('thumbnail')

        if thumbnail is not None:
            embed.set_thumbnail(thumbnail)

        return embed

    @property
    @abstractmethod
    def reactions(self) -> list[Emoji | str]:
        """Returns `list[Emoji | str]`
            with reactions to be added in embed.
        """

    @property
    def _current_time(self) -> str:
        """Returns current time in format %d.%m.%Y %H:%M"""
        return datetime.now().strftime("%d.%m.%Y %H:%M")
