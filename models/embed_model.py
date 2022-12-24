from abc import ABC, abstractmethod

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

    @property
    @abstractmethod
    def reactions(self) -> list[Emoji | str]:
        """Returns `list[Emoji | str]`
            with reactions to be added in embed.
        """
