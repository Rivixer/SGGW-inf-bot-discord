# pylint: disable-all

from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path

import pytest
from nextcord.embeds import Embed
from pytest import MonkeyPatch

from sggwbot.registration import (
    CodeController,
    CodeModel,
    MailLog,
    MemberData,
    MemberInfo,
    RegistrationModel,
)

TEST_JSON_PATH = Path("test_registration.json")


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
    default_role: RoleMock = DefaultRole()
    members: list[MemberMock] = []

    def get_member(self, member_id: int) -> MemberMock | None:
        for member in self.members:
            if member.id == member_id:
                return member


GUILD = GuildMock()


@pytest.fixture
def member1() -> MemberMock:
    return MemberMock(
        name="TestName1",
        nick="TestNick1",
        discriminator="1234",
        id=1234567890,
        roles=[],
        guild=GUILD,
    )


@pytest.fixture
def member2() -> MemberMock:
    return MemberMock(
        name="TestName2",
        nick="TestNick2",
        discriminator="1235",
        id=1234567891,
        roles=[],
        guild=GUILD,
    )


@pytest.fixture
def guild(member1: MemberMock, member2: MemberMock) -> GuildMock:
    guild = GUILD
    guild.members = [member1, member2]
    return guild


@pytest.fixture
def member_data(monkeypatch: MonkeyPatch, member1: MemberMock) -> MemberData:
    monkeypatch.setattr(MemberData, "__init__", lambda _: None)
    member_data = MemberData()  # type: ignore
    member_data.member = member1  # type: ignore
    member_data.index = "123456"
    return member_data


class BotMock:
    def get_default_guild(self) -> GuildMock:
        return GUILD


@dataclass
class AvatarMock:
    url: str


@dataclass
class MemberMock:
    name: str
    nick: str
    discriminator: str
    id: int
    roles: list[RoleMock]
    guild: GuildMock = GUILD
    avatar: AvatarMock = field(init=False)

    def __post_init__(self) -> None:
        if not self.roles:
            self.roles = [
                RoleMock("Role1", 123, 0x111111),
                RoleMock("Role2", 456, 0x222222),
            ]
        self.avatar = AvatarMock("link.png")

    @property
    def top_role(self) -> RoleMock:
        return self.roles[0]

    @property
    def mention(self) -> str:
        return f"<@{self.id}>"

    @property
    def display_name(self) -> str:
        return self.nick or self.name


def test_member_info_to_embed(member1: MemberMock) -> None:
    data = {
        "FirstName": "First",
        "LastName": "Last",
        "StudentID": "123456",
    }
    info = MemberInfo(member1, data, 1.0)  # type: ignore
    embed = info.to_embed()
    embed2 = (
        Embed(
            title="User information:",
            description="TestName1#1234 (<@1234567890>)",
            color=0x111111,
        )
        .add_field(
            name="First name",
            value="First",
        )
        .add_field(
            name="Last name",
            value="Last",
        )
        .add_field(name="Student ID", value="123456")
        .add_field(name="ID", value=member1.id, inline=False)
        .add_field(name="Roles", value="<@&456>, <@&123>", inline=False)
        .set_thumbnail(url="link.png")
    )

    assert embed.to_dict() == embed2.to_dict()


def test_matching_members(
    monkeypatch: MonkeyPatch,
    member1: MemberMock,
    member2: MemberMock,
    guild: GuildMock,
) -> None:
    monkeypatch.setattr(RegistrationModel, "_registered_users_path", TEST_JSON_PATH)
    registration_model = RegistrationModel(BotMock())  # type: ignore
    member1.guild = guild
    member2.guild = guild

    member_data_1 = {
        "FirstName": "First",
        "LastName": "Last",
        "StudentID": "123456",
    }

    member_data_2 = {
        "FirstName": "First2",
        "LastName": "Last2",
        "StudentID": "123457",
    }

    try:
        with open(TEST_JSON_PATH, "w", encoding="utf-8") as f:
            json.dump(
                {"1234567890": member_data_1, "1234567891": member_data_2},
                f,
            )

        member_info_1 = MemberInfo(member1, member_data_1, 1.0)  # type: ignore
        member_info_2 = MemberInfo(member2, member_data_2, 1.0)  # type: ignore
        result = registration_model.find_matching_members("TestName1")
        assert result == [member_info_1]
        result = registration_model.find_matching_members("TestNick2")
        assert result == [member_info_2]
        result = registration_model.find_matching_members("123457")
        assert result == [member_info_2]
        result = registration_model.find_matching_members("987654")
        assert result == []
        result = registration_model.find_matching_members("asdfasdf")
        assert result == []
        ratio = SequenceMatcher(None, "TestNameX", "TestName").ratio()
        member_info_1.ratio = ratio
        member_info_2.ratio = ratio
        result = registration_model.find_matching_members("TestName")
        assert result == [member_info_1, member_info_2]
    finally:
        TEST_JSON_PATH.unlink()


