import asyncio
import json
import os

from nextcord.application_command import SlashOption
from nextcord.interactions import Interaction
from nextcord.channel import TextChannel
from nextcord.message import Message
from nextcord.member import Member
from nextcord.ext import commands
import nextcord

from utils.commands import SlashCommandUtils
from utils.console import Console, FontColour
from sggw_bot import SGGWBot

from .registration_mail_controller import RegistrationMailController
from .registration_code_controller import RegistrationCodeController
from .registered_users_controller import RegisteredUsersContorller
from .registration_student_utils import RegistrationStudentUtils
from .registration_model import RegistrationModel
from .modals.code_modal import CodeModal
from .registration_exceptions import *


class RegistrationCog(commands.Cog):

    __slots__ = (
        '__bot',
        '__model'
    )

    __bot: SGGWBot
    __model: RegistrationModel

    def __init__(self, bot: SGGWBot) -> None:
        self.__bot = bot
        self.__model = RegistrationModel(bot)

    @commands.Cog.listener()
    async def on_message(self, message: Message) -> ...:
        channel_id = self.__model.data.get('registration_channel_id')
        if message.channel.id != channel_id or len(message.embeds) > 0:
            return

        if len(message.embeds) > 0 and message.author == self.__bot.user:
            return

        try:
            await message.delete()
        except:
            pass

    @commands.Cog.listener()
    async def on_ready(self) -> None:
        channel_id = self.__model.data.get('registration_channel_id')
        if channel_id is None:
            return Console.warn(
                'registration_channel_id in registration_settings.json is empty'
            )

        if (channel := self.__bot.get_channel(channel_id)) is None:
            return Console.warn(
                f'Registration channel with id {channel_id} not exists.'
            )

        if not isinstance(channel, TextChannel):
            return Console.warn(
                f'Registration channel {channel} must be TextChannel'
            )

        messages = await channel.history(limit=None).flatten()
        to_delete: list[Message] = []
        for message in messages:
            if message.author != self.__bot.user:
                to_delete.append(message)

        await asyncio.gather(*(message.delete() for message in to_delete))

    @nextcord.slash_command(
        name='register',
        description='Komenda do zarejestrowania się na tym serwerze.',
        dm_permission=False
    )
    @SlashCommandUtils.log()
    async def _register(
        self,
        interaction: Interaction,
        index_no: str = SlashOption(
            name='nr_indeksu',
            description='Twój nr indeksu. Same liczby np. `123456`.',
            min_length=6,
            max_length=6
        )
    ) -> ...:
        if not index_no.isdigit():
            return await interaction.response.send_message(
                'Indeks musi zawierać 6 cyfr!',
                ephemeral=True,
                delete_after=8
            )

        member: Member = interaction.user  # type: ignore
        code_ctrl = RegistrationCodeController(member)

        try:
            try:
                code = code_ctrl.generate_new_code(int(index_no))
                send_mail = True
            except TooManyRegistrationMails as e:
                code = e.old_code
                send_mail = False

            accounts = RegisteredUsersContorller.find_users_by_index(
                member.guild, index_no
            )

            if member in accounts:
                accounts.remove(member)

            if send_mail:
                code_expiration = code_ctrl.code_expiration
                mail_ctrl = RegistrationMailController(
                    member, index_no, code, code_expiration
                )
                await mail_ctrl.send_message()

            student = RegistrationStudentUtils.is_student(index_no) or False

            modal = CodeModal(
                index_no, code, student=student,
                other_accounts=accounts
            )
        except KeyboardInterrupt:
            raise KeyboardInterrupt
        except RegistrationBlocked as e:
            return await interaction.response.send_message(
                str(e), ephemeral=True
            )
        except RegistrationError as e:
            Console.important_error(f'Cannot send email ({index_no=})', e)
            return await interaction.response.send_message(
                'Nie udało się wysłać maila z kodem.\n'
                'Spróbuj ponownie później.\n'
                'Przepraszamy za problemy.',
                ephemeral=True,
                delete_after=60
            )

        await interaction.response.send_modal(modal)

    @nextcord.slash_command(
        name='whois',
        description='Info about a member.',
        dm_permission=False,
        default_member_permissions=1 << 17  # Mention everyone
    )
    @SlashCommandUtils.log()
    async def _whois(
        self,
        interaction: Interaction,
        argument: str = SlashOption(
            description='ID, name, surname or discord nick'
        )
    ) -> ...:
        try:
            embeds = RegisteredUsersContorller.get_embeds_with_matching_users(
                interaction.guild, argument  # type: ignore
            )
        except Exception as e:
            Console.error('Error in _whois command.', exception=e)
            return await interaction.response.send_message('[ERROR], {e}')

        if len(embeds) == 0:
            return await interaction.response.send_message(
                f'Nie znaleziono nikogo podobnego do `{argument}`.',
                ephemeral=True
            )

        await interaction.response.send_message(
            embeds=embeds,
            ephemeral=True
        )

    @nextcord.slash_command(
        name='get_member_info',
        description='Get json with information about a member.',
        dm_permission=False,
        default_member_permissions=1 << 17  # Mention everyone
    )
    @SlashCommandUtils.log()
    async def _get_member_info(
        self,
        interaction: Interaction,
        user_id: str
    ) -> ...:
        try:
            file = RegisteredUsersContorller.get_member_info_json(user_id)
        except (OSError, json.JSONDecodeError) as e:
            await interaction.response.send_message(
                f'Nie udało się pobrać jsona - {e}',
                ephemeral=True
            )
        else:
            await interaction.response.send_message(file=file, ephemeral=True)
        finally:
            try:
                os.remove(f'{user_id}_info_temp.json')
            except:
                pass

    @nextcord.slash_command(
        name='set_member_info',
        description='Update information about a member. '
        'Previous information will be overwritten. It cannot be undone.',
        dm_permission=False,
        default_member_permissions=1 << 17  # Mention everyone
    )
    @SlashCommandUtils.log()
    async def _set_member_info(
        self,
        interaction: Interaction,
        user_id: str,
        file: nextcord.Attachment = SlashOption(
            description='JSON file with member info downloaded from `/get_member_info` and updated.'
        )
    ) -> ...:
        try:
            await RegisteredUsersContorller.save_member_info_json(
                file, user_id
            )
        except KeyboardInterrupt:
            pass
        except Exception as e:
            await interaction.response.send_message(
                f'Nie udało się zaktualizować informacji o członku - {e}',
                ephemeral=True
            )
        else:
            await interaction.response.send_message(
                'Zaktualizowano informacje o członku',
                ephemeral=True
            )


def setup(bot: SGGWBot):
    bot.add_cog(RegistrationCog(bot))
