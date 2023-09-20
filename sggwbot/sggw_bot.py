# SPDX-License-Identifier: MIT
"""A module containing the main class of the bot.

The :class:`SGGWBot` class is used to initialize the bot.

Examples
-------- ::

    from sggwbot.sggw_bot import SGGWBot

    class Cog(commands.Cog):
        def __init__(self, bot: SGGWBot) -> None:
            self.bot = bot

    def setup(bot: SGGWBot) -> None:
        bot.add_cog(Cog(bot))
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import dotenv
import nextcord
from nextcord.channel import TextChannel
from nextcord.ext import commands
from nextcord.flags import Intents
from nextcord.guild import Guild

from sggwbot.console import Console
from sggwbot.utils import ProjectUtils


class SGGWBot(commands.Bot):
    """:class:`commands.Bot` but with custom commands added.

    Can be used as an alias in the cog class,
    because Discord API sends the :class:`commands.Bot`
    parameter in :func:`setup` in the cog's file.
    """

    __slots__ = (
        "_prefix",
        "_guild_id",
        "_bot_channel_id",
    )

    _guild_id: int
    _prefix: str
    _bot_channel_id: int

    def __init__(self) -> None:
        intents = Intents.all()
        intents.members = True
        intents.presences = True
        intents.message_content = True
        self._load_settings()

        super().__init__(
            command_prefix=self._prefix,
            intents=intents,
            case_insensitive=True,
        )

        dotenv.load_dotenv()
        self._load_cogs()

        lines_of_code = ProjectUtils.lines_of_code()
        Console.info(f"Linijek kodu: {lines_of_code}")

        setattr(self, "get_default_guild", self.get_default_guild)

    def _load_settings(self) -> None:
        model = {
            "GUILD_ID": "int",
            "PREFIX": "str",
            "ADMIN_ROLE_ID": "int",
            "BOT_CHANNEL_ID": "int",
        }

        path = Path("settings.json")
        if not path.exists():
            with open(path, "w", encoding="utf-8") as f:
                json.dump(model, f, indent=4)

            Console.critical_error(
                f"The '{path}' file did not exist.\n"
                "A prototype has been created.\n"
                "Complete it and start the bot again.",
            )

        with open(path, "r", encoding="utf-8") as f:
            data: dict = json.load(f)

        guild_id = data.get("GUILD_ID")
        if not isinstance(guild_id, int):
            Console.critical_error(f"GUILD_ID in '{path}' must be int")

        prefix = data.get("PREFIX")
        if not isinstance(prefix, str):
            Console.critical_error(f"PREFIX in {path} must be str")

        bot_channel_id = data.get("BOT_CHANNEL_ID")
        if not isinstance(bot_channel_id, int):
            Console.critical_error(f"BOT_CHANNEL_ID in {path} must be int")

        self._guild_id = guild_id
        self._prefix = prefix
        self._bot_channel_id = bot_channel_id

    def get_default_guild(self) -> Guild:
        """Returns the guild where the bot is used."""
        return self.get_guild(self._guild_id)  # type: ignore

    def get_bot_channel(self) -> TextChannel:
        """Returns the bot channel."""
        guild = self.get_default_guild()
        channel = guild.get_channel(self._bot_channel_id)
        assert isinstance(channel, TextChannel)
        return channel

    def _load_cogs(self) -> None:
        paths = [
            "sggwbot.role_assignment.py",
            "sggwbot.information.py",
            "sggwbot.project.py",
            "sggwbot.calendar.py",
            "sggwbot.status.py",
            "sggwbot.registration.py",
            "sggwbot.messaging.py",
            "sggwbot.voice_channel_manager.py",
        ]

        for path in paths:
            cog_name = str(path)[:-3]
            start_time = time.time()

            try:
                cog_path = str(path)[:-3].replace(
                    "\\" if sys.platform != "linux" else "/", "."
                )
                self.load_extension(cog_path)
                load_time = (time.time() - start_time) * 1000
                Console.info(f"Cog '{cog_name}' has been loaded! ({load_time:.2f}ms)")
            except (
                commands.ExtensionError,
                ModuleNotFoundError,
                nextcord.errors.HTTPException,
            ) as e:
                Console.important_error(
                    f"Cog '{cog_name}' couldn't be loaded!", exception=e
                )

    def main(self) -> None:
        """Runs the bot using `BOT_TOKEN` received from `.env` file."""
        self.run(os.environ.get("BOT_TOKEN"))
