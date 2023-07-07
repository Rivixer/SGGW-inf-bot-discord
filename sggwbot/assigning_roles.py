# SPDX-License-Identifier: MIT
"""A module to control the assigning_roles embed.

The assigning_roles embed is used to assign roles to users based on their lab group.

The user's roles are updated when a user reacts to the embed
with an emoji corresponding to a lab group.

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

from sggwbot.errors import ChangeMaxGroupsError, UpdateEmbedError
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

    @_assigning_roles.subcommand(
        name="change_max_groups",
        description="Set the max number of lab groups and update the embed.",
    )
    @InteractionUtils.with_info(
        before="Setting the max number of lab groups to {amount}...",
        after="Max number of lab groups has been set to {amount}.",
        catch_exceptions=[UpdateEmbedError, ChangeMaxGroupsError],
    )
    @InteractionUtils.with_log()
    async def _change_max_groups(
        self,
        interaction: Interaction,  # pylint: disable=unused-argument
        amount: int = SlashOption(
            description="Max number of groups (1-8).",
            min_value=1,
            max_value=8,
        ),
    ) -> None:
        """Sets the max number of lab groups and updates the assigning_roles embed.

        Parameters
        ----------
        interaction: :class:`Interaction`
            The interaction that triggered the command.
        amount: :class:`int`
            The max number of lab groups.

        Raises
        ------
        ChangeMaxGroupsError
            The max number of lab groups is not between 1 and 8.
        UpdateEmbedError
            The embed could not be updated.
        """
        # pylint: disable=assigning-non-slot,no-member
        old_amount = self._ctrl.model.max_groups
        try:
            self._ctrl.model.max_groups = amount
            await self._ctrl.update_embed()
        except (KeyError, ValueError) as e:
            self._ctrl.model.max_groups = old_amount
            raise ChangeMaxGroupsError(*e.args) from e

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

            await self._ctrl.change_group_role(emoji, member)
            await message.remove_reaction(reaction, member)
        except nextcord.DiscordException:
            return


# pylint: disable=no-member


@dataclass(slots=True, frozen=True)
class Group:
    """Represents a lab group on the server.

    Attributes
    ----------
    role_id: :class:`int`
        The ID of the role that is assigned to the user.
    descrption: :class:`str`
        The descrption of the group.
        Used to inform the user in embed what this group is for.
    emoji: :class:`str`
        The emoji that represents the group.
    """

    role_id: int
    description: str
    emoji: str

    @property
    def info(self) -> str:
        """Group's emoji with its description."""
        return f"{self.emoji} - {self.description}"


class AssigningRolesModel(Model):
    """Represents the assigning_roles model.

    Attributes
    ----------
    max_groups: :class:`int`
        The max number of lab groups.
    group_roles: list[:class:`Group`]
        The list of lab groups.
    other_roles: list[:class:`Group`]
        The list of other roles.

    Notes
    -----
    The assigning_roles model is a singleton.
    """

    __slots__ = (
        "_group_roles",
        "_other_roles",
        "_max_groups",
    )

    _group_roles: list[Group]
    _other_roles: list[Group]
    _max_groups: int

    def __init__(self) -> None:
        """Initialize the assigning_roles model."""
        super().__init__()
        self._load_groups()

    @property
    def _groups_data(self) -> dict[str, Any]:
        """The groups data from the settings.json file."""
        groups_data = self.data.get("groups")
        if not isinstance(groups_data, dict):
            raise TypeError("groups in settings.json must be dict")
        return groups_data

    def _load_groups(self) -> None:
        """Loads the groups data from the settings.json file."""
        groups_data = self._groups_data

        self.max_groups = groups_data.get("max_groups")
        group_roles, other_roles = [], []

        for i in range(self.max_groups):
            group = self._load_group(f"group_{i}")
            group_roles.append(group)

        for i in range(self.max_groups, 8):
            try:
                group = self._load_group(f"group_{i}")
            except KeyError:
                break
            group_roles.append(group)

        guest_role = self._load_group("guest")
        other_roles.append(guest_role)

        self._group_roles = group_roles
        self._other_roles = other_roles

    def _load_group(self, key: str) -> Group:
        group_data = self._groups_data.get(key)
        if group_data is None:
            raise KeyError(f"Key '{key}' not exists in {self._settings_path}")
        return Group(**group_data)

    def reload_settings(self) -> None:
        """Reloads the settings.json file and reloads groups."""
        super().reload_settings()
        self._load_groups()

    @staticmethod
    def _validate_max_groups(amount: Any) -> None:
        """Validates the max number of lab groups."""
        if not isinstance(amount, int):
            raise TypeError("max_groups must be int")
        if not 1 <= amount <= 8:
            raise ValueError("max_groups must be between 1 and 8")

    @property
    def max_groups(self) -> int:
        """Maximum number of laboratory groups."""
        return self._max_groups

    @max_groups.setter
    def max_groups(self, obj: Any) -> None:
        self._validate_max_groups(obj)
        self._max_groups = obj
        data = self._groups_data
        data["max_groups"] = obj
        self.update_settings("groups", data)

    @property
    def groups(self) -> list[Group]:
        """Group list. Laboratory groups are limited by :attr:`max_groups`."""
        roles = self._group_roles[: self.max_groups]
        roles.extend(self._other_roles)
        return roles


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
        groups_info = "\\n".join(map(lambda i: i.info, self.model.groups))
        return super().generate_embed(GROUP_DESCRIPTION=groups_info)

    @property
    def reactions(self) -> list[Emoji | str]:
        return list(map(lambda i: i.emoji, self.model.groups))


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
    change_group_role(emoji: :class:`nextcord.PartialEmoji`, member: :class:`nextcord.Member`)

    Notes
    -----
    The assigning_roles controller is a singleton.
    """

    embed_model: AssigningRolesEmbedModel
    model: AssigningRolesModel

    async def change_group_role(self, emoji: PartialEmoji, member: Member) -> None:
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

        for group in self.model.groups:
            role = member.guild.get_role(group.role_id)
            if role is None:
                continue  # pragma: no cover

            if reaction == group.emoji:
                role_to_add = role
            elif role in member.roles:
                roles_to_remove.append(role)

        if role_to_add is None:
            raise AttributeError(f"Role with '{emoji}' not exists")

        await asyncio.gather(
            member.remove_roles(*roles_to_remove), member.add_roles(role_to_add)
        )


def setup(bot: SGGWBot):
    """Loads the AssigningRolesCog cog."""
    bot.add_cog(AssigningRolesCog(bot))
