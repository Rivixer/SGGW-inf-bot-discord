from dataclasses import dataclass
from typing import Any

from utils.console import Console
from models.model import Model
from sggw_bot import SGGWBot


@dataclass(slots=True)
class _Group:
    id: int
    description: str
    emoji: str


class AssignRoleModel(Model):

    __slots__ = (
        '__group_roles',
        '__other_roles',
        '__max_groups'
    )

    __group_roles: list[_Group]
    __other_roles: list[_Group]
    __max_groups: int

    def __init__(self, bot: SGGWBot) -> None:
        super().__init__(bot)
        data = super()._load_settings()

        self.max_groups = data.get('max_groups')
        self.__group_roles = list()
        self.__other_roles = list()

        for i in range(self.__max_groups):
            group = self.__load_role(data, f'group_{i+1}')
            self.__group_roles.append(group)

        guest_role = self.__load_role(data, 'guest')
        self.__other_roles.append(guest_role)

    def __load_role(self, data: dict[str, Any], key: str) -> _Group:
        if (group_data := data.get(key)) is None:
            e = KeyError(f'Key {key} not exists in {super()._settings_path}.')
            Console.important_error(
                'Error while loading group from settings.json', e
            )
            raise e

        return _Group(**group_data)

    @staticmethod
    def __validate_max_groups(max_groups) -> None:
        """Valide max_groups.

        Raises
        ------
        TypeError
            max_groups must be int
        ValueError
            max_groups must be between 0 and 6
        """

        if not isinstance(max_groups, int):
            raise TypeError('max_group must be int')
        if not 0 < max_groups < 6:
            raise ValueError('max_group must be between 0 and 6')

    @property
    def max_groups(self) -> int:
        return self.__max_groups

    @max_groups.setter
    def max_groups(self, obj) -> None:
        self.__validate_max_groups(obj)
        self.__max_groups = obj

    @property
    def roles(self) -> list[_Group]:
        roles = self.__group_roles[:self.max_groups]
        roles.extend(self.__other_roles)
        return roles
