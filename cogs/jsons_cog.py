from datetime import datetime
import asyncio
import os

from nextcord.ext import commands
import nextcord

from utils.checks import has_admin_role, is_bot_channel


class JsonsCog(commands.Cog):

    __slots__ = '__bot'

    def __init__(self, bot: commands.Bot) -> None:
        self.__bot = bot

    @has_admin_role()
    @is_bot_channel()
    @commands.command(name='jsons')
    async def _jsons(self, ctx: commands.Context, *_) -> None:
        await ctx.message.delete()

        files = [
            nextcord.File('files/info.json'),
            nextcord.File('files/council.json'),
            nextcord.File('files/links.json'),
            nextcord.File('files/archive_links.json'),
        ]

        await ctx.send(
            f'{ctx.author.mention} '
            'Tu są wszystkie jsony. '
            'Ta wiadomość zniknie za 60 sek.',
            files=files,
            delete_after=60
        )

    @staticmethod
    async def __save_file(file: nextcord.Attachment):
        # Move existing file to old_files
        file_extension = file.filename.split('.')[-1]
        file_name = '.'.join(file.filename.split('.')[:-1])
        os.replace(
            f'files/{file.filename}',
            f'old_files/{file_name}-{datetime.now().strftime("%d-%m-%y_%H-%M-%S-%f")}.{file_extension}'.replace(' ', '_'),
        )

        # Save new file
        await file.save(f'files/{file.filename}')

    @has_admin_role()
    @is_bot_channel()
    @commands.command(name='update_json')
    async def _update_json(self, ctx: commands.Context, *_) -> None:
        await ctx.message.delete()

        if len(ctx.message.attachments) == 0:
            return await ctx.send(
                f'{ctx.author.mention} '
                'Nie załączyłeś żadnego pliku!',
                delete_after=10
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
            f'{wrong_names_info}',
            delete_after=10
        )

        print(
            f'User {ctx.author.display_name} użył %update_json.\n'
            f'{updated_info}\n'
            f'{wrong_names_info}'
        )


def setup(bot: commands.Bot):
    bot.add_cog(JsonsCog(bot))
