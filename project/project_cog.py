from nextcord.application_command import SlashOption
from nextcord.interactions import Interaction
import nextcord

from models.cog_with_embed import CogWithEmbed
from utils.commands import SlashCommandUtils
from sggw_bot import SGGWBot

from .project_controller import ProjectController


class ProjectCog(CogWithEmbed):

    __slots__ = (
        '__bot',
        '__ctrl'
    )

    __bot: SGGWBot
    __ctrl: ProjectController

    def __init__(self, bot: SGGWBot) -> None:
        self.__bot = bot
        self.__ctrl = ProjectController(bot)
        super().__init__(self.__ctrl, self._project)

    @nextcord.slash_command(
        name='project',
        description='Embed with project.',
        dm_permission=False,
        default_member_permissions=1 << 17  # Mention everyone
    )
    async def _project(self, *_) -> None:
        pass

    @_project.subcommand(name='change_thumbnail', description='Change thumbnail')
    @SlashCommandUtils.log()
    async def _change_thumbnail(
        self,
        interaction: Interaction,
        url: str = SlashOption(
            description='Emoji url (prefered page: \'emoji.gg\')',
            required=True
        )
    ) -> None:
        await self.__ctrl.change_thumbnail(interaction, url)

    @_project.subcommand(name='set_json', description='Set json with embed fields')
    @SlashCommandUtils.log()
    async def _set_fields(
        self,
        interaction: Interaction,
        file: nextcord.Attachment = SlashOption(
            description='JSON file with fields, '
            'downloaded from `/project get_json` and updated'
        )
    ) -> None:
        await self.__ctrl.set_fields_from_json(interaction, file, 'project')


def setup(bot: SGGWBot):
    bot.add_cog(ProjectCog(bot))
