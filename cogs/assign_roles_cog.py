from discord import RawReactionActionEvent
from nextcord.colour import Colour
from nextcord.ext import commands
from nextcord.embeds import Embed

from utils.checks import has_admin_role


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
        self.__embed_title = 'Wybierz odpowiednią grupę!'

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

        from utils.checks import settings
        emoji = str(payload.emoji)

        guest_role = message.guild.get_role(settings.get('GUEST_ROLE_ID'))
        group_roles = [message.guild.get_role(
            settings.get(f'GR_{i+1}_ID')) for i in range(5)
        ]

        roles = [*group_roles, guest_role]
        for role in roles:
            for member_role in payload.member.roles:
                if role == member_role:
                    await payload.member.remove_roles(role)
                    print(
                        f'Usunięto {payload.member.display_name} rangę {role.name}'
                    )

        if emoji in self.__group_emojis:
            role_to_add = group_roles[self.__group_emojis.index(emoji)]
            await payload.member.add_roles(role_to_add)
            print(
                f'Dodano {payload.member.display_name} rangę {role_to_add.name}'
            )
        elif emoji == self.__guest_emoji:
            await payload.member.add_roles(guest_role)
            print(
                f'Dodano {payload.member.display_name} rangę {guest_role.name}'
            )

        await message.remove_reaction(emoji, payload.member)

    @has_admin_role()
    @commands.command(name='roles_table')
    async def _roles_table(self, ctx: commands.Context, no_of_groups: str = '5', *_) -> None:
        await ctx.message.delete()

        try:
            max_group = int(no_of_groups)
        except ValueError as e:
            return await ctx.send(
                f'Błędna wartość \'no_of_groups\' ({e})',
                delete_after=7
            )

        if not (0 < max_group <= 5):
            return await ctx.send(
                f'Błędna wartość \'no_of_groups\' (musi być z przedziału od 0 do 5)',
                delete_after=7
            )

        values = list()
        emojis = list()
        for i, group_emoji in enumerate(self.__group_emojis):
            if i == max_group:
                break
            values.append(f'{group_emoji} - grupa nr {i+1}')
            emojis.append(group_emoji)
        values.append(f'{self.__guest_emoji} - gość')
        emojis.append(self.__guest_emoji)

        embed = Embed(
            title=self.__embed_title,
            description='Wystarczy, że klikniesz odpowiednią reakcję pod spodem.',
            colour=Colour.yellow()
        ).add_field(
            name='Opis reakcji:',
            value='\n'.join(values)
        )

        message = await ctx.send(embed=embed)

        for emoji in emojis:
            await message.add_reaction(emoji)


def setup(bot: commands.Bot):
    bot.add_cog(AssignRolesCog(bot))
