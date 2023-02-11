from nextcord.application_command import SlashOption
from nextcord.interactions import Interaction
from nextcord import Activity, ActivityType
from nextcord.ext import commands
import nextcord

from utils.commands import SlashCommandUtils
from utils.console import Console


class StatusCog(commands.Cog):

    __slots__ = '__bot',

    __bot: commands.Bot

    def __init__(self, bot: commands.Bot) -> None:
        self.__bot = bot

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        activity_type, text = self.__load_status_from_file()
        await self.__set_status(activity_type, text)

    def __load_status_from_file(self) -> tuple[ActivityType, str]:
        """Loads from status.txt where
            the first line is the ActivityType
            and the second line is the status text.

        If file not exists, returns `str` "zarządzanie serwerem".
        """

        try:
            with open('status.txt', 'r', encoding='utf-8') as f:
                lines = list(map(str.strip, f.readlines()))
                return (ActivityType[lines[0]], lines[1].strip())
        except Exception as e:
            Console.warn(
                f'Status cannot be loaded.',
                exception=e
            )
            return (ActivityType.playing, 'zarządzenie serwerem')

    def __save_status_to_file(self, activity_type: str, text: str) -> None:
        """Saves status to file.

        Raises
        ------
        OSError
            Cannot open file.
        """

        with open('status.txt', 'w', encoding='utf-8') as f:
            f.writelines([activity_type, '\n', text])

    async def __set_status(self, activity_type: ActivityType, text: str) -> None:
        await self.__bot.change_presence(
            activity=Activity(
                name=text,
                type=activity_type
            )
        )

    @nextcord.slash_command(
        name='status',
        description='Change bot status',
        dm_permission=False
    )
    @SlashCommandUtils.log('status')
    async def _status(
        self,
        interaction: Interaction,
        text: str,
        activity_type: str = SlashOption(
            choices=[
                ActivityType.playing.name,
                ActivityType.listening.name,
                ActivityType.watching.name,
                ActivityType.streaming.name,
            ]
        )
    ) -> None:
        try:
            await self.__set_status(ActivityType[activity_type], text)
            self.__save_status_to_file(activity_type, text)
        except KeyboardInterrupt:
            pass
        except Exception as e:
            await interaction.response.send_message(
                f'[BŁĄD] {e}', ephemeral=True
            )
        else:
            await interaction.response.send_message(
                'Zmieniono status', ephemeral=True
            )


def setup(bot: commands.Bot):
    bot.add_cog(StatusCog(bot))
