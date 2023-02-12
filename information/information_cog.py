from nextcord.application_command import SlashOption
from nextcord.interactions import Interaction
import nextcord

from models.cog_with_embed import CogWithEmbed
from sggw_bot import SGGWBot

from .information_controller import InformationController


class InformationCog(CogWithEmbed):

    __slots__ = (
        '__bot',
        '__ctrl'
    )

    __bot: SGGWBot
    __ctrl: InformationController

    def __init__(self, bot: SGGWBot) -> None:
        self.__bot = bot
        self.__ctrl = InformationController(bot)
        super().__init__(self.__ctrl, self._information)

    @nextcord.slash_command(
        name='information',
        description='Embed with information.',
        dm_permission=False,
        default_member_permissions=1 << 17  # Mention everyone
    )
    async def _information(self, *_) -> None:
        pass

    @_information.subcommand(name='change_thumbnail', description='Change thumbnail')
    async def _change_thumbnail(
        self,
        interaction: Interaction,
        url: str = SlashOption(
            description='Emoji url',
            required=True
        )
    ) -> None:
        await self.__ctrl.change_thumbnail(interaction, url)

    @_information.subcommand(name='set_json', description='Set json with embed fields')
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
    bot.add_cog(InformationCog(bot))
