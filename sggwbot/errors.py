# SPDX-License-Identifier: MIT
"""A module containing all custom exceptions."""


class SGGWBotError(Exception):
    """Base exception for all SGGWBot exceptions."""


class UpdateEmbedError(SGGWBotError):
    """Cannot update the embed."""


class ChangeMaxGroupsError(SGGWBotError):
    """Changing max numbers of groups failed."""


class RegistrationError(SGGWBotError):
    """Registration failed."""


class AttachmentError(SGGWBotError):
    """Attachment error."""
