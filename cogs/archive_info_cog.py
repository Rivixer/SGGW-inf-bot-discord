from typing import TypeVar
import matplotlib
import json

from nextcord.colour import Colour
from nextcord.ext import commands
from nextcord.embeds import Embed
import nextcord

from utils.checks import has_admin_role, is_bot_channel
from utils.settings import update_settings, settings
from utils.message import MainMessageUtils
from utils.update_embed import UpdateEmbed
from utils.console import Console
from main import BOT_PREFIX

T = TypeVar('T', bound=dict[str, dict[str, str | dict[str, str]]])

_MSG_JSON_NAME = 'ARCHIVE_INFO_MSG'


class ArchiveInfoCog(commands.Cog):

    __slots__ = '__bot'

    def __init__(self, bot: commands.Bot) -> None:
        self.__bot = bot

    def generate_embeds(self, *, preview: bool = False) -> list[Embed]:
        path = f'files{"/preview" if preview else ""}/archive_links.json'

        try:
            with open(path, encoding='utf-8') as f:
                data: T = json.load(f)
        except OSError as e:
            Console.error(f'Nie można załadować {path}', exception=e)
            return []

        embeds: list[embed] = list()

        for semestr_name, semestr_data in data.items():
            colour_hex = semestr_data.get('Colour')

            if colour_hex is not None:
                colour_rgb = matplotlib.colors.to_rgb(colour_hex)
                colour = Colour.from_rgb(
                    *map(lambda i: int(i*255), colour_rgb)
                )
            else:
                colour = Colour.light_gray()

            embed = Embed(
                title=semestr_name,
                colour=colour
            )

            if preview:
                embed.set_author(name='PREVIEW')

            for category_name, category_data in semestr_data.items():
                if category_name in ('Footer', 'Colour'):
                    continue

                values: list[str] = []
                for link_name, link_url in category_data.items():
                    values.append(f'[{link_name}]({link_url})')

                embed.add_field(
                    name=f'{category_name}:',
                    value='\n'.join(values),
                    inline=False
                )

            if footer := semestr_data.get('Footer'):
                embed.set_footer(text=footer)

            embeds.append(embed)

        return embeds

    @commands.group(name='archive', brief='Embeds with old things')
    @has_admin_role()
    async def _archive(self, *_) -> None:
        pass

    @_archive.command(
        name='send',
        brief='Send new main message',
        description='''The command message will be deleted.
        The sent message will be the main message now.
        The channel where the message was sent
        will be now the main channel of this message.
        If old main message exists, delete it.'''
    )
    async def _send(self, ctx: commands.Context, *_) -> None:
        await ctx.message.delete()

        try:
            _, old_message = await MainMessageUtils.fetch_channel_n_msg(
                ctx, _MSG_JSON_NAME
            )
        except:
            ...
        else:
            await old_message.delete()

        embeds = self.generate_embeds()
        message = await ctx.send(embeds=embeds)
        update_settings(
            _MSG_JSON_NAME, {
                "MSG_ID": message.id,
                "CHANNEL_ID": ctx.channel.id
            }
        )

    @_archive.command(
        name='update',
        brief='Update current main message',
        description='''You can use this on any channel,
        but only on the main channel the message will be deleted.
        If main message not exists, send info about it.
        '''
    )
    async def _update(self, ctx: commands.Context, *_) -> None:
        msg_settings: dict = settings.get(_MSG_JSON_NAME)
        channel_id = msg_settings.get('CHANNEL_ID')

        if channel_id == ctx.channel.id:
            await ctx.message.delete()

        try:
            channel, message = await MainMessageUtils.fetch_channel_n_msg(
                ctx, _MSG_JSON_NAME
            )
        except (nextcord.NotFound, nextcord.HTTPException, commands.errors.CommandInvokeError):
            return await ctx.send(
                f'{ctx.author.mention} Nie znaleziono wiadmomości do zaktualizowania. '
                f'Zaktualizuj settings.json lub użyj komendy \'{BOT_PREFIX}archive send\'.',
                delete_after=(10 if channel_id == ctx.channel.id else None)
            )

        UpdateEmbed.override_file('archive_links')

        embeds = self.generate_embeds()
        await message.edit(embeds=embeds)

        if channel.id != ctx.channel.id:
            await ctx.send(
                f'{ctx.author.mention} Zaktualizowano archive_info na {channel.mention}'
            )

    @ is_bot_channel()
    @ _archive.command(
        name='preview',
        brief='Show preview of archive info embeds',
        description='Only on the bot-channel.'
    )
    async def _preview(self, ctx: commands.Context, *_) -> None:
        embeds = self.generate_embeds(preview=True)
        await ctx.send(embeds=embeds)


def setup(bot: commands.Bot):
    bot.add_cog(ArchiveInfoCog(bot))
