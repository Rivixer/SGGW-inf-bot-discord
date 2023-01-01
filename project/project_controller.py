from models.embed_controller import EmbedController
from models.controller import Controller
from sggw_bot import SGGWBot

from .project_model import ProjectModel
from .project_embed import ProjectEmbed


class ProjectController(Controller, EmbedController):

    _model: ProjectModel
    _embed_model: ProjectEmbed

    def __init__(self, bot: SGGWBot) -> None:
        model = ProjectModel(bot)
        embed_model = ProjectEmbed(model)

        Controller.__init__(self, model)
        EmbedController.__init__(self, embed_model)
