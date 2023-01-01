from nextcord.embeds import Embed
from nextcord.emoji import Emoji

from models.embed_model import EmbedModel

from .project_model import ProjectModel


class ProjectEmbed(EmbedModel):

    _model: ProjectModel

    def generate_embed(self) -> Embed:
        return super().generate_embed()

    @property
    def reactions(self) -> list[Emoji | str]:
        return []
