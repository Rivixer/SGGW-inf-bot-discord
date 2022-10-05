from distutils.command.install_egg_info import install_egg_info
import os

import dotenv
from nextcord import Intents
from nextcord.ext import commands

if __name__ == '__main__':
    intents = Intents.all()
    intents.members = True
    intents.presences = True
    intents.message_content = True

    dotenv.load_dotenv()
    
    bot = commands.Bot(
        command_prefix='%',
    )
    bot.run(os.environ.get('BOT_TOKEN'))