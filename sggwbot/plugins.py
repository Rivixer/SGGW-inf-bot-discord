# SPDX-License-Identifier: MIT
"""A module to control the plugins.

The plugins are used to extend the functionality of the bot.

The plugins are loaded from the `plugins` directory.

The plugins can be enabled, disabled, and reloaded.

To create a new plugin, copy the plugin structure (`plugins/example` directory).
Rename the directory and the files (the main file must have the same name as the directory).
Rerun the bot to load the new plugin.

The plugin structure:
- `plugins`
    - `example`
        - `example.py`
        - `plugin.json`
    - 'your_plugin'
        - 'your_plugin.py'
        - 'plugin.json'

The `plugin.json` file contains the settings for the plugin.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, auto
import json
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar

import nextcord
from nextcord.ext import commands, tasks
from nextcord.interactions import Interaction

from sggwbot.console import Console, FontColour
from sggwbot.errors import (
    ExceptionData,
    InvalidSettingsFile,
    PluginError,
    PluginNotFoundError,
    PluginOperationError,
)
from sggwbot.utils import InteractionUtils

if TYPE_CHECKING:
    from sggw_bot import SGGWBot


def _console_message(
    message: str,
    /,
    _type: str = "PLUGINS",
    *,
    colour: FontColour = FontColour.GREY,
    bold_text: bool = True,
    bold_type: bool = True,
) -> None:
    Console.specific(
        message,
        _type,
        colour=colour,
        bold_text=bold_text,
        bold_type=bold_type,
    )


class PluginsCog(commands.Cog):
    """A cog to control the plugins."""

    __slots__ = (
        "_bot",
        "_list",
    )

    _bot: SGGWBot
    _list: list[Plugin]

    _DIR: ClassVar[str] = "plugins"

    def __init__(self, bot: SGGWBot) -> None:
        """Initializes the cog."""
        self._bot = bot
        self._list = []
        self._load_plugins()
        self._plugins_info.start()  # pylint: disable=no-member

    @tasks.loop(count=1)
    async def _plugins_info(self):
        await self._bot.wait_until_ready()

        enabled = [plugin.name for plugin in self._list if plugin.is_enabled]
        disabled = [plugin.name for plugin in self._list if plugin.is_disabled]
        invalid = [plugin.name for plugin in self._list if plugin.is_invalid]

        messages = [
            "Enabled plugins: " + (", ".join(enabled) if enabled else "-"),
            "Disabled plugins: " + (", ".join(disabled) if disabled else "-"),
            "Invalid plugins: " + (", ".join(invalid) if invalid else "-"),
        ]

        for message in messages:
            _console_message(message)

    @nextcord.slash_command(
        name="plugins",
        description="The plugins.",
        dm_permission=False,
    )
    async def _plugins(self, *_) -> None:
        """The placeholder for the plugins command."""

    @_plugins.subcommand(
        name="list",
        description="Shows the list of plugins.",
    )
    @InteractionUtils.with_log()
    async def _plugins_list(self, interaction: Interaction) -> None:
        """Shows the list of plugins.

        Parameters
        ----------
        interaction : Interaction
            The interaction.
        """

        embed = nextcord.Embed(
            title="Plugins",
            colour=nextcord.Colour.light_grey(),
        )

        for status in PluginStatus:
            plugins = [plugin.name for plugin in self._list if plugin.status == status]

            embed.add_field(
                name=status.name.title() + ":",
                value="- " + ", ".join(plugins) if plugins else "-",
                inline=False,
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    @_plugins.subcommand(
        name="enable",
        description="Enables a plugin.",
    )
    @InteractionUtils.with_info(
        before="Enabling the '{name}' plugin.",
        after="The '{name}' plugin has been enabled.",
        catch_exceptions=[
            ExceptionData(
                PluginNotFoundError,
                with_traceback_in_response=False,
                with_traceback_in_log=False,
            ),
            ExceptionData(
                ValueError,
                with_traceback_in_response=False,
                with_traceback_in_log=False,
            ),
            PluginOperationError,
        ],
    )
    @InteractionUtils.with_log()
    async def _plugins_enable(self, _: Interaction, name: str) -> None:
        """Enables a plugin.

        Parameters
        ----------
        interaction : Interaction
            The interaction.
        name : str
            The name of the plugin to enable.
        """

        plugin = self._find_plugin(name)

        if plugin.is_enabled:
            raise ValueError(f"Plugin '{name}' is already enabled")

        if not self._bot.load_cog(plugin.extension_name):
            raise PluginOperationError(f"Plugin '{name}' couldn't be enabled")

        plugin.enable()

        _console_message(f"Plugin {plugin.name} has been enabled.")

    @_plugins.subcommand(
        name="disable",
        description="Disables a plugin.",
    )
    @InteractionUtils.with_info(
        before="Disabling the '{name}' plugin.",
        after="The '{name}' plugin has been disabled.",
        catch_exceptions=[
            ExceptionData(
                PluginNotFoundError,
                with_traceback_in_response=False,
                with_traceback_in_log=False,
            ),
            ExceptionData(
                ValueError,
                with_traceback_in_response=False,
                with_traceback_in_log=False,
            ),
            PluginOperationError,
        ],
    )
    @InteractionUtils.with_log()
    async def _plugins_disable(self, _: Interaction, name: str) -> None:
        """Disables a plugin.

        Parameters
        ----------
        interaction : Interaction
            The interaction.
        name : str
            The name of the plugin to disable.
        """

        plugin = self._find_plugin(name)

        if plugin.is_disabled:
            raise ValueError(f"Plugin '{name}' is already disabled")

        if not self._bot.unload_cog(plugin.extension_name):
            raise PluginOperationError(f"Plugin '{name}' couldn't be disabled")

        plugin.disable()
        _console_message(f"Plugin {plugin.name} has been disabled.")

    @_plugins.subcommand(
        name="reload",
        description="Reloads a plugin.",
    )
    @InteractionUtils.with_info(
        before="Reloading the '{name}' plugin.",
        after="The '{name}' plugin has been reloaded.",
        catch_exceptions=[
            ExceptionData(
                PluginNotFoundError,
                with_traceback_in_response=False,
                with_traceback_in_log=False,
            ),
            PluginOperationError,
        ],
    )
    @InteractionUtils.with_log()
    async def _plugins_reload(self, _: Interaction, name: str) -> None:
        """Reloads the plugins.

        Parameters
        ----------
        interaction : Interaction
            The interaction.
        name : str
            The name of the plugin to reload.
        """

        plugin = self._find_plugin(name)

        method = self._bot.reload_cog if plugin.is_enabled else self._bot.load_cog
        if not method(plugin.extension_name):
            raise PluginOperationError(f"Plugin '{name}' couldn't be reloaded")

        _console_message(f"Plugin {plugin.name} has been reloaded.")

    def _load_plugins(self) -> None:
        """Loads the plugins."""
        plugins: list[Plugin] = []

        for plugin_dir in Path(self._DIR).iterdir():
            if plugin_dir.name == "example":
                continue
            if plugin_dir.is_dir() and not plugin_dir.name.startswith("_"):
                plugin = Plugin(plugin_dir.name, plugin_dir)
                plugins.append(plugin)

        for plugin in plugins:
            try:
                plugin.load_settings_or_create_default()
            except InvalidSettingsFile as e:
                Console.error(
                    f"Plugin {plugin.name} has invalid settings file and cannot be loaded.",
                    exception=e,
                )
                plugin.status = PluginStatus.INVALID
                continue

            if plugin.is_enabled:
                if not self._bot.load_cog(plugin.extension_name):
                    Console.error(f"Plugin {plugin.name} couldn't be loaded.")
                    plugin.status = PluginStatus.INVALID

        self._list = plugins

    def _find_plugin(self, name: str) -> Plugin:
        """Finds a plugin by name.

        Parameters
        ----------
        name : str
            The name of the plugin.

        Returns
        -------
        Plugin
            The plugin.
        """
        try:
            return next(plugin for plugin in self._list if plugin.name == name)
        except StopIteration as e:
            raise PluginNotFoundError(name) from e


class PluginStatus(Enum):
    """An enumeration to represent the plugin status."""

    ENABLED = auto()
    DISABLED = auto()
    INVALID = auto()


@dataclass(slots=True)
class Plugin:
    """A class to represent a plugin."""

    name: str
    directory: Path
    status: PluginStatus = field(init=False)

    @property
    def is_enabled(self) -> bool:
        """Whether the plugin is enabled or not."""
        return self.status == PluginStatus.ENABLED

    @property
    def is_disabled(self) -> bool:
        """Whether the plugin is disabled or not."""
        return self.status == PluginStatus.DISABLED

    @property
    def is_invalid(self) -> bool:
        """Whether the plugin is invalid or not."""
        return self.status == PluginStatus.INVALID

    @property
    def extension_name(self) -> str:
        """The name of the extension."""
        return str(self.directory / self.name).replace("\\", ".").replace("/", ".")

    @property
    def _settings_file(self) -> Path:
        """The path to the settings file."""
        return self.directory / "plugin.json"

    def load_settings_or_create_default(self) -> None:
        """Loads the settings or creates the default settings."""
        try:
            if (file := self._settings_file).exists():
                with file.open("r") as file:
                    data: dict[str, Any] = json.load(file)
                    status: bool | None = data.get("enabled")
                    if status is None:
                        self.status = PluginStatus.INVALID
                    elif status:
                        self.status = PluginStatus.ENABLED
                    else:
                        self.status = PluginStatus.DISABLED
            else:
                data = {"enabled": False}
                with file.open("w") as file:
                    json.dump(data, file, indent=4)
                self.status = PluginStatus.DISABLED
        except json.JSONDecodeError as e:
            raise InvalidSettingsFile(file) from e
        except OSError as e:
            raise PluginError(f"Couldn't load the settings file {file}") from e

    def enable(self) -> None:
        """Enables the plugin."""
        settings_file = self._settings_file

        with settings_file.open("r") as file:
            data: dict[str, Any] = json.load(file)
            data["enabled"] = True

        with settings_file.open("w") as file:
            json.dump(data, file, indent=4)

        self.status = PluginStatus.ENABLED

    def disable(self) -> None:
        """Disables the plugin."""
        settings_file = self._settings_file

        with settings_file.open("r") as file:
            data: dict[str, Any] = json.load(file)
            data["enabled"] = False

        with settings_file.open("w") as file:
            json.dump(data, file, indent=4)

        self.status = PluginStatus.DISABLED


def setup(bot: SGGWBot):
    """Loads the PluginsCog."""
    bot.add_cog(PluginsCog(bot))
