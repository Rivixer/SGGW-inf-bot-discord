from nextcord.member import Member
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import datetime as dt
import string
import random
import json

from utils.console import Console, FontColour

from .registration_exceptions import RegistrationBlocked, TooManyRegistrationMails


@dataclass(slots=True)
class RegistrationCodeController:

    __member: Member

    @property
    def __file_path(self) -> Path:
        """Returns Path where the codes are stored.

        Creates the file if it doesn't exist.
        """

        path = Path('registration/registration_codes.json')
        if not path.exists():
            with open(path, 'w', encoding='utf-8') as f:
                json.dump({}, f, ensure_ascii=True, indent=4)

            Console.specific(
                f'{path} has been created.',
                'Registration', FontColour.YELLOW
            )
        return path

    def __load_data(self) -> dict[str, list[dict[str, Any]]]:
        with open(self.__file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data

    def __save_data(self, data: dict[str, list[dict[str, Any]]]) -> None:
        with open(self.__file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=True, indent=4)

    def __add_info_to_json(
        self,
        index_no: int,
        code: str,
        generated: dt.datetime | None = None,

    ) -> None:
        """Updates info in json.

        If generated is None, it will be replaced by datetime.now().

        Parameters
        ----------
        index_no: `int`
            Index number
        code: `str`
            Generated code
        sent: `datetime
            Datetime when the code was sent
        generated: `datetime | None`
            Datetime when the code was generated
        """

        data = self.__load_data()
        member_id = str(self.__member.id)

        if data.get(member_id) is None:
            data[member_id] = list()

        if generated is None:
            generated = dt.datetime.now()

        info = {
            'index': index_no,
            'code': code,
            'generated': generated.strftime('%Y-%m-%d %H:%M:%S'),
            'sent': dt.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        try:
            data[member_id].append(info)
        except KeyError:
            data[member_id] = [info]

        self.__save_data(data)

    def __get_info_from_json(self) -> list[dict[str, Any]]:
        return self.__load_data().get(str(self.__member.id), [])

    @property
    def code_expiration(self) -> str:
        member_data = self.__get_info_from_json()
        try:
            last_log = member_data[-1]
            generated = dt.datetime.strptime(
                last_log.get('generated'),  # type: ignore
                '%Y-%m-%d %H:%M:%S'
            )
            expiration = generated + dt.timedelta(days=1)
            return expiration.strftime('%Y-%m-%d %H:%M:%S')
        except:
            return 'w niedalekiej przyszłości'

    def generate_new_code(self, index_no: int) -> str:
        """Returns the code that user should provide for registration.

        The code is generated once a day.
        This means that if the previous code was generated less than 24 hours ago,
        it will be returned without updating the generation time.

        Raises
        ------
        TooManyRegistrationMails
            Last mail has been send less than 5 minutes ago
        RegistrationBlocked
            3 different index numbers have been provided
            or more than 5 emails were sent in the last 24 hours
        """

        member_data = self.__get_info_from_json()
        last_indexes = set(i.get('index') for i in member_data)
        if len(last_indexes) >= 3 and index_no not in last_indexes:
            raise RegistrationBlocked(
                'Podałeś 3 razy inny indeks.\n'
                'Rejestracja została **pernamentnie zablokowana**.\n'
                'Jeśli chcesz się odwołać, znajdź Admina z listy po prawej '
                'i napisz do niego prywatną wiadomość.'
            )

        last_day_logs: list[dict[str, Any]] = []
        for log in member_data:
            generated_str = log.get('generated')
            if generated_str is None:
                continue
            generated = dt.datetime.strptime(
                generated_str, '%Y-%m-%d %H:%M:%S')
            if generated + dt.timedelta(days=1) >= dt.datetime.now():
                log_copy = log.copy()
                log_copy['generated'] = generated
                last_day_logs.append(log_copy)

        if len(last_day_logs) >= 5:
            next_try = min(
                i.get('generated') for i in last_day_logs  # type: ignore
            ) + dt.timedelta(days=1)
            raise RegistrationBlocked(
                'Wysłałano zbyt wiele próśb o rejestrację.\n'
                'Rejestracja została **tymczasowo zablokowana**.\n'
                f'Następna możliwa próba: {next_try}'
            )

        try:
            last_log = member_data[-1]
        except:
            pass
        else:
            old_code = last_log.get('code')
            if old_code is not None:
                generated_str = last_log.get('generated')
                if generated_str is not None:
                    generated = dt.datetime.strptime(
                        generated_str, '%Y-%m-%d %H:%M:%S')
                else:
                    generated = dt.datetime.now()

                sent_str = last_log.get('sent')
                if sent_str is not None:
                    sent = dt.datetime.strptime(
                        sent_str, '%Y-%m-%d %H:%M:%S')
                else:
                    sent = dt.datetime.now()

                old_index = last_log.get('index')

                if sent + dt.timedelta(minutes=5) >= dt.datetime.now() and old_index == index_no:
                    raise TooManyRegistrationMails(old_code)

                if generated + dt.timedelta(days=1) >= dt.datetime.now():
                    self.__add_info_to_json(index_no, old_code, generated)
                    return old_code

        code = ''.join([random.choice(string.ascii_letters) for _ in range(8)])
        self.__add_info_to_json(index_no, code)
        return code
