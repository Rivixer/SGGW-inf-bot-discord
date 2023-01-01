from nextcord.colour import Colour
from nextcord.embeds import Embed
from nextcord.emoji import Emoji

from models.embed_model import EmbedModel

from .informations_model import InformationsModel


class InformationsEmbed(EmbedModel):

    _model: InformationsModel

    def generate_embed(self) -> Embed:
        return super().generate_embed()

    @property
    def reactions(self) -> list[Emoji | str]:
        return []
