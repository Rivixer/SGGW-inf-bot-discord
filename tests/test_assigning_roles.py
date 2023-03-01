# pylint: disable=all

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Generator

import pytest
from pytest import MonkeyPatch

from sggwbot.assigning_roles import (
    AssigningRolesController,
    AssigningRolesEmbedModel,
    AssigningRolesModel,
    Group,
)

TEST_JSON_PATH = Path("test_assigning_roles.json")


class BotMock:
    pass


@pytest.fixture
def model(monkeypatch: MonkeyPatch) -> Generator[AssigningRolesModel, None, None]:
    data = {
        "groups": {
            "max_groups": 1,
            "group_0": {"role_id": 123, "description": "Role number 1", "emoji": "1️⃣"},
            "guest": {"role_id": 345, "description": "Guest role", "emoji": "*️⃣"},
        }
    }
    with open(TEST_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f)
    monkeypatch.setattr(AssigningRolesModel, "_settings_path", TEST_JSON_PATH)
    yield AssigningRolesModel()
    TEST_JSON_PATH.unlink()


@pytest.fixture
def embed_model(model: AssigningRolesModel) -> AssigningRolesEmbedModel:
    return AssigningRolesEmbedModel(model, BotMock())  # type: ignore


@pytest.fixture
def ctrl(
    model: AssigningRolesModel, embed_model: AssigningRolesEmbedModel
) -> AssigningRolesController:
    return AssigningRolesController(model, embed_model)


@pytest.fixture
def default_groups() -> list[Group]:
    return [Group(123, "Role number 1", "1️⃣"), Group(345, "Guest role", "*️⃣")]


def _add_group_to_json(name: str, role_id: int, desc: str, emoji: str) -> None:
    with open(TEST_JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    data["groups"][name] = {"role_id": role_id, "description": desc, "emoji": emoji}
    with open(TEST_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f)


def test_group_info() -> None:
    group = Group(123, "testing group", "1️⃣")
    assert group.info == "1️⃣ - testing group"


def test_max_groups(model: AssigningRolesModel) -> None:
    assert model.max_groups == 1


def test_set_max_group(model: AssigningRolesModel) -> None:
    model.max_groups = 2
    assert model.max_groups == 2
    with pytest.raises(TypeError):
        model.max_groups = "a"
    with pytest.raises(ValueError):
        model.max_groups = 0
    with pytest.raises(ValueError):
        model.max_groups = 9


def test_load_not_existsing_group(model: AssigningRolesModel) -> None:
    with pytest.raises(KeyError):
        model._load_group("not_existsing_group")


def test_load_groups(model: AssigningRolesModel) -> None:
    _add_group_to_json("group_1", 345, "desc3", "3️⃣")
    model.reload_settings()


def test_groups_data(model: AssigningRolesModel) -> None:
    expected = {
        "max_groups": 1,
        "group_0": {"role_id": 123, "description": "Role number 1", "emoji": "1️⃣"},
        "guest": {"role_id": 345, "description": "Guest role", "emoji": "*️⃣"},
    }

    assert model._groups_data == expected
    open(TEST_JSON_PATH, "w", encoding="utf-8").write("{}")
    with pytest.raises(TypeError):
        model.reload_settings()


def test_list_of_groups(
    monkeypatch: MonkeyPatch, model: AssigningRolesModel, default_groups: list[Group]
) -> None:
    _add_group_to_json("group_1", 345, "desc3", "3️⃣")
    model.reload_settings()
    group1 = Group(345, "desc3", "3️⃣")
    assert model.groups == default_groups
    monkeypatch.setattr(AssigningRolesModel, "_max_groups", 2)
    expected = default_groups
    expected.insert(1, group1)
    assert model.groups == expected


@dataclass
class PartialEmojiMock:
    emoji: str

    def __str__(self) -> str:
        return self.emoji


@dataclass
class RoleMock:
    id: int
    desc: str
    emoji: str


class GuildMock:

    roles: list[RoleMock] = [
        RoleMock(123, "group_0", "1️⃣"),
        RoleMock(345, "guest", "*️⃣"),
    ]

    def get_role(self, role_id: int) -> RoleMock | None:
        for role in self.roles:
            if role.id == role_id:
                return role


class MemberMock:

    roles: list[RoleMock]
    guild: GuildMock

    def __init__(self) -> None:
        self.roles = []
        self.guild = GuildMock()

    async def remove_roles(self, *roles) -> None:
        for role in roles:
            self.roles.remove(role)

    async def add_roles(self, *roles) -> None:
        for role in roles:
            self.roles.append(role)


@pytest.mark.asyncio
async def test_change_group_role(ctrl: AssigningRolesController) -> None:
    member = MemberMock()
    await ctrl.change_group_role(PartialEmojiMock("*️⃣"), member)  # type: ignore
    assert member.roles == [RoleMock(345, "guest", "*️⃣")]
    await ctrl.change_group_role(PartialEmojiMock("1️⃣"), member)  # type: ignore
    assert member.roles == [RoleMock(123, "group_0", "1️⃣")]

    with pytest.raises(AttributeError):
        await ctrl.change_group_role(PartialEmojiMock("📣"), member)  # type: ignore


def test_embed_reaction(embed_model: AssigningRolesEmbedModel) -> None:
    assert embed_model.reactions == ["1️⃣", "*️⃣"]
