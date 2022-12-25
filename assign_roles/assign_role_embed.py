from nextcord.colour import Colour
from nextcord.embeds import Embed
from nextcord.emoji import Emoji

from models.embed_model import EmbedModel

from .assign_role_model import AssignRoleModel


class AssignRoleEmbed(EmbedModel):

    _model: AssignRoleModel

    def generate_embed(self) -> Embed:
        return Embed(
            title='Przydziel się do swojej grupy labolatoryjnej!',
            description='Możesz należeć tylko do 1 grupy.',
            colour=Colour.yellow()
        ).add_field(
            name='Kliknij niżej odpowiednią reakcję:',
            value='\n'.join(f'{r.emoji} - {r.description}'
                            for r in self._model.roles)
        ).set_footer(
            text='Nie spam! Twoja reakcja zniknie po zmianie grupy.'
        )

    @property
    def reactions(self) -> list[Emoji | str]:
        return list(map(lambda i: i.emoji, self._model.roles))
