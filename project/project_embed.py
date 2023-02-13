from nextcord.embeds import Embed
from nextcord.emoji import Emoji

from utils.line_counter import LineCounter
from models.embed_model import EmbedModel

from .project_model import ProjectModel


class ProjectEmbed(EmbedModel):

    _model: ProjectModel

    def generate_embed(self) -> Embed:
        embed = super().generate_embed()

        counter = LineCounter('py')
        lines_of_py = counter.count_lines_of_code()

        if (
            2 <= lines_of_py % 10 <= 4
            and not (12 <= lines_of_py % 100 <= 14)
        ):
            lines_of_code_text = 'linijki kodu'
        else:
            lines_of_code_text = 'linijek kodu'

        for i, field in enumerate(embed.fields):
            field_value = field.value
            if field_value is None:
                continue

            new_value = field_value.format(
                LINES_OF_PY=f'{lines_of_py} {lines_of_code_text}'
            )

            if field_value != new_value:
                embed.remove_field(i)
                embed.insert_field_at(
                    index=i, name=field.name,
                    value=new_value, inline=field.inline
                )

        return embed

    @property
    def reactions(self) -> list[Emoji | str]:
        return []
