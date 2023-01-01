import os

from nextcord.raw_models import RawReactionActionEvent
from nextcord.application_command import SlashOption
from nextcord.interactions import Interaction
from nextcord.channel import TextChannel
from nextcord.ext import commands
import nextcord

from sggw_bot import SGGWBot

from .assign_role_controller import AssignRoleController


class AssignRoleCog(commands.Cog):

    __slots__ = (
        '__bot',
        '__ctrl'
    )

    __bot: SGGWBot
    __ctrl: AssignRoleController

    def __init__(self, bot: SGGWBot) -> None:
        self.__bot = bot
        self.__ctrl = AssignRoleController(bot)

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent) -> None:
        if payload.member is None or payload.member.bot:
            return

        channel = self.__bot.get_channel(payload.channel_id)

        if not isinstance(channel, TextChannel):
            return

        try:
            message = await channel.fetch_message(payload.message_id)
        except nextcord.NotFound:
            return

        if not message.author.bot or message.id != self.__ctrl.message_id:
            return

        reaction = nextcord.utils.get(
            message.reactions,
            emoji=payload.emoji.name
        )

        if reaction is None or self.__bot.user not in await reaction.users().flatten():
            return await message.remove_reaction(reaction or payload.emoji, payload.member)

        await self.__ctrl.change_group_role(str(payload.emoji), payload.member)

        try:
            await message.remove_reaction(reaction, payload.member)
        except:
            pass

    @nextcord.slash_command(
        name='roles',
        description='Embed with lab groups.',
        dm_permission=False,
        default_member_permissions=1 << 17  # Mention everyone
    )
    async def _roles(self, *_) -> None:
        pass

    @_roles.subcommand(name='send', description='Send new embed')
    async def _send(self, interaction: Interaction) -> None:
        await self.__ctrl.send(interaction)

    @_roles.subcommand(name='update', description='Update embed')
    async def _update(self, interaction: Interaction) -> None:
        await self.__ctrl.update(interaction)

    @_roles.subcommand(
        name='set_max_groups',
        description='Set max number of groups'
    )
    async def _max_groups(
        self,
        interaction: Interaction,
        amount: int = SlashOption(
            description='Max number of groups (1-5).',
            min_value=1,
            max_value=5
        )
    ) -> None:
        await self.__ctrl.update_max_groups(interaction, amount=amount)

    @_roles.subcommand(name='change_thumbnail', description='Change thumbnail')
    async def _change_thumbnail(
        self,
        interaction: Interaction,
        url: str = SlashOption(
            description='Url to emoji (prefered page: \'emoji.gg\'',
            required=True
        )
    ) -> None:
        await self.__ctrl.change_thumbnail(interaction, url)

    @_roles.subcommand(name='get_json', description='Get json with embed fields')
    async def _get_fields(self, interaction: Interaction) -> None:
        try:
            file = self.__ctrl.get_fields_from_json('roles')
        except OSError as e:
            await interaction.response.send_message(
                f'Nie udało się pobrać jsona - {e}', ephemeral=True
            )
        else:
            await interaction.response.send_message(file=file, ephemeral=True)
        finally:
            try:
                os.remove('roles_fields_temp.json')
            except:
                pass

    @_roles.subcommand(name='set_json', description='Set json with embed fields')
    async def _set_fields(
            self,
            interaction: Interaction,
            file: nextcord.Attachment = SlashOption(
                description='JSON file with fields, '
                'downloaded from `/roles get_json` and updated'
            )
    ) -> None:
        await self.__ctrl.set_fields_from_json(interaction, file, 'roles')


def setup(bot: SGGWBot):
    bot.add_cog(AssignRoleCog(bot))
