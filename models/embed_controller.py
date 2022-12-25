from __future__ import annotations

from typing import Callable, Coroutine, Any
from abc import ABC
import asyncio

from nextcord.interactions import Interaction
from nextcord.channel import TextChannel
from nextcord.message import Message
from nextcord.guild import Guild

from utils.console import Console

from .controller import Controller
from .embed_model import EmbedModel
from .model import Model


class EmbedController(ABC):

    _embed_model: EmbedModel
    _model: Model

    def __init__(self, embed_model: EmbedModel) -> None:
        if not isinstance(self, Controller):
            raise TypeError(
                f'{self.__class__.__name__} must also inherit from `models.controller`.'
            )

        if not '_model' in dir(self) or getattr(self, '_model', None) is None:
            raise AttributeError(
                f'{self.__class__.__name__} must have \'_model\' variable '
                'initialized in `Controller.__init__`.'
            )

        self._embed_model = embed_model

    @property
    def message_id(self) -> int | None:
        return self._model.data.get('message', {}).get('id')

    async def send(self, interaction: Interaction) -> None:
        """|coro|

        Replies to a message that a new message is being generated.

        If the message is created properly, the reply will be deleted.

        Otherwise, the content of the response will be changed to the content of the exception.
        The full text of the exception will be printed on the console.
        If part of the message has been sent, it will be deleted.
        """

        reply = await interaction.response.send_message(
            '*Generowanie wiadomości...*',
            ephemeral=True
        )

        async def delete_msg():
            try:
                await msg.delete()
            except NameError:
                pass

        try:
            msg = await self.__send_msg(interaction.channel)  # type: ignore
            await self.__add_reactions(msg)
            self.__update_data(msg)
        except KeyboardInterrupt:
            pass
        except Exception as e:
            Console.error('Error in `/roles send` command.', exception=e)
            await asyncio.gather(*(delete_msg(),  reply.edit(f'**[BŁĄD]** {e}')))
        else:
            await reply.delete()

    @staticmethod
    def _with_update(reply_content: str, *, reload_settings: bool = False):
        """A decorator that first replies to the interaction that the function will be executed.

        Next executes the function.

        If an error occured, catches it, prints its content to the console
        and changes content of the reply message to the content of the excpetion.

        Otherwise, updates the message.

        The function where the decorator is used must be a corountine,
        must be in a class inherited from EmbedController,
        the first argument (after self) must be Interaction
        and other arguments must be keywords.

        reply_content will be formatted using str.format(**kwargs).

        Parameters
        ----------
        reply_content: `str`
            The content of the interaction response during the update.
        reload_settings: `bool`
            If True, reload the settings in the model before executing the function.
        """

        def decorator(func: Callable[..., Coroutine[Any, Any, None]]):
            async def wrapper(self: EmbedController, interaction: Interaction, *args, **kwargs):
                reply = await interaction.response.send_message(
                    reply_content.format(**kwargs), ephemeral=True
                )

                try:
                    if reload_settings:
                        self._model.reload_from_settings()
                    await func(self, interaction, *args, **kwargs)
                    embed = self._embed_model.generate_embed()
                    guild = interaction.guild
                    msg = await self.__get_message(guild)  # type: ignore
                    await asyncio.gather(*(
                        msg.edit(embed=embed),
                        msg.clear_reactions()
                    ))
                    await self.__add_reactions(msg)
                except KeyboardInterrupt:
                    pass
                except Exception as e:
                    Console.error(f'Error in {func.__name__}.', exception=e)
                    await reply.edit(f'**[BŁĄD]** {e}')
                else:
                    await reply.delete()

            return wrapper
        return decorator

    @_with_update('Aktualizowanie embed...', reload_settings=True)
    async def update(self, interaction: Interaction) -> None:
        pass

    async def __send_msg(self, channel: TextChannel) -> Message:
        """|coro|

        Sends an embed from `embed_model.generate_embed()`.

        Raises
        ------
        nextcord.errors.*
            Discord API cannot send the message.
        """

        embed = self._embed_model.generate_embed()
        return await channel.send(embed=embed)

    async def __add_reactions(self, msg: Message) -> None:
        """|coro|

        Adds reactions to the message from `_embed_model`.

        Raises
        ------
        nextcord.errors.*
            Discord API has a problem.
        """

        await asyncio.gather(
            *(msg.add_reaction(r) for r in self._embed_model.reactions)
        )

    def __update_data(self, msg: Message) -> None:
        """Updates message data in settings.json

        If file not exists, creates it with 'message' key.
        """

        msg_data = {
            'id': msg.id,
            'channel_id': msg.channel.id,
            'guild_id': (msg.guild.id if msg.guild else 0)
        }

        self._model.update_json('message', msg_data, force=True)

    async def __get_message(self, guild: Guild) -> Message:
        """|coro|

        Returns a message fetched using settings.json data.

        Raises
        ------
        TypeError
            Found channel must be TextChannel.
        nextcord.errors.*
            Message not found.
        """

        data: dict[str, int] = self._model.data.get('message', {})
        channel_id = data.get('channel_id', -1)
        msg_id = data.get('id', -1)

        channel = guild.get_channel(channel_id)

        if not isinstance(channel, TextChannel):
            raise TypeError('Channel is not a TextChannel')

        return await channel.fetch_message(msg_id)
