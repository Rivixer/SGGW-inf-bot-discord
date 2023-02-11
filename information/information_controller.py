from models.embed_controller import EmbedController
from models.controller import Controller
from sggw_bot import SGGWBot

from .information_model import InformationModel
from .information_embed import InformationEmbed


class InformationController(Controller, EmbedController):

    _model: InformationModel
    _embed_model: InformationEmbed

    def __init__(self, bot: SGGWBot) -> None:
        model = InformationModel(bot)
        embed_model = InformationEmbed(model)

        Controller.__init__(self, model)
        EmbedController.__init__(self, embed_model)
