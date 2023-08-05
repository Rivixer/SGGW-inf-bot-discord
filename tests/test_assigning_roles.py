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

from .mocks import *

TEST_JSON_PATH = Path("test_assigning_roles.json")


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
    return AssigningRolesEmbedModel(model, BotMock(GuildMock()))  # type: ignore


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


@pytest.mark.asyncio
async def test_change_group_role(ctrl: AssigningRolesController) -> None:
    group_0_role = RoleMock("group_0", 123, 0x111111)
    guest_role = RoleMock("guest", 345, 0x222222)

    group_0_partial_emoji = PartialEmojiMock("1️⃣")
    guest_partial_emoji = PartialEmojiMock("*️⃣")
    invalid_partial_emoji = PartialEmojiMock("📣")

    guild = GuildMock()
    guild.roles = [group_0_role, guest_role]

    member = MemberMock(
        name="TestName",
        nick="TestNick",
        discriminator="1234",
        id=1234567890,
        roles=[group_0_role],
        _guild=guild,
    )

    # Change group_0 to guest
    await ctrl.change_group_role(guest_partial_emoji, member)  # type: ignore
    assert member.roles == [guest_role]

    # Change guest to group_0
    await ctrl.change_group_role(group_0_partial_emoji, member)  # type: ignore
    assert member.roles == [group_0_role]

    # Try to change group_0 using invalid emoji
    with pytest.raises(AttributeError):
        await ctrl.change_group_role(invalid_partial_emoji, member)  # type: ignore


def test_embed_reaction(embed_model: AssigningRolesEmbedModel) -> None:
    assert embed_model.reactions == ["1️⃣", "*️⃣"]
