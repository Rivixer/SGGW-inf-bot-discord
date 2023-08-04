# pylint: disable-all

import nextcord

from sggwbot.utils import MemberUtils

from .mocks import *


def test_convert_member_without_unique_name_to_string():
    member = MemberMock(
        name="TestName",
        nick="TestNick",
        discriminator="1234",
        id=1234567890,
        roles=[],
    )
    result = MemberUtils.convert_to_string(member)  # type: ignore
    assert result == "TestName#1234"


def test_convert_member_with_unique_name_to_string():
    # if member has a unique name, discriminator is 0
    member = MemberMock(
        name="TestName",
        nick="TestNick",
        discriminator="0",
        id=1234567890,
        roles=[],
    )
    result = MemberUtils.convert_to_string(member)  # type: ignore
    assert result == "TestName"
