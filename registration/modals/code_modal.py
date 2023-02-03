import os

from nextcord.interactions import Interaction
from nextcord.enums import TextInputStyle
from nextcord.ui import Modal, TextInput
from nextcord.member import Member

from utils.console import Console

from ..registered_users_controller import RegisteredUsersContorller
from ..registration_exceptions import RegistrationError


class CodeModal(Modal):

    __slots__ = (
        '__index_no'
        '__student',
        '__other_accounts',
        '__code'
    )

    __index_no: str
    __student: bool
    __other_accounts: list[Member]
    __code: str

    def __init__(
        self,
        index_no: str,
        code: str,
        *,
        student: bool,
        other_accounts: list[Member] | None = None
    ) -> None:
        """Modal for entering the code sent by email"""

        super().__init__(title='Rejestracja', timeout=None)

        self.__code = code
        self.__index_no = index_no
        self.__student = student
        self.__other_accounts = other_accounts or []

        self.add_item(self.__code_input)

        if not self.__student:
            self.add_item(self.__more_info_input)

        if self.__other_accounts:
            self.add_item(self.__other_account_info)

    @property
    def __code_input(self) -> TextInput:
        """Returns a TextInput with a field to enter the code sent by mail."""

        domain = os.environ.get("SGGW_MAIL_DOMAIN")

        if domain is None:
            raise RegistrationError('SGGW_MAIL_DOMAIN in .env is empty')

        return TextInput(
            label='Wprowadź kod:',
            placeholder=f'wysłany na s{self.__index_no}@{domain}',
            required=True,
            min_length=8,
            max_length=8,
        )

    @property
    def __more_info_input(self) -> TextInput:
        """Returns a TextInput with a field to enter additional information
        as to why a non-student wants to register.
        """

        return TextInput(
            label='Dlaczego tu jesteś?',
            placeholder='Nie ma Cię na liście.\n'
            'Jesteś z roku niżej/wyżej? Twierdzisz, że to błąd?\n'
            'Powiadom nas o tym tutaj!',
            style=TextInputStyle.paragraph,
            required=True,
        )

    @property
    def __other_account_info(self) -> TextInput:
        """Returns TextInput with field to input info about second account."""

        if (account_count := len(self.__other_accounts)) == 1:
            account_count_info = '1 konto'
        elif account_count < 5:
            account_count_info = f'{account_count} konta'
        else:
            account_count_info = f'{account_count} kont'

        return TextInput(
            label='Do czego Ci kolejne konto?',
            placeholder=f'Masz już {account_count_info}.\n'
            'Być może streamujesz z tableta?\n'
            'Daj znać! Które konto ma być Twoim głównym?',
            style=TextInputStyle.paragraph,
            required=True,
        )

    async def callback(self, interaction: Interaction) -> ...:
        code_input = self.children[0]

        if not isinstance(code_input, TextInput):
            raise TypeError('code_input must be TextInput')

        if code_input.value != self.__code:
            return await interaction.response.send_message(
                'Kod jest niepoprawny!',
                ephemeral=True,
                delete_after=30
            )

        other_info = dict()

        if not self.__student:
            non_student_input = self.children[1]
            if isinstance(non_student_input, TextInput):
                other_info['Non-student reason'] = non_student_input.value
            if self.__other_accounts:
                another_account_input = self.children[2]
                if isinstance(another_account_input, TextInput):
                    other_info['Another account reason'] = another_account_input.value
        elif self.__other_accounts:
            another_account_input = self.children[1]
            if isinstance(another_account_input, TextInput):
                other_info['Another account reason'] = another_account_input.value

        try:
            await RegisteredUsersContorller.register_user(
                interaction.user, self.__index_no, other_info  # type: ignore
            )
        except RegistrationError as e:
            Console.important_error('Cannot register user', e)
            return interaction.response.send_message(
                'Coś poszło nie tak z rejestracją.\n'
                'Spróbuj ponownie poźniej.\n'
                'Przepraszamy za utrudnienia.',
                ephemeral=True,
                delete_after=30
            )

        await interaction.response.send_message(
            '**Zarejestrowano.**\n'
            'Odwiedź ***#informacje*** po więcej informacji.',
            ephemeral=True,
            delete_after=30
        )
