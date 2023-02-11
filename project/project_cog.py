import os

from nextcord.application_command import SlashOption
from nextcord.interactions import Interaction
from nextcord.ext import commands
import nextcord

from utils.commands import SlashCommandUtils
from sggw_bot import SGGWBot

from .project_controller import ProjectController


class projectCog(commands.Cog):

    __slots__ = (
        '__bot',
        '__ctrl'
    )

    __bot: SGGWBot
    __ctrl: ProjectController

    def __init__(self, bot: SGGWBot) -> None:
        self.__bot = bot
        self.__ctrl = ProjectController(bot)

    @nextcord.slash_command(
        name='project',
        description='Embed with project.',
        dm_permission=False,
        default_member_permissions=1 << 17  # Mention everyone
    )
    async def _project(self, *_) -> None:
        pass

    @_project.subcommand(name='send', description='Send new embed')
    @SlashCommandUtils.log('project send', show_channel=True)
    async def _send(self, interaction: Interaction) -> None:
        await self.__ctrl.send(interaction)

    @_project.subcommand(name='update', description='Update embed')
    @SlashCommandUtils.log('project update')
    async def _update(self, interaction: Interaction) -> None:
        await self.__ctrl.update(interaction)

    @_project.subcommand(name='change_thumbnail', description='Change thumbnail')
    @SlashCommandUtils.log('project change_thumbnail')
    async def _change_thumbnail(
        self,
        interaction: Interaction,
        url: str = SlashOption(
            description='Emoji url (prefered page: \'emoji.gg\')',
            required=True
        )
    ) -> None:
        await self.__ctrl.change_thumbnail(interaction, url)

    @_project.subcommand(name='get_json', description='Get json with embed fields')
    @SlashCommandUtils.log('project get_json')
    async def _get_fields(self, interaction: Interaction) -> None:
        try:
            file = self.__ctrl.get_fields_from_json('project')
        except OSError as e:
            await interaction.response.send_message(
                f'Nie udało się pobrać jsona - {e}', ephemeral=True
            )
        else:
            await interaction.response.send_message(file=file, ephemeral=True)
        finally:
            try:
                os.remove('project_fields_temp.json')
            except:
                pass

    @_project.subcommand(name='set_json', description='Set json with embed fields')
    @SlashCommandUtils.log('project set_json')
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
    bot.add_cog(projectCog(bot))
