from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from nextcord.activity import Activity
from nextcord.application_command import SlashOption
from nextcord.enums import ActivityType
from nextcord.ext import commands
from nextcord.interactions import Interaction
import nextcord

from sggwbot.console import Console
from sggwbot.utils import InteractionUtils

if TYPE_CHECKING:
    from sggwbot.sggw_bot import SGGWBot


class StatusCog(commands.Cog):

    __slots__ = (
        '_bot',
    )

    _STATUS_PATH = Path('data/status.txt')
    _bot: SGGWBot

    def __init__(self, bot: SGGWBot) -> None:
        self._bot = bot

    @commands.Cog.listener(name='on_ready')
    async def _on_ready(self) -> None:
        activity_type, text = self._get_data_from_file()
        await self._set_status(activity_type, text)

    @nextcord.slash_command(
        name='status',
        description='Change bot status',
        dm_permission=False
    )
    @InteractionUtils.with_info(
        before='Changing status...',
        after='Status has been changed to: **{activity_type} *{text}***',
        catch_errors=True,
    )
    @InteractionUtils.with_log()
    async def _status(
        self,
        _: Interaction,
        text: str,
        activity_type: str = SlashOption(
            choices=[
                ActivityType.playing.name,
                ActivityType.listening.name,
                ActivityType.watching.name,
                ActivityType.streaming.name,
            ],
        ),
    ) -> None:
        await self._set_status(ActivityType[activity_type], text)

    def _get_data_from_file(self) -> tuple[ActivityType, str]:
        try:
            with open(self._STATUS_PATH, 'r', encoding='utf-8') as f:
                lines = list(map(str.strip, f.readlines()))
            return (ActivityType[lines[0]], lines[1].strip())
        except (OSError, nextcord.DiscordException, KeyError) as e:
            Console.warn(
                'Status could not be loaded. The default status has been set.',
                exception=e
            )
            return (ActivityType.playing, 'zarządzenie serwerem')

    def _save_data_to_file(self, activity_type: ActivityType, text: str) -> None:
        try:
            with open(self._STATUS_PATH, 'w', encoding='utf-8') as f:
                f.write(f'{activity_type.name}\n{text}')
        except OSError as e:
            Console.error('Error while saving the status.', exception=e)

    async def _set_status(self, activity_type: ActivityType, text: str) -> None:
        activity = Activity(name=text, type=activity_type)
        await self._bot.change_presence(activity=activity)
        self._save_data_to_file(activity_type, text)


def setup(bot: SGGWBot):
    """Adds StatusCog to the bot."""
    bot.add_cog(StatusCog(bot))
