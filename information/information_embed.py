from nextcord.colour import Colour
from nextcord.embeds import Embed
from nextcord.emoji import Emoji

from models.embed_model import EmbedModel

from .information_model import InformationModel


class InformationEmbed(EmbedModel):

    _model: InformationModel

    def generate_embed(self) -> Embed:
        return super().generate_embed()

    @property
    def reactions(self) -> list[Emoji | str]:
        return []
