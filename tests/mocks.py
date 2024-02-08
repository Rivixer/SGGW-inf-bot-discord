# pylint: disable=all

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RoleMock:
    name: str
    id: int
    colour: int

    @property
    def mention(self) -> str:
        return f"<@&{self.id}>"


class DefaultRole(RoleMock):
    def __init__(self) -> None:
        super().__init__("everyone", 0, 0x0)


class GuildMock:
    default_role: RoleMock
    roles: list[RoleMock]
    members: set[MemberMock]

    def __init__(self) -> None:
        self.default_role = DefaultRole()
        self.roles = [self.default_role]
        self.members = set()

    def get_member(self, member_id: int) -> MemberMock | None:
        for member in self.members:
            if member.id == member_id:
                return member

    def get_role(self, role_id: int) -> RoleMock | None:
        for role in self.roles:
            if role.id == role_id:
                return role


@dataclass
class BotMock:
    guild: GuildMock

    def get_default_guild(self) -> GuildMock:
        return self.guild


@dataclass
class AvatarMock:
    url: str


@dataclass
class MemberMock:
    name: str
    nick: str
    id: int
    roles: list[RoleMock]
    discriminator: str | None = None
    avatar: AvatarMock | None = None
    _guild: GuildMock | None = None

    def __post_init__(self) -> None:
        self.avatar = AvatarMock("link.png")
        if self.guild is not None:
            self.guild.members.add(self)
        if not self.roles:
            self.roles = [DefaultRole()]

    def __str__(self) -> str:
        if self.discriminator:
            return f"{self.name}#{self.discriminator}"
        return self.name

    def __hash__(self) -> int:
        return self.id

    @property
    def top_role(self) -> RoleMock:
        return self.roles[0]

    @property
    def mention(self) -> str:
        return f"<@{self.id}>"

    @property
    def display_name(self) -> str:
        return self.nick or self.name

    @property
    def guild(self) -> GuildMock | None:
        return self._guild

    @guild.setter
    def guild(self, new_guild: GuildMock | None) -> None:
        if new_guild is None and self._guild is not None:
            self._guild.members.remove(self)
        elif new_guild is not None:
            new_guild.members.add(self)
        self._guild = new_guild

    async def remove_roles(self, *roles) -> None:
        for role in roles:
            self.roles.remove(role)

    async def add_roles(self, *roles) -> None:
        for role in roles:
            self.roles.append(role)

    def __repr__(self) -> str:
        return f"<MemberMock name='{self.name}' nick='{self.nick}' id={self.id}>"


@dataclass
class PartialEmojiMock:
    emoji: str

    def __str__(self) -> str:
        return self.emoji
