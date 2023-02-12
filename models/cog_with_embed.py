from typing import Callable, Awaitable
from dataclasses import dataclass
import os

from nextcord.enums import ApplicationCommandOptionType
from nextcord.interactions import Interaction
from nextcord.ext import commands
from nextcord.application_command import (
    SlashApplicationSubcommand,
    SlashApplicationCommand
)

from models.embed_controller import EmbedController
from utils.commands import SlashCommandUtils


@dataclass(slots=True, frozen=True, kw_only=True)
class _Subcommand:
    function: Callable[..., Awaitable[None]]
    name: str
    description: str | None = None


class CogWithEmbed(commands.Cog):

    __slots__ = (
        '__ctrl',
        '__parent',
    )

    __ctrl: EmbedController
    __parent: SlashApplicationCommand

    def __init__(self, ctrl: EmbedController, parent: SlashApplicationCommand) -> None:
        self.__ctrl = ctrl
        self.__parent = parent
        self.__add_commands()

    @property
    def parent_name(self) -> str:
        name = self.__parent.name
        if name is None:
            raise TypeError('Parent name is None')
        return name

    def __add_commands(self) -> None:
        commands = [
            _Subcommand(
                function=self._send,
                name='send',
                description='Send new embed'
            ),
            _Subcommand(
                function=self._update,
                name='update',
                description='Update embed'
            ),
            _Subcommand(
                function=self._get_fields,
                name='get_json',
                description='Get json with embed fields'
            )
        ]

        for command in commands:
            ret = SlashApplicationSubcommand(
                command.name, command.description,
                cmd_type=ApplicationCommandOptionType.sub_command,
                callback=command.function,
                parent_cmd=self.__parent
            )
            self.__parent.children[command.name] = ret

    @SlashCommandUtils.log(show_channel=True)
    async def _send(self, interaction: Interaction) -> None:
        await self.__ctrl.send(interaction)

    @SlashCommandUtils.log()
    async def _update(self, interaction: Interaction) -> None:
        await self.__ctrl.update(interaction)

    @SlashCommandUtils.log()
    async def _get_fields(self, interaction: Interaction) -> None:
        try:
            file = self.__ctrl.get_fields_from_json(self.parent_name)
        except OSError as e:
            await interaction.response.send_message(
                f'Nie udało się pobrać jsona - {e}', ephemeral=True
            )
        else:
            await interaction.response.send_message(file=file, ephemeral=True)
        finally:
            try:
                os.remove(f'{self.parent_name}_fields_temp.json')
            except:
                pass
