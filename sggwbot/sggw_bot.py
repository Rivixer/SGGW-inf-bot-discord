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

import json
import logging
import os
import sys
import time
from pathlib import Path

import dotenv
import nextcord
from nextcord.ext import commands
from nextcord.flags import Intents
from nextcord.guild import Guild

from sggwbot.console import Console
from sggwbot.utils import ProjectUtils

_logger = logging.getLogger(__name__)


class SGGWBot(commands.Bot):
    """:class:`commands.Bot` but with custom commands added.

    Can be used as an alias in the cog class,
    because Discord API sends the :class:`commands.Bot`
    parameter in :func:`setup` in the cog's file.
    """

    __slots__ = (
        "_prefix",
        "_guild_id",
    )

    _guild_id: int

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

            _logger.critical(
                "The '%s' file did not exist.\n"
                "A prototype has been created.\n"
                "Complete it and start the bot again.",
                path,
            )

        with open(path, "r", encoding="utf-8") as f:
            data: dict = json.load(f)

        guild_id = data.get("GUILD_ID")
        if not isinstance(guild_id, int):
            _logger.critical("GUILD_ID in '%s' must be int", path)
            sys.exit()

        prefix = data.get("PREFIX")
        if not isinstance(prefix, str):
            _logger.critical("PREFIX in '%s' must be str", path)
            sys.exit()

        self._guild_id = guild_id
        self._prefix = prefix

    def get_default_guild(self) -> Guild:
        """Returns the guild where the bot is used."""
        return self.get_guild(self._guild_id)  # type: ignore

    def _load_cogs(self) -> None:
        paths = [
            "sggwbot.assigning_roles.py",
            "sggwbot.information.py",
            "sggwbot.project.py",
            "sggwbot.calendar.py",
            "sggwbot.status.py",
            # "sggwbot.registration.py",
            "sggwbot.messaging.py",
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
