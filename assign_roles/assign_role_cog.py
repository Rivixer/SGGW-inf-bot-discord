from nextcord.raw_models import RawReactionActionEvent
from nextcord.application_command import SlashOption
from nextcord.interactions import Interaction
from nextcord.channel import TextChannel
from nextcord.ext import commands
import nextcord

from .assign_role_controller import AssignRoleController


class AssignRoleCog(commands.Cog):

    __slots__ = (
        '__bot',
        '__ctrl'
    )

    __bot: commands.Bot
    __ctrl: AssignRoleController

    def __init__(self, bot: commands.Bot) -> None:
        self.__bot = bot
        self.__ctrl = AssignRoleController()

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
        default_member_permissions=131072
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


def setup(bot: commands.Bot):
    bot.add_cog(AssignRoleCog(bot))
