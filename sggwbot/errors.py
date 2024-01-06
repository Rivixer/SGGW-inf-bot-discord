# SPDX-License-Identifier: MIT
"""A module containing all custom exceptions."""


from dataclasses import dataclass, field
from typing import Type


class SGGWBotError(Exception):
    """Base exception for all SGGWBot exceptions."""


class UpdateEmbedError(SGGWBotError):
    """Cannot update the embed."""


class RegistrationError(SGGWBotError):
    """Registration failed."""


class AttachmentError(SGGWBotError):
    """Attachment error."""


class NoVoiceConnection(SGGWBotError):
    """No voice connection."""


@dataclass
class ExceptionData:
    """Exception data with attributes to be passed to the error handler.

    Attributes
    ----------
    type: Type[Exception]
        Exception type.
    with_traceback_in_reply: bool = False
        Whether to include traceback in command response.
        Defaults to ``True``.
    with_traceback_in_log: bool = True
        Whether to include traceback in log.
        Defaults to ``True``.

    Examples
    -------- ::

        @nextcord.slash_command(name="divide", description="Divide two numbers.")
        @InteractionUtils.with_info(catch_errors=[
            ExceptionData(ZeroDivisionError, with_traceback_in_reply=False)
        ])
        async def _divide(self, interaction, a, b) -> None:
            await interaction.response.send_message(f"{a} / {b} = {a / b}")

    Notes
    -----
    This class is used to send exception data to the error handler.
    """

    type: Type[Exception]
    with_traceback_in_response: bool = field(default=True, kw_only=True)
    with_traceback_in_log: bool = field(default=True, kw_only=True)
