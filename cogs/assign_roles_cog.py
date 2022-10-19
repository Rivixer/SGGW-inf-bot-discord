from typing import Generator
import asyncio


from nextcord.raw_models import RawReactionActionEvent
from nextcord.message import Message
from nextcord.colour import Colour
from nextcord.ext import commands
from nextcord.embeds import Embed
import nextcord

from utils.checks import has_admin_role, is_bot_channel
from utils.message import MainMessageUtils
from utils.settings import update_settings, settings
from utils.console import Console, FontColour


_MSG_JSON_NAME = 'ROLES_MSG'


class AssignRolesCog(commands.Cog):

    __slots__ = (
        '__bot',
        '__group_emojis',
        '__guest_emoji',
        '__embed_title'
    )

    __bot: commands.Bot
    __group_emojis: list[str]
    __guest_emoji: str
    __embed_title: str

    def __init__(self, bot: commands.Bot) -> None:
        self.__bot = bot
        self.__group_emojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣']
        self.__guest_emoji = '*️⃣'
        self.__embed_title = 'Przydziel się do swojej grupy labolatoryjnej!'

    async def __remove_old_roles(self, member: nextcord.Member, *roles: nextcord.Role) -> None:
        for role in roles:
            for member_role in member.roles:
                if role == member_role:
                    await member.remove_roles(role)
                    Console.specific(
                        f'{member.display_name}: usunięto rangę {role.name}',
                        'Role', FontColour.PINK
                    )

    async def __assign_new_role(self, member: nextcord.Member, role: nextcord.Role) -> None:
        await member.add_roles(role)
        Console.specific(
            f'{member.display_name}: dodano rangę {role.name}',
            'Role', FontColour.PINK
        )

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: RawReactionActionEvent) -> None:
        if payload.member.bot:
            return

        channel = self.__bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)

        if not message.author.bot:
            return

        if len(message.embeds) == 0 or message.embeds[0].title != self.__embed_title:
            return

        reaction = nextcord.utils.get(
            message.reactions,
            emoji=payload.emoji.name
        )

        if reaction is None or self.__bot.user not in await reaction.users().flatten():
            return await message.remove_reaction(reaction or payload.emoji, payload.member)

        from utils.checks import settings
        emoji = str(payload.emoji)

        guest_role = message.guild.get_role(settings.get('GUEST_ROLE_ID'))
        group_roles = [message.guild.get_role(
            settings.get(f'GR_{i+1}_ID')) for i in range(5)
        ]

        all_roles = [*group_roles, guest_role]

        await self.__remove_old_roles(payload.member, *all_roles)

        if emoji in self.__group_emojis:
            role_to_assign = group_roles[self.__group_emojis.index(emoji)]
        elif emoji == self.__guest_emoji:
            role_to_assign = guest_role

        await asyncio.gather(
            self.__assign_new_role(payload.member, role_to_assign),
            message.remove_reaction(emoji, payload.member)
        )

    def __generate_emojis(self, max_group: int) -> Generator[str, None, None]:
        for i, emoji in enumerate(self.__group_emojis):
            if i == max_group:
                break
            yield emoji

    def generate_embed(self, max_group: int | None = None, *, preview: bool = False) -> Embed:
        if max_group is None:
            max_group = len(self.__group_emojis)

        values = list()
        emojis = list()
        for i, group_emoji in enumerate(self.__generate_emojis(max_group)):
            values.append(f'{group_emoji} - grupa nr {i+1}')
            emojis.append(group_emoji)
        values.append(f'{self.__guest_emoji} - gość')
        emojis.append(self.__guest_emoji)

        embed = Embed(
            title=self.__embed_title,
            description='Możesz należeć tylko do 1 grupy.',
            colour=Colour.yellow()
        ).add_field(
            name='Kliknij pod spodem odpowiednią reakcję:',
            value='\n'.join(values)
        ).set_footer(
            text='Nie spam! Twoja reakcja zostanie cofnięta po zmianie grupy.'
        )

        if preview:
            embed.set_author(name='PREVIEW')

        return embed

    def __validate_max_groups_input(self, max_group_input: str | None) -> str | None:
        """Return reason if validate failed."""

        if max_group_input is None:
            return 'Podaj dodatkowy argument \'max_group\' (od 1 do 5)'

        try:
            no_of_groups = int(max_group_input)
        except ValueError as e:
            return f'Błędna wartość \'max_group\' ({e})'

        if not (0 < no_of_groups <= 5):
            return f'Błędna wartość \'max_group\' (musi być z przedziału od 1 do 5)'

    @has_admin_role()
    @commands.group(name='roles', brief='Embed with function to choose lab group')
    async def _roles(self, *_) -> None:
        pass

    @_roles.command(
        name='send',
        brief='Send new main message',
        description='''The command message will be deleted.
        The sent message will be the main message now.
        The channel where the message was sent
        will be now the main channel of this message.
        If old main message exists, delete it.'''
    )
    async def _send(
        self,
        ctx: commands.Context,
        max_group: str | None = None,
        * _
    ) -> None:

        await ctx.message.delete()

        try:
            _, old_message = await MainMessageUtils.fetch_channel_n_msg(
                ctx, _MSG_JSON_NAME
            )
        except:
            ...
        else:
            await old_message.delete()

        if reason := self.__validate_max_groups_input(max_group):
            return await ctx.send(
                f'{ctx.author.mention} {reason}',
                delete_after=7
            )

        max_group = int(max_group)
        embed = self.generate_embed(max_group)
        message = await ctx.send(embed=embed)

        update_settings(
            _MSG_JSON_NAME, {
                "MSG_ID": message.id,
                "CHANNEL_ID": ctx.channel.id
            }
        )

        all_emojis = [
            *list(self.__generate_emojis(max_group)),
            self.__guest_emoji
        ]

        for emoji in all_emojis:
            await message.add_reaction(emoji)

    @ _roles.command(
        name='update',
        brief='Update current main message',
        description='''You can use this on any channel,
        but only on the main channel the message will be deleted.
        If main message not exists, send info about it.
        '''
    )
    async def _update(
        self,
        ctx: commands.Context,
        max_group: str | None = None,
        * _
    ) -> None:
        msg_settings: dict = settings.get(_MSG_JSON_NAME)
        channel_id = msg_settings.get("CHANNEL_ID")

        if channel_id == ctx.channel.id:
            await ctx.message.delete()

        if reason := self.__validate_max_groups_input(max_group):
            return await ctx.send(
                f'{ctx.author.mention} {reason}',
                delete_after=(7 if channel_id == ctx.channel.id else None)
            )

        max_group = int(max_group)

        try:
            channel, message = await MainMessageUtils.fetch_channel_n_msg(
                ctx, _MSG_JSON_NAME
            )
        except (nextcord.NotFound, nextcord.HTTPException, commands.errors.CommandInvokeError):
            return await ctx.send(
                'Nie znaleziono wiadmomości do zaktualizowania. '
                'Zaktualizuj settings.json lub użyj komendy \'roles send\'.',
                delete_after=(10 if channel_id == ctx.channel.id else None)
            )

        embed = self.generate_embed(max_group)
        await asyncio.gather(
            message.edit(embed=embed),
            message.clear_reactions()
        )

        if channel.id != ctx.channel.id:
            await ctx.send(
                f'{ctx.author.mention} Zaktualizowano role na {ctx.channel.mention}'
            )

        all_emojis = [
            *list(self.__generate_emojis(max_group)),
            self.__guest_emoji
        ]

        for emoji in all_emojis:
            await message.add_reaction(emoji)

    @is_bot_channel()
    @_roles.command(
        name='preview',
        brief='Show preview of archive info embeds',
        description='Only on the bot-channel.'
    )
    async def _preview(self, ctx: commands.Context, max_group: str | None = None, *_) -> None:
        if reason := self.__validate_max_groups_input(max_group):
            return await ctx.send(f'{ctx.author.mention} {reason}')

        embed = self.generate_embed(int(max_group), preview=True)
        await ctx.send(embed=embed)


def setup(bot: commands.Bot):
    bot.add_cog(AssignRolesCog(bot))
