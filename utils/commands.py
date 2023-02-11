from typing import Callable, Awaitable
from abc import ABC
import functools

from nextcord.application_command import (
    SlashApplicationSubcommand,
    SlashApplicationCommand
)
from nextcord.interactions import Interaction
from nextcord.channel import TextChannel
from nextcord.member import Member

from utils.console import Console, FontColour


_FUNC = Callable[..., Awaitable[None]]


class SlashCommandUtils(ABC):

    @staticmethod
    def log(
        colour: FontColour = FontColour.PINK,
        show_channel: bool = False
    ) -> Callable[..., _FUNC]:
        """Prints to the console information about
            the user who ran a decorated command.

        This decorator should be placed after
            decorators that set a function as a command.

        If the command is a subcommand, its name
            will be preceded by its parent name.

        Prameters
        ---------
        colour: `FontColour`
            Console message colour.
        show_channel: `bool`
            If True, the channel ID will be printed in the console.
        """

        def decorator(func: _FUNC) -> _FUNC:
            @functools.wraps(func)
            async def wrapper(self, interaction: Interaction, *args, **kwargs) -> None:
                command = interaction.application_command
                if isinstance(command, SlashApplicationSubcommand):
                    parent: SlashApplicationCommand
                    parent = command.parent_cmd  # type: ignore
                    command_name = f'{parent.name} {command.name}'
                elif isinstance(command, SlashApplicationCommand):
                    command_name = command.name
                else:
                    raise TypeError(
                        'Decorated function must be '
                        'SlashApplicationSubcommand or SlashApplicationCommand'
                    )

                type_info = 'SLASH_COMMAND'
                user: Member = interaction.user  # type: ignore
                user_info = f'{user.display_name} ({user.name}#{user.discriminator})'
                kwargs_info = ' '.join(
                    f'{k}:{v}' for k, v in kwargs.items()
                    if v is not None
                )

                if show_channel:
                    channel = interaction.channel
                    if isinstance(channel, TextChannel):
                        type_info += f'/{channel.name}'

                Console.specific(
                    f'{user_info} used /{command_name} {kwargs_info}',
                    type_info, colour
                )

                return await func(self, interaction, *args, **kwargs)
            return wrapper
        return decorator
