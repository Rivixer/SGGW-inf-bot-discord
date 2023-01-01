from models.model import Model

from sggw_bot import SGGWBot


class InformationsModel(Model):

    def __init__(self, bot: SGGWBot) -> None:
        super().__init__(bot)
        super()._load_settings()
