from nextcord.guild import Guild
from nextcord.role import Role

from models.model import Model
from sggw_bot import SGGWBot


class RegistrationModel(Model):

    def __init__(self, bot: SGGWBot) -> None:
        super().__init__(bot)
        super()._load_settings()

    def get_verified_role(self, guild: Guild) -> Role | None:
        role_id = self.data.get('verified_role_id', 0)
        return guild.get_role(role_id)
