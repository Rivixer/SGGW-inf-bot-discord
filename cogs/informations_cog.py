from datetime import datetime
from typing import TypeVar
import json

from nextcord.colour import Colour
from nextcord.ext import commands
from nextcord.embeds import Embed
import nextcord
from utils.console import Console
from utils.message import MainMessageUtils

from utils.settings import update_settings, settings
from utils.checks import has_admin_role, is_bot_channel
from main import BOT_PREFIX
from utils.update_embed import UpdateEmbed


_T = TypeVar('_T', bound=dict[str, dict[str, str]])

_MSG_JSON_NAME = 'INFO_MSG'


class InformationsCog(commands.Cog):

    __slots__ = '__bot',

    __bot: commands.Bot

    def __init__(self, bot: commands.Bot) -> None:
        self.__bot = bot

    def __add_council_field(self, embed: Embed, *, preview: bool = False) -> None:
        file_path = f'files{"/preview" if preview else ""}/council.json'

        try:
            with open(file_path, encoding='utf-8') as f:
                council: _T = json.load(f)
        except OSError as e:
            return Console.important_error(
                f'Nie udało się wczytać pliku {file_path}', e
            )

        users: list[str] = list()

        for user_role_name, user_data in council.items():
            user_name = user_data.get('Name')
            user_id = user_data.get('UserID')
            user = self.__bot.get_user(user_id)

            if user is not None:
                users.append(f'{user_role_name}: {user_name} ({user.mention})')
            else:
                users.append(f'{user_role_name}: {user_name}')

        embed.add_field(
            name='Trójka / Rada:',
            value='\n'.join(users),
            inline=False
        )

    def __add_info_fields(self, embed: Embed, path: str) -> None:
        try:
            with open(path, encoding='utf-8') as f:
                info: _T = json.load(f)
        except OSError as e:
            return Console.important_error(
                f'Nie udało się wczytać pliku {path}', e
            )

        for info_name, info_data in info.items():
            embed.add_field(
                name=f'{info_name}:',
                value=info_data,
                inline=False
            )

    def __add_link_fields(self, embed: Embed, *, preview: bool = False) -> None:
        file_path = f'files{"/preview" if preview else ""}/links.json'

        try:
            with open(file_path, encoding='utf-8') as f:
                council: _T = json.load(f)
        except OSError as e:
            return Console.important_error(
                f'Nie udało się wczytać pliku {file_path}', e
            )

        for category_name, category_data in council.items():

            values: list[str] = list()
            for link_name, link_url in category_data.items():
                values.append(f'[{link_name}]({link_url})')

            embed.add_field(
                name=f'{category_name}:',
                value='\n'.join(values),
                inline=False
            )

    def generate_embed(self, ctx: commands.Context, preview: bool = False) -> Embed:
        embed = Embed(
            title='Informacje',
            description=f'Aktualizacja: {datetime.now().strftime("%d.%m.%Y %H:%M")}',
            colour=Colour.red()
        )

        if preview:
            embed.set_author(name='PREVIEW')

        if guild_icon := ctx.guild.icon:
            embed.set_thumbnail(url=guild_icon.url)

        self.__add_council_field(embed, preview=preview)
        self.__add_info_fields(
            embed, f'files{"/preview" if preview else ""}/info.json'
        )
        self.__add_link_fields(embed)
        self.__add_info_fields(
            embed, f'files{"/preview" if preview else ""}/info2.json'
        )

        embed.set_footer(
            text='Zalecane jest ustawienie pseudonimu z imieniem i 1. literą nazwiska.'
        )

        return embed

    @commands.group(name='info', brief='Send info embed')
    @has_admin_role()
    async def _info(self, *_) -> None:
        pass

    @_info.command(
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

        embed = self.generate_embed(ctx)
        message = await ctx.send(embed=embed)
        update_settings(
            _MSG_JSON_NAME, {
                "MSG_ID": message.id,
                "CHANNEL_ID": ctx.channel.id
            }
        )

    @_info.command(
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
                f'Zaktualizuj settings.json lub użyj komendy \'{BOT_PREFIX}info send\'.',
                delete_after=(10 if channel_id == ctx.channel.id else None)
            )

        UpdateEmbed.override_file('info')
        UpdateEmbed.override_file('info2')
        UpdateEmbed.override_file('council')
        UpdateEmbed.override_file('links')

        embed = self.generate_embed(ctx)
        await message.edit(embed=embed)

        if channel.id != ctx.channel.id:
            await ctx.send(
                f'{ctx.author.mention} Zaktualizowano info na {channel.mention}'
            )

    @is_bot_channel()
    @_info.command(
        name='preview',
        brief='Show preview of archive info embeds',
        description='Only on the bot-channel.'
    )
    async def _preview(self, ctx: commands.Context, *_) -> None:
        embed = self.generate_embed(ctx, preview=True)
        await ctx.send(embed=embed)


def setup(bot: commands.Bot):
    bot.add_cog(InformationsCog(bot))
