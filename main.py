from pathlib import Path
import sys
import os

from nextcord.ext import commands
from nextcord import Intents
import dotenv

from utils.console import Console

BOT_PREFIX = '%'


if __name__ == '__main__':
    intents = Intents.all()
    intents.members = True
    intents.presences = True
    intents.message_content = True

    dotenv.load_dotenv()

    bot = commands.Bot(
        command_prefix=BOT_PREFIX,
        intents=intents,
        case_insensitive=True
    )

    for path in Path('.').rglob('*_cog.py'):
        if str(path).startswith('.venv'):
            continue

        cog_name = str(path)[:-7]

        try:
            bot.load_extension(
                str(path)[:-3].replace(
                    '\\' if sys.platform != 'linux' else '/', '.'
                )
            )
            Console.cogs(f'Cog \'{cog_name}\' został załadowany!')
        except commands.ExtensionError as e:
            Console.error(
                f'ERROR! Cog \'{cog_name}\' nie został załadowany!',
                exception=e
            )

    bot.run(os.environ.get('BOT_TOKEN'))
