from datetime import datetime
import asyncio
import os

from nextcord.ext import commands
import nextcord

from utils.checks import has_admin_role, is_bot_channel
from utils.console import Console, FontColour


class JsonsCog(commands.Cog):

    __slots__ = '__bot'

    def __init__(self, bot: commands.Bot) -> None:
        self.__bot = bot

    @has_admin_role()
    @is_bot_channel()
    @commands.command(
        name='jsons',
        brief='Send all jsons',
        description='Only on the bot-channel.'
    )
    async def _jsons(self, ctx: commands.Context, *_) -> None:
        files = [
            nextcord.File('files/info.json'),
            nextcord.File('files/info2.json'),
            nextcord.File('files/council.json'),
            nextcord.File('files/links.json'),
            nextcord.File('files/archive_links.json'),
        ]

        await ctx.send(
            f'{ctx.author.mention} '
            'Tu są wszystkie jsony.',
            files=files,
        )

    @staticmethod
    async def __save_file(file: nextcord.Attachment):
        # Move existing file to old_files
        file_extension = file.filename.split('.')[-1]
        file_name = '.'.join(file.filename.split('.')[:-1])

        if not os.path.exists('old_files/preview'):
            os.mkdir('old_files/preview')

        os.replace(
            f'files/preview/{file.filename}',
            f'old_files/preview/{file_name}-{datetime.now().strftime("%d-%m-%y_%H-%M-%S-%f")}.{file_extension}'.replace(' ', '_'),
        )

        # Save new file
        await file.save(f'files/preview/{file.filename}')

    @has_admin_role()
    @is_bot_channel()
    @commands.command(
        name='update_json',
        brief='Update json',
        description='''Only on the bot-channel.
        Attach json file(s) in command message.
        If file(s) with the same name exist(s), move it/them to `old_files/`
        and save new file(s) to location of this/these file(s)
        Otherwise, send a message with json names that do not match.'''
    )
    async def _update_json(self, ctx: commands.Context, *_) -> None:
        if len(ctx.message.attachments) == 0:
            return await ctx.send(
                f'{ctx.author.mention} '
                'Nie załączyłeś żadnego pliku!'
            )

        json_names = list()

        for json_name in os.listdir('files/'):
            json_names.append(json_name.split('.')[:-1])

        attachments = ctx.message.attachments

        to_save: list[nextcord.Attachment] = list()
        wrong_names: list[nextcord.Attachment] = list()
        for attachment in attachments:
            if attachment.filename.split('.')[:-1] in json_names:
                to_save.append(attachment)
            else:
                wrong_names.append(attachment.filename)

        await asyncio.gather(
            *(self.__save_file(i) for i in to_save)
        )

        saved_names = map(lambda i: i.filename, to_save)

        updated_info = f'Zaktualizowano: {", ".join(saved_names)}' if to_save else ''
        wrong_names_info = f'Błędna nazwa: {", ".join(wrong_names)}' if wrong_names else ''

        await ctx.send(
            f'{ctx.author.mention}\n'
            f'{updated_info}\n'
            f'{wrong_names_info}'
        )

        Console.specific(
            f'User {ctx.author.display_name} użył %update_json.\n'
            f'{updated_info}\n'
            f'{wrong_names_info}',
            'UpdateJSON',
            FontColour.PINK
        )


def setup(bot: commands.Bot):
    bot.add_cog(JsonsCog(bot))
