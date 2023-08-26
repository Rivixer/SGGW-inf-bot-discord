# SPDX-License-Identifier: MIT
"""A module to control the assigning_roles embed.

The assigning_roles embed is used to assign roles to users based on their group.
(e.g. laboratory group, faculty group, etc.)

The user's roles are updated when a user reacts to the embed
with an emoji corresponding to a group.

The assigning_roles embed is sent to the channel
where the command '/assigning_roles send' was used.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import nextcord
from nextcord.application_command import SlashOption
from nextcord.channel import TextChannel
from nextcord.embeds import Embed
from nextcord.emoji import Emoji
from nextcord.errors import DiscordException
from nextcord.ext import commands
from nextcord.interactions import Interaction
from nextcord.message import Attachment

from sggwbot.errors import UpdateEmbedError
from sggwbot.models import ControllerWithEmbed, EmbedModel, Model
from sggwbot.utils import InteractionUtils

if TYPE_CHECKING:
    from nextcord.member import Member
    from nextcord.partial_emoji import PartialEmoji
    from nextcord.raw_models import RawReactionActionEvent
    from nextcord.role import Role

    from sggwbot import SGGWBot


class AssigningRolesCog(commands.Cog):
    """A cog to control the assigning_roles embed."""

    __slots__ = (
        "_bot",
        "_ctrl",
    )

    _bot: SGGWBot
    _ctrl: AssigningRolesController

    def __init__(self, bot: SGGWBot) -> None:
        """Initialize the cog."""

        self._bot = bot
        model = AssigningRolesModel()
        embed_model = AssigningRolesEmbedModel(model, bot)
        self._ctrl = AssigningRolesController(model, embed_model)

    @nextcord.slash_command(
        name="assigning_roles",
        description="The assigning_roles embed.",
        dm_permission=False,
    )
    async def _assigning_roles(self, *_) -> None:
        """The assigning_roles embed.

        This command is a placeholder for the subcommands.
        """

    @_assigning_roles.subcommand(
        name="send",
        description="Send a new assigning_roles embed.",
    )
    @InteractionUtils.with_info(
        before="Sending assigning_roles embed...",
        after="The assigning_roles embed has been sent.",
        catch_exceptions=[DiscordException],
    )
    @InteractionUtils.with_log(show_channel=True)
    async def _send(self, interaction: Interaction) -> None:
        """Sends a new assigning_roles embed.

        The assigning_roles embed is sent to the channel where the command was used.

        Parameters
        ----------
        interaction: :class:`Interaction`
            The interaction that triggered the command.
        """

        channel = interaction.channel
        if isinstance(channel, TextChannel):
            await self._ctrl.send_embed(channel)

    @_assigning_roles.subcommand(
        name="update",
        description="Update the assigning_roles embed.",
    )
    @InteractionUtils.with_info(
        before="Updating assigning_roles embed...",
        after="The assigning_roles embed has been updated.",
        catch_exceptions=[UpdateEmbedError],
    )
    @InteractionUtils.with_log()
    async def _update(
        self, interaction: Interaction  # pylint: disable=unused-argument
    ) -> None:
        """Updates the assigning_roles embed.

        Parameters
        ----------
        interaction: :class:`Interaction`
            The interaction that triggered the command.

        Raises
        ------
        UpdateEmbedError
            The embed could not be updated.
        """
        await self._ctrl.update_embed()

    @_assigning_roles.subcommand(
        name="get_json",
        description="Get the assigning_roles embed json.",
    )
    @InteractionUtils.with_info(
        before="Getting assigning_roles embed json...",
        catch_exceptions=[DiscordException],
    )
    @InteractionUtils.with_log()
    async def _get_json(self, interaction: Interaction) -> None:
        """Gets the json file representing the assigning_roles embed.

        Parameters
        ----------
        interaction: :class:`Interaction`
            The interaction that triggered the command.
        """
        msg = await interaction.original_message()
        await msg.edit(content=None, file=self._ctrl.embed_json)

    @_assigning_roles.subcommand(
        name="set_json",
        description="Set the assigning_roles embed json and update the embed.",
    )
    @InteractionUtils.with_info(
        before="Setting assigning_roles embed json and updating the embed...",
        after="The assigning_roles embed and json file have been updated.",
        catch_exceptions=[TypeError, DiscordException, UpdateEmbedError],
    )
    @InteractionUtils.with_log()
    async def _set_json(
        self,
        interaction: Interaction,  # pylint: disable=unused-argument
        file: Attachment = SlashOption(
            description="JSON file "
            "downloaded from `/assigning_roles get_json` and updated"
        ),
    ) -> None:
        """Sets the json file representing the assigning_roles embed and updates this embed.

        Parameters
        ----------
        interaction: :class:`Interaction`
            The interaction that triggered the command.
        file: :class:`Attachment`
            The json file downloaded from `/assigning_roles get_json` and updated.

        Raises
        ------
        UpdateEmbedError
            The embed could not be updated.
        """
        await self._ctrl.set_embed_json(file)
        await self._ctrl.update_embed()

    @commands.Cog.listener(name="on_raw_reaction_add")
    async def _on_raw_reaction_add(self, payload: RawReactionActionEvent) -> None:
        """Handles the reaction add event.

        Parameters
        ----------
        payload: :class:`RawReactionActionEvent`
            The payload of the reaction add event.
        """

        emoji = payload.emoji
        member = payload.member
        if member is None or member.bot:
            return

        channel = self._bot.get_channel(payload.channel_id)
        if not isinstance(channel, TextChannel):
            return

        if payload.message_id != self._ctrl.message_id:
            return

        try:
            message = await channel.fetch_message(payload.message_id)
            reaction = nextcord.utils.get(message.reactions, emoji=emoji.name)

            if (
                reaction is None
                or self._bot.user not in await reaction.users().flatten()
            ):
                return await message.remove_reaction(emoji, member)

            await self._ctrl.change_role(emoji, member)
            await message.remove_reaction(reaction, member)
        except nextcord.DiscordException:
            return


# pylint: disable=no-member


@dataclass(slots=True, frozen=True)
class ServerRole:
    """Represents a role on the server.

    Attributes
    ----------
    role_id: :class:`int`
        The ID of the role.
    descrption: :class:`str`
        The descrption of the role.
        Used to inform the user in embed what this role is for.
    emoji: :class:`str`
        The emoji that represents the role.
    """

    role_id: int
    description: str
    emoji: str

    @property
    def info(self) -> str:
        """Role's emoji with its description."""
        return f"{self.emoji} - {self.description}"


