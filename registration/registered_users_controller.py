from difflib import SequenceMatcher
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from abc import ABC
import asyncio
import json
import os

from nextcord.channel import TextChannel
from nextcord.message import Attachment
from nextcord.member import Member
from nextcord.embeds import Embed
from nextcord.guild import Guild
import nextcord

from assign_roles.assign_role_model import AssignRoleModel
from utils.console import Console, FontColour
from utils.settings import settings

from .registration_exceptions import RegistrationError
from .registration_model import RegistrationModel


@dataclass(frozen=True, slots=True)
class _MemberInfo:
    ratio: float
    member: Member
    info: dict[str, Any]

    def __post_init__(self) -> None:
        assert 0 <= self.ratio <= 1

    def __hash__(self) -> int:
        return self.member.id if self.member else 0


class RegisteredUsersController(ABC):

    @staticmethod
    def __get_file_path() -> Path:
        """Returns Path to json where registered users are stored.

        If the file doesn't exist, it creates new one.
        """

        path = Path('registration/registered_users.json')
        if not path.exists():
            with open(path, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=True, indent=4)

            Console.specific(
                f'{path} has been created.',
                'Registration', FontColour.YELLOW
            )
        return path

    @classmethod
    def __load_data(cls) -> dict[str, dict[str, Any]]:
        """Loads data from json.

        Prints warning to the console if the file is empty.

        Raises
        ------
        OSError
            Cannot open file
        JSONDecodeError
            Json file is corrupted
        """

        with open(cls.__get_file_path(), 'r', encoding='utf-8') as f:
            data = json.load(f)

        if len(data) == 0:
            Console.warn(f'The file {cls.__get_file_path()} is empty.')

        return data

    @classmethod
    async def register_user(cls, member: Member, index_no: str, other_info: dict[str, str]) -> None:
        """Gives the member a verified role.

        Saves index_no and other_info (e.g. why it is his second account)
            in registered_users.json.

        Raises
        ------
        RegistrationError
            Registration failed
        """

        try:
            data = cls.__load_data()
        except Exception as e:
            raise RegistrationError from e

        try:
            data[str(member.id)]['StudentID'] = int(index_no)
        except KeyError:
            data[str(member.id)] = {'StudentID': int(index_no)}

        for k, v in other_info.items():
            data[str(member.id)][k] = v

        # We don't need to send the bot parameter,
        # because we don't use it,
        # and the model will be deleted at the end of this function
        model = RegistrationModel(None)  # type: ignore
        verified_role = model.get_verified_role(member.guild)

        if verified_role is None:
            raise RegistrationError('verified_role is None')

        try:
            with open(cls.__get_file_path(), 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=True, indent=4)
        except Exception as e:
            raise RegistrationError(e)

        async def send_message_in_bot_channel():
            channel_id = settings.get('BOT_CHANNEL_ID')
            if channel_id is None:
                return
            channel = member.guild.get_channel(channel_id)
            if not isinstance(channel, TextChannel):
                return
            await channel.send(
                f'**Użytkownik {member.display_name}#{member.discriminator} '
                f'zarejestrował się!** (index={index_no}) ' +
                (f'\n{other_info}' if other_info else '')
            )

        await asyncio.gather(
            member.add_roles(verified_role),
            send_message_in_bot_channel()
        )

    @classmethod
    def find_users_by_index(cls, guild: Guild, index: str) -> list[Member]:
        """Returns a list of members with the same index as provided.

        Raises
        ------
        OSError
            Cannot open json file
        JSONDecodeError
            Json file is corrupted
        """

        data = cls.__load_data()

        members = []
        for user_id, user_data in data.items():
            if str(user_data.get('StudentID')) == index:
                members.append(guild.get_member(int(user_id)))
        return members

    @classmethod
    def get_embeds_with_matching_users(cls, guild: Guild, arg: str) -> list[Embed]:
        """Returns list of embeds with information about members matching the argument `arg`.

        Member information will be got from 'registered_users.json'.

        Parameters
        ----------
        guild: `nextcord.Guild`
            A guild whose members can be found by ID.
        arg: `str`
            User search argument. It can be a user ID, display name, name, surname or index number.
            Display name, name and surname may contain typos.

        Returns
        -------
        `list[Embed]`
            The list of embeds sorted ascending by ratio.

        Raises
        ------
        OSError
            Cannot open json file
        JSONDecodeError
            Json file is corrupted
        """

        data = cls.__load_data()

        matching_members: set[_MemberInfo] = set()

        for member in guild.members:
            member_data = data.get(str(member.id), {})

            arg = arg.lower()

            name = member_data.get('Name', '')
            surname = member_data.get('Surname', '')
            student_id = member_data.get('StudentID')

            to_compare = list(filter(None, (
                member.display_name,
                member.name,
                name,
                surname,
                name+surname,
                surname+name,
                str(member.id),
                str(student_id)
            )))

            ratio = max([
                SequenceMatcher(None, i.lower(), arg).ratio()
                for i in to_compare
            ])

            member_info = _MemberInfo(ratio, member, member_data)
            matching_members.add(member_info)

        max_ratio = max(map(lambda i: i.ratio, matching_members))
        threshold = max_ratio * 0.9
        embeds = []

        if max_ratio <= 0.5:
            return embeds

        for member_info in sorted(matching_members, key=lambda i: i.ratio):
            if threshold <= member_info.ratio:
                embed = cls.__convert_member_to_embed(member_info)
                embeds.append(embed)

        return embeds

    @staticmethod
    def __convert_member_to_embed(member_info: _MemberInfo) -> Embed:
        """Converts _MemberInfo and returns info in Embed."""

        member = member_info.member
        info = member_info.info

        embed = Embed(
            title='Informacje o użytkowniku:',
            description=f'{member.name}#{member.discriminator} ({member.mention})',
            colour=member.top_role.colour
        ).set_thumbnail(
            url=member.avatar.url if member.avatar else member.default_avatar.url
        )

        for k, v in info.items():
            embed.add_field(name=k, value=v)

        everyone = member.guild.default_role
        roles_info = [r.mention for r in member.roles if r != everyone][::-1]
        embed.add_field(name='Role', value=', '.join(roles_info), inline=False)

        return embed

    @classmethod
    def get_member_info_json(cls, member_id: int | str) -> nextcord.File:
        """Returns `nextcord.File` with member information in json.

        Stores it in <member_id>_info_temp.json.

        Raises
        ------
        OSError
            Cannot open file
        """

        temp_filename = f'{member_id}_info_temp.json'
        data = cls.__load_data()

        member_data = data.get(str(member_id), {})

        with open(temp_filename, 'w', encoding='utf-8') as f:
            json.dump(member_data, f, indent=4)

        return nextcord.File(temp_filename, f'{member_id}_info.json')

    @classmethod
    async def save_member_info_json(
        cls,
        file: Attachment,
        member_id: int | str
    ) -> None:
        """|coro|

        Sets the member information from the json attached in the message.

        Temporarily saves the attachment to a <member_id>_info_temp.json.
        Deletes it after reading it.

        Even though the exception has been raised,
        if a temporary file has been created it will be deleted.

        Parameters
        ----------
        - file: `nextcord.Attachment` - An attachment enclosed in the file.
        - member_id: `str` - ID of the member whose information will be updated.

        Raises
        ------
        IndexError
            Must be only one attachment
        nextcord.HTTPException
            Save an attachment failed
        OSError
            Read an attachment or json update failed
        JSONDecodeError
            Json file is corrupted
        """

        temp_filename = f'{member_id}_info_temp.json'

        try:
            await file.save(temp_filename)

            with open(temp_filename, 'r', encoding='utf-8') as f:
                member_data = json.load(f)

            data = cls.__load_data()
            data[str(member_id)] = member_data

            with open(cls.__get_file_path(), 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=True, indent=4)
        finally:
            try:
                os.remove(temp_filename)
            except:
                pass