def test_mail_log() -> None:
    now = dt.datetime.now()
    mail_log = MailLog("123456", [now])
    assert mail_log.to_dict() == {
        "provided_index": "123456",
        "mails_sent_time": [now.timestamp()],
    }


def test_code_model_valid() -> None:
    model = CodeModel("987654", dt.datetime(2022, 11, 23, 12, 34, 56), [])
    assert model._valid_until == dt.datetime(2022, 11, 23, 20, 34, 56)
    assert model.is_valid is False
    assert model.expire == "23.11.2022 20:34:56"

    model = CodeModel("987654", dt.datetime.now(), [])
    assert model.is_valid is True


def test_code_model_should_send_email() -> None:
    model = CodeModel("xxxxxx", dt.datetime.now(), [])
    assert model.should_send_email("123456") is True

    log1 = MailLog("123456", [dt.datetime.now()])
    log2 = MailLog("987654", [dt.datetime.now() - dt.timedelta(minutes=4)])
    log3 = MailLog("555555", [dt.datetime.now() - dt.timedelta(minutes=20)])

    model.mail_logs = [log1]
    assert model.should_send_email("123456") is False
    assert model.should_send_email("987654") is True

    model.mail_logs = [log1, log2]
    assert model.should_send_email("123456") is False
    assert model.should_send_email("987654") is False

    model.mail_logs = [log1, log2, log3]
    assert model.should_send_email("555555") is True


def test_code_model_check_if_blocked() -> None:
    model = CodeModel("xxxxxx", dt.datetime.now(), [])
    assert model.check_if_blocked("123456") is None

    log1 = MailLog("123456", [dt.datetime.now()])
    log2 = MailLog(
        "234567",
        [
            dt.datetime.now() - dt.timedelta(minutes=20),
            dt.datetime.now() - dt.timedelta(minutes=25),
            dt.datetime.now() - dt.timedelta(minutes=30),
        ],
    )
    log3 = MailLog("345678", [dt.datetime.now() - dt.timedelta(minutes=23)])

    model.mail_logs = [log1]
    assert model.check_if_blocked("123456") is None

    model.mail_logs = [log2]
    assert model.check_if_blocked("234567") is not None

    model.mail_logs = [log1, log2]
    assert model.check_if_blocked("555555") is None

    model.mail_logs = [log1, log2, log3]
    assert model.check_if_blocked("555555") is not None

    model = CodeModel("xxxxxx", dt.datetime.now() - dt.timedelta(hours=9), [])
    model.mail_logs = [log2]
    assert model.check_if_blocked("234567") is None


def test_code_model_add_mail_sent_time() -> None:
    model = CodeModel("xxxxxx", dt.datetime.now(), [])
    model.add_mail_sent_time("123456")
    assert model.mail_logs == [MailLog("123456", [dt.datetime.now()])]

    model.add_mail_sent_time("123456")
    assert model.mail_logs == [
        MailLog("123456", [dt.datetime.now(), dt.datetime.now()])
    ]


def test_code_model_to_dict() -> None:
    log1 = MailLog("123456", [dt.datetime.now()])
    model = CodeModel("xxxxxx", dt.datetime.now(), [log1])
    assert model.to_dict() == {
        "code": "xxxxxx",
        "generation_time": dt.datetime.now().timestamp(),
        "mail_logs": [log1.to_dict()],
    }


def test_code_controller_generate_code(member_data: MemberData) -> None:
    controller = CodeController("123456", member_data)
    code = controller._generate_code()
    assert len(code) == 8
    assert code.isascii()
