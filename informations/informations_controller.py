from models.embed_controller import EmbedController
from models.controller import Controller
from sggw_bot import SGGWBot

from .informations_model import InformationsModel
from .informations_embed import InformationsEmbed


class InformationsController(Controller, EmbedController):

    _model: InformationsModel
    _embed_model: InformationsEmbed

    def __init__(self, bot: SGGWBot) -> None:
        model = InformationsModel(bot)
        embed_model = InformationsEmbed(model)

        Controller.__init__(self, model)
        EmbedController.__init__(self, embed_model)
