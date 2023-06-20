# SPDX-License-Identifier: MIT
"""A module for managing voice channels.

This module provides functionality to manage voice channels on a server.
The server has a category dedicated to voice channels,
where only one channel can be empty at a time.
If a member joins an empty channel, a new channel is created.
If a member leaves a channel and makes it empty,
the channel is automatically deleted.
"""

from __future__ import annotations

import asyncio
import json
import random

import nextcord
from nextcord.application_command import SlashOption
from nextcord.channel import CategoryChannel, VoiceChannel
from nextcord.ext import commands, tasks
from nextcord.interactions import Interaction
from nextcord.member import Member, VoiceState

from sggwbot.console import Console
from sggwbot.models import Controller, Model
from sggwbot.sggw_bot import SGGWBot
from sggwbot.utils import InteractionUtils


class VoiceChananelManagerCog(commands.Cog):
    """A cog to manage voice channels."""

    __slots__ = (
        "_bot",
        "_ctrl",
        "_model",
    )

    _bot: SGGWBot
    _model: VoiceChannelManagerModel

    def __init__(self, bot: SGGWBot) -> None:
        """Initializes the void channel manager cog."""
        self._bot = bot
        self._model = VoiceChannelManagerModel(bot)
        self._ctrl = VoiceChannelManagerController(self._model)
        self._check_voice_channels.start()  # pylint: disable=no-member

    @commands.Cog.listener("on_voice_state_update")
    async def _on_voice_state_update(
        self, member: Member, before: VoiceState, after: VoiceState
    ):
        """Called when a member changes their voice state.

        Parameters
        ----------
        member: :class:`Member`
            The member that changed their voice state.
        before: :class:`VoiceState`
            The voice state before the change.
        after: :class:`VoiceState`
            The voice state after the change.
        """

        if member.bot or before.channel == after.channel:
            return

        if (
            after.channel
            and after.channel.category == self._model.voice_channel_category
            and len(after.channel.members) == 1
        ):
            await self._ctrl.create_new_channel()

        if (
            before.channel
            and before.channel.category == self._model.voice_channel_category
            and len(list(map(lambda i: not i.bot, before.channel.members))) == 0
            and any(filter(lambda i: len(i.members) == 0, before.channel.category.channels))  # type: ignore
        ):
            await self._ctrl.delete_channel(before.channel)  # type: ignore

    @nextcord.slash_command(
        name="limit",
        description="Set the limit of the voice channel you are in.",
    )
    @InteractionUtils.with_info(
        before="Changing the limit to {limit}...",
        after="The limit has been changed.",
        catch_errors=True,
    )
    @InteractionUtils.with_log()
    async def _limit(
        self,
        interaction: Interaction,
        limit: int = SlashOption(
            name="new_voice_channel_user_limit",
            min_value=0,
            max_value=99,
        ),
    ) -> None:
        """Sets the limit of the voice channel the member is in.

        Parameters
        ----------
        interaction: :class:`Interaction`
            The interaction that triggered the command.
        limit: :class:`int`
            The limit to be set.
        """

        user: Member = interaction.user  # type: ignore
        voice = user.voice

        if (
            not interaction.guild
            or not interaction.channel
            or not self._model.user_on_voice(user)
        ):
            return

        await voice.channel.edit(user_limit=limit)  # type: ignore

    @nextcord.slash_command(
        name="name",
        description="Set the name of the voice channel you are in. (max 2 times per 10 minutes)",
    )
    @InteractionUtils.with_info(
        before="Changing the name to {name}...",
        after="The name has been changed.",
        catch_errors=True,
        with_traceback=False,
        additional_errors=[TimeoutError],
    )
    @InteractionUtils.with_log()
    async def _name(
        self,
        interaction: Interaction,
        name: str = SlashOption(
            name="new_voice_channel_name",
            description="The name to be set.",
            required=True,
        ),
    ) -> None:
        """Sets the name of the voice channel the member is in.

        Parameters
        ----------
        interaction: :class:`Interaction`
            The interaction that triggered the command.
        name: :class:`str`
            The name to be set.

        Raises
        ------
        TimeoutError
            If the name of the channel has been changed 2 times per 10 minutes.
        """

        user: Member = interaction.user  # type: ignore
        voice = user.voice

        if (
            not interaction.guild
            or not interaction.channel
            or not self._model.user_on_voice(user)
        ):
            return

        try:
            async with asyncio.timeout(5):
                await self._ctrl.change_channel_name(voice.channel, name)  # type: ignore
        except asyncio.TimeoutError as exc:
            raise TimeoutError(
                "The name of the channel can be changed max 2 times per 10 minutes."
            ) from exc

        await voice.channel.edit(name=name)  # type: ignore

    @tasks.loop(count=1)
    async def _check_voice_channels(self) -> None:
        """Checks the voice channels and deletes the empty ones,
        if there are more than one. If there are no empty channels,
        creates a new one.
        """

        await self._bot.wait_until_ready()
        is_one_empty = False

        for channel in self._model.voice_channel_category.channels:
            if not isinstance(channel, VoiceChannel):
                continue

            if len(channel.members) == 0:
                if is_one_empty:
                    await self._ctrl.delete_channel(channel)
                else:
                    is_one_empty = True

        if not is_one_empty:
            await self._ctrl.create_new_channel()


