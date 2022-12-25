from pathlib import Path
import json
import time
import sys
import os

from nextcord.ext import commands
from nextcord.guild import Guild
from nextcord import Intents
import dotenv

from utils.console import Console


class SGGWBot(commands.Bot):

    __slots__ = (
        '__prefix',
        '__guild_id',
        '__bot'
    )

    __guild_id: int
    __prefix: str
    __bot: commands.Bot

    def __init__(self) -> None:
        intents = Intents.all()
        intents.members = True
        intents.presences = True
        intents.message_content = True

        dotenv.load_dotenv()
        self.__load_settings()

        self.__bot = commands.Bot(
            command_prefix=self.__prefix,
            intents=intents,
            case_insensitive=True
        )

        setattr(self.__bot, 'get_default_guild',
                self.get_default_guild)

    def __load_settings(self) -> None:

        MODEL = """{
            "GUILD_ID": int,
            "PREFIX": str
        }"""

        path = Path('settings.json')
        if not path.exists():
            with open(path, 'w') as f:
                f.write(MODEL)

            Console.critical_error(
                'Error while starting bot.',
                FileNotFoundError(
                    """The 'settings.json' file did not exist.
                    A prototype has been created.
                    Complete it and start the bot again.
                    """
                )
            )

        with open('settings.json', 'r') as f:
            data: dict = json.load(f)

        guild_id = data.get('GUILD_ID')  # type: ignore
        if not isinstance(guild_id, int):
            Console.critical_error(
                'Error while starting bot.',
                ValueError("guild_id in 'settings.json' must be int")
            )

        prefix = data.get('PREFIX')
        if not isinstance(prefix, str):
            Console.critical_error(
                'Error while starting bot.',
                ValueError("prefix in 'settings.json' must be str")
            )

        self.__guild_id = guild_id
        self.__prefix = prefix

    def get_default_guild(self) -> Guild:
        return self.__bot.get_guild(self.__guild_id)  # type: ignore

    def load_cogs(self) -> None:
        for path in Path('.').rglob('*_cog.py'):
            if str(path).startswith('.venv'):
                continue

            cog_name = str(path)[:-7]
            start_time = time.time()

            try:
                self.__bot.load_extension(
                    str(path)[:-3].replace(
                        '\\' if sys.platform != 'linux' else '/', '.'
                    )
                )
                Console.cogs(
                    f'Cog \'{cog_name}\' został załadowany! '
                    f'({(time.time()-start_time)*1000:.2f}ms)'
                )
            except commands.ExtensionError as e:
                Console.error(
                    f'ERROR! Cog \'{cog_name}\' nie został załadowany!',
                    exception=e
                )

    def start(self) -> None:
        self.__bot.run(os.environ.get('BOT_TOKEN'))


if __name__ == '__main__':
    sggw_bot = SGGWBot()
    sggw_bot.load_cogs()
    sggw_bot.start()
