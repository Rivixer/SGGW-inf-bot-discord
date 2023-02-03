from dataclasses import dataclass
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import aiosmtplib
import os

from nextcord.member import Member

from utils.console import Console, FontColour

from .registration_exceptions import RegistrationError


@dataclass(slots=True)
class RegistrationMailController:

    __member: Member
    __index_no: str
    __code: str
    __code_expiration: str

    @property
    def __sggw_mail_domain(self) -> str:
        domain = os.environ.get("SGGW_MAIL_DOMAIN")
        if domain is None:
            raise RegistrationError('SGGW_MAIL_DOMAIN in .env is empty')
        return domain

    @property
    def __message(self) -> MIMEMultipart:
        message = MIMEMultipart()
        message['Subject'] = 'Rejestracja Discord'
        message['From'] = 'noreply'
        message['To'] = f's{self.__index_no}@{self.__sggw_mail_domain}'

        with open('registration/mail_prototype.html', 'r', encoding='utf-8') as f:
            text = f.read()

        server_icon = self.__member.guild.icon
        user_avatar = self.__member.avatar

        text = text.replace(
            '{{USER_DISPLAY_NAME}}', self.__member.display_name
        ).replace(
            '{{USER_DISCRIMINATOR}}', self.__member.discriminator
        ).replace(
            '{{REGISTRATION_CODE}}', self.__code
        ).replace(
            '{{DISCORD_NAME}}', self.__member.guild.name
        ).replace(
            '{{CODE_EXPIRATION}}', self.__code_expiration
        )

        if user_avatar:
            text = text.replace("{{USER_AVATAR}}", user_avatar.url)

        if server_icon:
            text = text.replace('{{DISCORD_LOGO}}', server_icon.url)

        message.attach(MIMEText(text, 'html', 'utf-8'))

        return message

    async def send_message(self) -> None:
        """Sends email with a code.

        Raises
        ------
        RegistrationError
            Email cannot be sent
        """

        username = os.environ.get('MAIL_ADDRESS')
        password = os.environ.get('MAIL_PASSWORD')

        if username is None or password is None:
            raise RegistrationError(
                'MAIL_ADRESS or MAIL_PASSWORD in .env is empty'
            )

        async with aiosmtplib.SMTP(
            hostname='smtp.gmail.com',
            port=465,
            use_tls=True
        ) as smtp:
            try:
                await smtp.login(
                    username=username,
                    password=password
                )
                await smtp.send_message(self.__message)
            except Exception as e:
                raise RegistrationError(e)

        Console.specific(
            f'Email with code {self.__code} has been sent to '
            f's{self.__index_no}@{self.__sggw_mail_domain}',
            'Registration', FontColour.PINK
        )
