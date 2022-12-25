import asyncio

from nextcord.interactions import Interaction
from nextcord.member import Member
from nextcord.role import Role

from models.embed_controller import EmbedController
from models.controller import Controller

from .assign_role_model import AssignRoleModel
from .assign_role_embed import AssignRoleEmbed


class AssignRoleController(Controller, EmbedController):

    _model: AssignRoleModel
    _embed_model: AssignRoleEmbed

    def __init__(self) -> None:
        model = AssignRoleModel()
        embed_model = AssignRoleEmbed(model)

        Controller.__init__(self, model)
        EmbedController.__init__(self, embed_model)

    async def change_group_role(self, emoji: str, member: Member) -> None:
        """|coro|

        Assign role to user.

        Remove other roles from user.

        Role will be get from number emoji.

        Raises
        ------
        AttributeError
            Role that has been added not exists.
        """

        role_to_add: Role | None = None
        roles_to_remove: list[Role] = []

        for group in self._model.roles:
            role = member.guild.get_role(group.id)

            if role is None:
                continue

            if group.emoji == emoji:
                role_to_add = role
            elif role in member.roles:
                roles_to_remove.append(role)

        if role_to_add is None:
            raise AttributeError(f'Role with \'{emoji}\' not exists.')

        await asyncio.gather(
            member.remove_roles(*roles_to_remove),
            member.add_roles(role_to_add)
        )

    @EmbedController._with_update('*Zmienianie maksymalnej ilości grup na {amount}...*')
    async def update_max_groups(self, interaction: Interaction, *, amount: int) -> None:
        """Updates max_groups in _model and in settings.json

        Raises
        ------
        OsError
            Cannot open settings file.
        """

        self._model.max_groups = amount
        self._model.update_json('max_groups', amount)
