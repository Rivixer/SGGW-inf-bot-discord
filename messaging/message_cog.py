from typing import Any, Optional
import json
import os

from nextcord.application_command import SlashOption
from nextcord.message import Message, Attachment
from nextcord.interactions import Interaction
from nextcord.channel import TextChannel
from nextcord.ext import commands
from nextcord.file import File
import nextcord

from utils.commands import SlashCommandUtils
from utils.attachment import AttachmentUtils
from sggw_bot import SGGWBot

from .embed_utils import EmbedUtils


class MessageCog(commands.Cog):

    __slots__ = (
        '__bot',
    )

    __bot: SGGWBot

    def __init__(self, bot: SGGWBot) -> None:
        self.__bot = bot

    @staticmethod
    async def __get_message(
        interaction: Interaction,
        message_id: str | int
    ) -> Message:
        if isinstance(message_id, str) and not message_id.isdigit():
            raise TypeError(
                'All chars in reply_to_msg_id must be numbers'
            )

        channel = interaction.channel
        return await channel.fetch_message(int(message_id))  # type: ignore

    @nextcord.slash_command(
        name='message',
        description="Manage messages.",
        dm_permission=False,
        default_member_permissions=1 << 17  # Mention everyone
    )
    async def _message(self, *_) -> None:
        pass

    @_message.subcommand(name='send', description="Send a message.")
    @SlashCommandUtils.log(show_channel=True)
    async def _send(
        self,
        interaction: Interaction,
        text: str = SlashOption(
            name='content',
            description='Message content',
            required=False,
            default='',
        ),
        reply_to_msg_id: Optional[str] = SlashOption(
            description='ID of the message to be replied to',
            required=False,
            default=None,
        ),
        file_embed: Attachment = SlashOption(
            name='embed',
            description='Attach embed',
            default=None,
            required=False,
        ),
        attachment: Attachment = SlashOption(
            name='file',
            description='Attach file',
            default=None,
            required=False,
        ),
        preview: bool = SlashOption(
            description='If it is true, only you will see the message',
            default=None,
            required=False,
        ),
    ) -> ...:
        message_kwargs: dict[str, Any] = {
            'content': text.replace('\\n', '\n').replace('\\t', '\t')
        }

        try:
            if reply_to_msg_id is not None and preview:
                raise ValueError(
                    'reply_to_msg_id cannot be provided if preview is True'
                )

            channel = interaction.channel
            if not isinstance(channel, TextChannel):
                raise TypeError('Channel must be TextChannel')

            if reply_to_msg_id is not None:
                reply_to = await self.__get_message(interaction, reply_to_msg_id)
            else:
                reply_to = None

            if file_embed is not None:
                embed = await EmbedUtils.convert_attachment_to_embed(file_embed)
                message_kwargs['embed'] = embed

            if attachment is not None:
                attachment_utils = AttachmentUtils(attachment)
                path = await attachment_utils.save_temporarily()
                message_kwargs['file'] = File(path, attachment.filename)

            if preview:
                return await interaction.response.send_message(
                    **message_kwargs, ephemeral=preview
                )

            if reply_to is not None:
                await reply_to.reply(**message_kwargs)
            else:
                await channel.send(**message_kwargs)

            await interaction.response.send_message(
                f'Pomyślnie wysłano wiadomość',
                ephemeral=True
            )

        except Exception as e:
            await interaction.response.send_message(
                f'**[BŁĄD]** {e}',
                ephemeral=True
            )
        finally:
            if 'attachment_utils' in locals():
                del message_kwargs['file']
                attachment_utils.delete()  # type: ignore

    @_message.subcommand(name='edit', description="Edit a message.")
    @SlashCommandUtils.log(show_channel=True)
    async def _edit(
        self,
        interaction: Interaction,
        message_id: str = SlashOption(
            description='ID of the message to be edited',
        ),
        text: Optional[str] = SlashOption(
            name='content',
            description='Edit message content',
            default=None,
            required=False,
        ),
        file_embed: Attachment = SlashOption(
            name='embed',
            description='Edit embed',
            default=None,
            required=False,
        ),
        attachment: Attachment = SlashOption(
            name='file',
            description='Edit file',
            default=None,
            required=False,
        ),
    ) -> None:
        message_kwargs: dict[str, Any] = {}

        try:
            channel = interaction.channel
            if not isinstance(channel, TextChannel):
                raise TypeError('Channel must be TextChannel')

            message = await self.__get_message(interaction, message_id)

            if text is not None:
                message_kwargs['content'] = text

            if file_embed is not None:
                embed = await EmbedUtils.convert_attachment_to_embed(file_embed)
                message_kwargs['embed'] = embed

            if attachment is not None:
                attachment_utils = AttachmentUtils(attachment)
                path = await attachment_utils.save_temporarily()
                message_kwargs['file'] = File(path, attachment.filename)

            await message.edit(**message_kwargs)
            await interaction.response.send_message(
                f'Pomyślnie edytowano: {", ".join(message_kwargs.keys())}',
                ephemeral=True
            )

        except Exception as e:
            await interaction.response.send_message(
                f'**[BŁĄD]** {e}',
                ephemeral=True
            )
        finally:
            if 'attachment_utils' in locals():
                del message_kwargs['file']
                attachment_utils.delete()  # type: ignore

    @_message.subcommand(name='remove', description="Remove something from message")
    @SlashCommandUtils.log(show_channel=True)
    async def _remove(
        self,
        interaction: Interaction,
        message_id: str = SlashOption(
            description='ID of the message',
        ),
        text: bool = SlashOption(
            name='content',
            description='Remove the message content',
            default=False,
            required=False,
        ),
        file_embed: bool = SlashOption(
            name='embed',
            description='Remove the enclosed embed',
            default=False,
            required=False,
        ),
        attachment: bool = SlashOption(
            name='file',
            description='Remove the enclosed file',
            default=False,
            required=False,
        ),
    ) -> None:
        try:
            channel = interaction.channel
            if not isinstance(channel, TextChannel):
                raise TypeError('Channel must be TextChannel')

            message = await self.__get_message(interaction, message_id)

            message_kwargs: dict[str, Any] = {}

            if text:
                message_kwargs['content'] = None

            if file_embed:
                message_kwargs['embed'] = None

            if attachment:
                message_kwargs['file'] = None

            await message.edit(**message_kwargs)
            await interaction.response.send_message(
                f'Pomyślnie usunięto: {", ".join(message_kwargs.keys())}',
                ephemeral=True
            )

        except Exception as e:
            await interaction.response.send_message(
                f'**[BŁĄD]** {e}',
                ephemeral=True
            )

    @_message.subcommand(
        name='add_reaction',
        description='Add a reaction to the message. '
        'If a reaction is added, remove it.'
    )
    @SlashCommandUtils.log(show_channel=True)
    async def _add_reaction(
        self,
        interaction: Interaction,
        message_id: str = SlashOption(
            description='ID of the message',
            required=True,
        ),
        emoji: str = SlashOption(
            description='Emoji (emoji or its ID) to be added to the message',
            required=True,
        ),
    ) -> ...:
        try:
            guild: nextcord.Guild = interaction.guild  # type: ignore
            if emoji.isdigit():
                _emoji = await guild.fetch_emoji(int(emoji))
            else:
                _emoji = emoji

            channel = interaction.channel
            if not isinstance(channel, TextChannel):
                raise TypeError('Channel must be TextChannel')

            message = await self.__get_message(interaction, message_id)

            for reaction in message.reactions:
                if reaction.emoji != _emoji:
                    continue
                async for user in reaction.users():
                    if user == self.__bot.user:
                        await message.remove_reaction(_emoji, user)
                        return await interaction.response.send_message(
                            f'Pomyślnie usunięto z wiadomości reakcję: {_emoji}',
                            ephemeral=True
                        )

            await message.add_reaction(_emoji)
            await interaction.response.send_message(
                f'Pomyślnie dodano do wiadomości reakcję: {_emoji}',
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f'**[BŁĄD]** {e}',
                ephemeral=True
            )

    @_message.subcommand(name='get_embed', description='Get an embed from the message.')
    @SlashCommandUtils.log(show_channel=True)
    async def _get_embed(
        self,
        interaction: Interaction,
        message_id: str = SlashOption(
            description='ID of the message with embed',
            required=False,
            default=None,
        ),
    ) -> None:
        try:
            if not message_id.isdigit():
                raise TypeError(
                    'All chars in message_id must be numbers'
                )

            message = await self.__get_message(interaction, message_id)
            embed = EmbedUtils.get_embed_from_message(message)

            if embed is None:
                raise KeyError('Message does not contain an embed')

            with open('temp_embed.json', 'w', encoding='utf-8') as f:
                json.dump(embed.to_dict(), f, ensure_ascii=True, indent=4)

            file = File('temp_embed.json')

            await interaction.response.send_message(
                f'Oto embed z wiadomości.',
                file=file,
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f'**[BŁĄD]** {e}',
                ephemeral=True
            )
        finally:
            try:
                os.remove('temp_embed.json')
            except:
                pass

    @_message.subcommand(name='embed_prototype', description="Get prototype of embed in json.")
    @SlashCommandUtils.log()
    async def _prototype(self, interaction: Interaction) -> None:
        try:
            file = EmbedUtils.embed_prototype()
            await interaction.response.send_message(
                file=file, ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f'**[BŁĄD]** {e}',
                ephemeral=True
            )


def setup(bot: SGGWBot):
    bot.add_cog(MessageCog(bot))
