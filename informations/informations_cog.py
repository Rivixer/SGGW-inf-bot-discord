import os

from nextcord.application_command import SlashOption
from nextcord.interactions import Interaction
from nextcord.ext import commands
import nextcord

from sggw_bot import SGGWBot

from .informations_controller import InformationsController


class InformationsCog(commands.Cog):

    __slots__ = (
        '__bot',
        '__ctrl'
    )

    __bot: SGGWBot
    __ctrl: InformationsController

    def __init__(self, bot: SGGWBot) -> None:
        self.__bot = bot
        self.__ctrl = InformationsController(bot)

    @nextcord.slash_command(
        name='informations',
        description='Embed with informations.',
        dm_permission=False,
        default_member_permissions=131072
    )
    async def _informations(self, *_) -> None:
        pass

    @_informations.subcommand(name='send', description='Send new embed')
    async def _send(self, interaction: Interaction) -> None:
        await self.__ctrl.send(interaction)

    @_informations.subcommand(name='update', description='Update embed')
    async def _update(self, interaction: Interaction) -> None:
        await self.__ctrl.update(interaction)

    @_informations.subcommand(name='change_thumbnail', description='Change thumbnail')
    async def _change_thumbnail(
        self,
        interaction: Interaction,
        url: str = SlashOption(
            description='Emoji url (prefered page: \'emoji.gg\')',
            required=True
        )
    ) -> None:
        await self.__ctrl.change_thumbnail(interaction, url)

    @_informations.subcommand(name='get_json', description='Get json with embed fields')
    async def _get_fields(self, interaction: Interaction) -> None:
        try:
            file = self.__ctrl.get_fields_from_json('informations')
        except OSError as e:
            await interaction.response.send_message(
                f'Nie udało się pobrać jsona - {e}', ephemeral=True
            )
        else:
            await interaction.response.send_message(file=file, ephemeral=True)
        finally:
            try:
                os.remove('informations_fields_temp.json')
            except:
                pass

    @_informations.subcommand(name='set_json', description='Set json with embed fields')
    async def _set_fields(
            self,
            interaction: Interaction,
            file: nextcord.Attachment = SlashOption(
                description='JSON file with fields, '
                'downloaded from `/informations get_json` and updated'
            )
    ) -> None:
        await self.__ctrl.set_fields_from_json(interaction, file, 'informations')


def setup(bot: SGGWBot):
    bot.add_cog(InformationsCog(bot))