class AssigningRolesModel(Model):
    """Represents the assigning_roles model.

    Attributes
    ----------
    roles: list[:class:`Group`]
        The list of roles.

    Notes
    -----
    The assigning_roles model is a singleton.
    """

    __slots__ = ("_roles",)

    _roles: list[ServerRole]

    def __init__(self) -> None:
        """Initialize the assigning_roles model."""
        super().__init__()
        self._load_roles()

    @property
    def _roles_data(self) -> dict[str, Any]:
        """The roles data from the settings.json file."""
        roles_data = self.data.get("roles")
        if not isinstance(roles_data, dict):
            raise TypeError("roles in settings.json must be dict")
        return roles_data

    def _load_roles(self) -> None:
        """Loads the roles data from the settings.json file."""
        roles_data = self._roles_data
        self._roles = []

        for role_name in roles_data.keys():
            role = self._load_role(role_name)
            self.roles.append(role)

    def _load_role(self, key: str) -> ServerRole:
        role_data = self._roles_data.get(key)
        if role_data is None:
            raise KeyError(f"Key '{key}' not exists in {self._settings_path}")
        return ServerRole(**role_data)

    def reload_settings(self) -> None:
        """Reloads the settings.json file and reloads roles."""
        super().reload_settings()
        self._load_roles()

    @property
    def roles(self) -> list[ServerRole]:
        """Role list."""
        return self._roles


class AssigningRolesEmbedModel(EmbedModel):
    """Represents the assigning_roles embed model.

    Attributes
    ----------
    model: :class:`AssigningRolesModel`
        The assigning_roles model.

    Notes
    -----
    The assigning_roles embed model is a singleton.
    """

    model: AssigningRolesModel

    def generate_embed(self, **_) -> Embed:
        roles_info = "\\n".join(map(lambda i: i.info, self.model.roles))
        return super().generate_embed(GROUP_DESCRIPTION=roles_info)

    @property
    def reactions(self) -> list[Emoji | str]:
        return list(map(lambda i: i.emoji, self.model.roles))


class AssigningRolesController(ControllerWithEmbed):
    """Represents the assigning_roles controller.

    Attributes
    ----------
    model: :class:`AssigningRolesModel`
        The assigning_roles model.
    embed_model: :class:`AssigningRolesEmbedModel`
        The assigning_roles embed model.

    Methods
    -------
    change_role(emoji: :class:`nextcord.PartialEmoji`, member: :class:`nextcord.Member`)

    Notes
    -----
    The assigning_roles controller is a singleton.
    """

    embed_model: AssigningRolesEmbedModel
    model: AssigningRolesModel

    async def change_role(self, emoji: PartialEmoji, member: Member) -> None:
        """|coro|

        Assigns the member the role corresponding to the emoji and removes other roles.

        Parameters
        ----------
        emoji: :class:`nextcord.PartialEmoji`
            The emoji that the user reacted to.
        member: :class:`nextcord.Member`
            The member who reacted to the embed message.

        Raises
        ------
        AttributeError
            The role corresponding to the emoji does not exist.
        """

        role_to_add: Role | None = None
        roles_to_remove: list[Role] = []
        reaction = str(emoji)

        for server_role in self.model.roles:
            role = member.guild.get_role(server_role.role_id)
            if role is None:
                continue  # pragma: no cover

            if reaction == server_role.emoji:
                role_to_add = role
            elif role in member.roles:
                roles_to_remove.append(role)

        if role_to_add is None:
            raise AttributeError(f"Role with '{emoji}' not exists")

        await asyncio.gather(
            member.remove_roles(*roles_to_remove),
            member.add_roles(role_to_add),
        )


def setup(bot: SGGWBot):
    """Loads the AssigningRolesCog cog."""
    bot.add_cog(AssigningRolesCog(bot))
