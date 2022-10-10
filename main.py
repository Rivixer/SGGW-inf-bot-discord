import os

import dotenv
from nextcord import Intents
from nextcord.ext import commands

BOT_PREFIX = '%%%'


if __name__ == '__main__':
    intents = Intents.all()
    intents.members = True
    intents.presences = True
    intents.message_content = True

    dotenv.load_dotenv()

    bot = commands.Bot(
        command_prefix=BOT_PREFIX,
        intents=intents
    )

    bot.load_extension('cogs.informations_cog')
    bot.load_extension('cogs.archive_info_cog')
    bot.load_extension('cogs.jsons_cog')
    bot.load_extension('cogs.assign_roles_cog')
    bot.load_extension('cogs.test_cog')
    bot.run(os.environ.get('BOT_TOKEN'))