class VoiceChannelManagerController(Controller):
    """The controller for the voice channel manager cog."""

    __slots__ = ("_model",)

    _model: VoiceChannelManagerModel

    def __init__(self, model: VoiceChannelManagerModel) -> None:
        """Initializes the voice channel manager controller."""
        super().__init__(model)
        self._model = model

    async def create_new_channel(self):
        """Creates a new voice channel."""
        category = self._model.voice_channel_category
        name = self._model.get_next_voice_channel_name()
        await category.create_voice_channel(name=name)

    async def delete_channel(self, channel: VoiceChannel):
        """Deletes a voice channel.

        Parameters
        ----------
        channel: :class:`VoiceChannel`
            The voice channel to be deleted.
        """
        await channel.delete()

    async def change_channel_name(self, channel: VoiceChannel, name: str):
        """Changes the name of a voice channel.

        Parameters
        ----------
        channel: :class:`VoiceChannel`
            The voice channel to be changed.
        name: :class:`str`
            The new name of the voice channel.
        """
        await channel.edit(name=name)


class VoiceChannelManagerModel(Model):
    """The model for the voice channel manager cog."""

    __slots__ = (
        "_voice_channel_category_id",
        "_voice_channel_names",
        "_bot",
    )

    _bot: SGGWBot
    _voice_channel_category_id: int
    _voice_channel_names: list[str]

    def __init__(self, bot: SGGWBot) -> None:
        """Initializes the voice channel manager model."""
        super().__init__()
        self._bot = bot
        self._load_voice_channel_names()
        self._load_voice_channel_category_id()

    def user_on_voice(self, user: Member) -> bool:
        """Returns whether the user is on voice."""
        return (
            user.voice is not None
            and isinstance(user.voice.channel, VoiceChannel)
            and user.voice.channel.category_id == self._voice_channel_category_id
        )

    @property
    def voice_channel_category(self) -> CategoryChannel:
        """The voice channel category."""
        guild = self._bot.get_default_guild()
        return list(
            filter(
                lambda i: i.id == self._voice_channel_category_id,
                guild.categories,
            )
        )[0]

    def _load_voice_channel_category_id(self) -> None:
        with open("data/category_ids.json", "r", encoding="utf-8") as file:
            data = json.load(file)
        self._voice_channel_category_id = data["voice_channels"]

    def get_voice_channels(self) -> list[VoiceChannel]:
        """Returns a list of voice channels in the voice channel category."""
        guild = self._bot.get_default_guild()
        return list(
            filter(
                lambda i: i.category_id == self._voice_channel_category_id,
                guild.voice_channels,
            )
        )

    def _load_voice_channel_names(self) -> None:
        path = "data/voice_channel_names.txt"
        try:
            with open(path, "r", encoding="utf-8") as file:
                channel_names = map(lambda line: line.strip(), file.readlines())
        except OSError:
            Console.warn(f"File '{path}' not found.")
            channel_names = []
        self._voice_channel_names = list(filter(None, channel_names))

    def _voice_channel_name_exists(self, name: str) -> bool:
        voice_channels = self.get_voice_channels()
        for voice_channel in voice_channels:
            if voice_channel.name == name:
                return True
        return False

    def get_next_voice_channel_name(self) -> str:
        """Returns the next voice channel name.
        If all names have been used, returns random room.
        """

        names = self._voice_channel_names
        random.shuffle(names)
        for name in names:
            if not self._voice_channel_name_exists(name):
                return name

        while True:
            room = f"3/{random.randint(1, 99)}"
            if not self._voice_channel_name_exists(room):
                return room


def setup(bot: SGGWBot) -> None:
    """Loads the voice channel manager cog."""
    bot.add_cog(VoiceChananelManagerCog(bot))