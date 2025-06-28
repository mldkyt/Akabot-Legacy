#      Akabot is a general purpose bot with a ton of features.
#      Copyright (C) 2023-2025 lunya.pet
#
#      This program is free software: you can redistribute it and/or modify
#      it under the terms of the GNU Affero General Public License as
#      published by the Free Software Foundation, either version 3 of the
#      License, or (at your option) any later version.
#
#      This program is distributed in the hope that it will be useful,
#      but WITHOUT ANY WARRANTY; without even the implied warranty of
#      MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#      GNU Affero General Public License for more details.
#
#      You should have received a copy of the GNU Affero General Public License
#      along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
import asyncio
import logging
from typing import Any

import discord
from discord import Color, Interaction
from discord.ui import View, Modal, InputText

from utils.analytics import analytics
from utils.config import get_key


async def migration_1():
    # Convert user ID's in upvotes and downvotes to strings, if they are not already
    client = get_client()

    for x in await client['SuggestionMessagesV2'].find():
        if all(isinstance(x, str) for x in x['Upvotes']) and all(isinstance(x, str) for x in x['Downvotes']):
            continue

        logging.debug('PERFORMING MIGRATION convert upvotes and downvotes to strings')

        upvotes = x['Upvotes']
        downvotes = x['Downvotes']
        await client['SuggestionMessagesV2'].update_one({'_id': x['_id']},
                                                  {'$set': {'Upvotes': [str(x) for x in upvotes],
                                                            'Downvotes': [str(x) for x in downvotes]}})



async def perform_basic_vote_checks(interaction: discord.Interaction) -> bool | tuple[bool, Any]:
    """
    Perform basic checks for voting on a suggestion. Checks for DB record and if the user has already voted.
    Args:
        interaction: Interaction

    Returns: False or True and the data when succeeded

    """
    client = get_client()

    data = await client['SuggestionMessagesV2'].find_one({'MessageID': str(interaction.message.id)})
    if not data:
        await interaction.response.send_message('This suggestion does not exist in the database', ephemeral=True)
        return False

    if str(interaction.user.id) in data['Upvotes'] or str(interaction.user.id) in data['Downvotes']:
        await interaction.response.send_message('You have already voted on this suggestion', ephemeral=True)
        return False

    return True, data


async def update_existing_suggestions_message_interaction(interaction: discord.Interaction):
    """
    Update the existing suggestions message with the new vote count
    Args:
        interaction: Interaction

    Returns: Nothing

    """
    client = get_client()

    suggestions_msg = await client['SuggestionMessagesV2'].find_one({'MessageID': str(interaction.message.id)})


    author = interaction.guild.get_member(int(suggestions_msg['AuthorID']))

    new_emb = discord.Embed(title='Suggestion', color=Color.blue(),
                            author=discord.EmbedAuthor(name=f'{author.display_name}\'s suggestion',
                                                       icon_url=author.display_avatar.url),
                            description=generate_message_content(str(interaction.message.id)))
    await interaction.response.edit_message(embed=new_emb)


async def update_existing_suggestions_message(msg: discord.Message):
    """
    Update the existing suggestions message with the new vote count
    Args:
        msg: Message object to update

    Returns: Nothing
    """
    client = get_client()

    suggestions_msg = await client['SuggestionMessagesV2'].find_one({'MessageID': str(msg.id)})


    if not suggestions_msg:
        return

    logging.info('Refreshing message %s', msg.id)

    author = msg.guild.get_member(int(suggestions_msg['AuthorID']))

    new_emb = discord.Embed(title='Suggestion', color=Color.blue(),
                            author=discord.EmbedAuthor(name=f'{author.display_name}\'s suggestion',
                                                       icon_url=author.display_avatar.url),
                            description=generate_message_content(str(msg.id)))

    await msg.edit(embed=new_emb)


class V2SuggestionView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='👍', style=discord.ButtonStyle.primary, custom_id='upvote')
    async def upvote(self, button: discord.ui.Button, interaction: discord.Interaction):
        success, data = await perform_basic_vote_checks(interaction)
        if not success:
            return

        client = get_client()

        await client['SuggestionMessagesV2'].update_one({'MessageID': str(interaction.message.id)},
                                                  {'$push': {'Upvotes': str(interaction.user.id)}})

        await update_existing_suggestions_message_interaction(interaction)

    @discord.ui.button(label='👎', style=discord.ButtonStyle.primary, custom_id='downvote')
    async def downvote(self, button: discord.ui.Button, interaction: discord.Interaction):
        success, data = await perform_basic_vote_checks(interaction)
        if not success:
            return

        client = get_client()

        await client['SuggestionMessagesV2'].update_one({'MessageID': str(interaction.message.id)},
                                                  {'$push': {'Downvotes': str(interaction.user.id)}})


        await update_existing_suggestions_message_interaction(interaction)

    @discord.ui.button(label='See more information', style=discord.ButtonStyle.primary, custom_id='more_info')
    async def get_info(self, button: discord.ui.Button, interaction: discord.Interaction):
        client = get_client()
        data = await client['SuggestionMessagesV2'].find_one({'MessageID': str(interaction.message.id)})
        if not data:
            await interaction.response.send_message('This suggestion does not exist in the database', ephemeral=True)
            return

        upvotes = data['Upvotes']
        downvotes = data['Downvotes']
        message = data['Suggestion']
        author = interaction.guild.get_member(int(data['AuthorID']))
        percent = len(upvotes) / (len(upvotes) + len(downvotes)) * 100 if len(upvotes) + len(downvotes) > 0 else 0

        upvoters = [f'<@{x}>' for x in upvotes]
        if len(upvoters) == 0:
            upvoters = ['No upvoters']
        downvoters = [f'<@{x}>' for x in downvotes]
        if len(downvoters) == 0:
            downvoters = ['No downvoters']

        await interaction.response.send_message(
            (await trl(interaction.user.id, interaction.guild.id, 'suggestions_v2_information', append_tip=True))
            .format(message=message, author=author.mention, upvotes=str(len(upvotes)), downvotes=str(len(downvotes)),
                    percent=f"{percent:.0f}",
                    upvoters=', '.join(upvoters), downvoters=', '.join(downvoters)),
            ephemeral=True, view=V2SuggestionAuthorExtraView(msg_id=data['MessageID'],
                                                             ch_id=str(interaction.channel.id)) if str(
                interaction.user.id) == data['AuthorID'] else None)


class V2SuggestionEditMessageModal(Modal):
    def __init__(self, msg_id: str, ch_id: str):
        super().__init__(timeout=300, title='Edit Message')

        self.msg_id = msg_id
        self.ch_id = ch_id

        self.add_item(InputText(label='New Message', placeholder='Enter the new message here', max_length=2000))

    async def callback(self, interaction: Interaction):
        client = get_client()

        await client['SuggestionMessagesV2'].update_one({'MessageID': self.msg_id},
                                                  {'$set': {'Suggestion': self.children[0].value}})

        ch = interaction.guild.get_channel(int(self.ch_id))
        msg = await ch.fetch_message(int(self.msg_id))

        await update_existing_suggestions_message(msg)
        await interaction.respond('Message updated', ephemeral=True)


class V2SuggestionAuthorExtraView(View):
    def __init__(self, msg_id: str, ch_id: str):
        super().__init__(timeout=120)
        self.msg_id = msg_id
        self.ch_id = ch_id

    @discord.ui.button(label='Update Message')
    async def update_message(self, button: discord.ui.Button, interaction: discord.Interaction):
        modal = V2SuggestionEditMessageModal(msg_id=self.msg_id, ch_id=self.ch_id)
        await interaction.response.send_modal(modal)


async def generate_message_content(id: str):
    client = get_client()
    data = await client['SuggestionMessagesV2'].find_one({'MessageID': id})
    if not data:
        raise ValueError('Message not found')

    upvotes = len(data['Upvotes'])
    downvotes = len(data['Downvotes'])
    message = data['Suggestion']

    percent = upvotes / (upvotes + downvotes) * 100 if upvotes + downvotes > 0 else 0

    return f"""{message}

**{upvotes + downvotes} votes**
**{percent:.0f}% approval**"""

import discord
import sentry_sdk
from discord.ext import commands

from database import get_client
from utils.languages import get_translation_for_key_localized as trl
from utils.settings import get_setting, set_setting

class Suggestions(discord.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot
        try:
            asyncio.create_task(migration_1())
        except Exception as e:
            sentry_sdk.capture_exception(e)

    @discord.Cog.listener()
    async def on_message(self, message: discord.Message):
        try:
            if message.author.bot:
                return
            if message.is_system():
                return

            client = get_client()

            if await client['SuggestionChannels'].count_documents({'ChannelID': str(message.channel.id)}) > 0:
                if message.channel.permissions_for(message.guild.me).manage_messages and get_key('Message_Intent', "false") == "true":
                    # Version 2

                    await client['SuggestionMessagesV2'].insert_one({
                        'MessageID': str(message.id),
                        'Suggestion': message.content,
                        'Upvotes': [],
                        'Downvotes': [],
                        'AuthorID': str(message.author.id)
                    })

                    effective_avatar = message.author.default_avatar.url
                    if message.author.avatar:
                        effective_avatar = message.author.avatar.url

                    emb = discord.Embed(title='Suggestion', color=Color.blue(),
                                        author=discord.EmbedAuthor(
                                            name=f'{message.author.display_name}\'s suggestion',
                                            icon_url=effective_avatar),
                                        description=generate_message_content(str(message.id)))
                    new_msg = await message.channel.send(embed=emb, view=V2SuggestionView())

                    await client['SuggestionMessagesV2'].update_one({'MessageID': str(message.id)},
                                                              {'$set': {'MessageID': str(new_msg.id)}})

                    if await get_setting(message.guild.id, "suggestions_thread_creating", "true") == "true":
                        # Name of thread is determined from the suggestion text but shortened to fit
                        thr_name = message.content[:28]
                        if thr_name != message.content:
                            thr_name = f'{thr_name}...'

                        # Create thread for the message
                        await new_msg.create_thread(name=thr_name)

                    await message.delete()
                else:
                    # Version 1
                    emojis = await get_setting(message.guild.id, 'suggestion_emoji', '👍👎')
                    if emojis == '👍👎':
                        await message.add_reaction('👍')
                        await message.add_reaction('👎')
                    elif emojis == '✅❌':
                        await message.add_reaction('✅')
                        await message.add_reaction('❌')

                    if await get_setting(message.guild.id, "suggestion_reminder_enabled", "false") == "true":
                        to_send = await get_setting(message.guild.id, "suggestion_reminder_message", "")
                        sent = await message.reply(to_send)
                        await sent.delete(delay=5)
        except Exception as e:
            sentry_sdk.capture_exception(e)

    suggestions_group = discord.SlashCommandGroup(name='suggestions', description='Suggestion commands')

    @suggestions_group.command(name='add_channel', description='Add a suggestion channel')
    @discord.default_permissions(manage_guild=True)
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def cmd_add_channel(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
        try:
            client = get_client()

            if await client['SuggestionChannels'].count_documents({'ChannelID': str(ctx.guild.id)}) == 0:
                await client['SuggestionChannels'].insert_one({'GuildID': str(ctx.guild.id), 'ChannelID': str(channel.id)})
                await ctx.respond((await trl(ctx.user.id, ctx.guild.id, 'suggestions_channel_added', append_tip=True)).format(
                    channel=channel.mention), ephemeral=True)
            else:
                await ctx.respond(await trl(ctx.user.id, ctx.guild.id, 'suggestions_channel_already_exists'), ephemeral=True)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(await trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @suggestions_group.command(name='remove_channel', description='Remove a suggestion channel')
    @discord.default_permissions(manage_guild=True)
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def cmd_remove_channel(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
        try:
            client = get_client()

            if await client['SuggestionChannels'].count_documents({'ChannelID': str(ctx.guild.id)}) == 0:
                await ctx.respond(await trl(ctx.user.id, ctx.guild.id, "suggestions_channel_not_found"), ephemeral=True)
            else:
                await client['SuggestionChannels'].delete_one({'ChannelID': str(ctx.guild.id)})
                await ctx.respond((await trl(ctx.user.id, ctx.guild.id, "suggestions_channel_removed", append_tip=True)).format(
                    channel=channel.mention), ephemeral=True)

        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(await trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @suggestions_group.command(name='set_thread_creating', description='Enable/disable creating of thread when suggesting (default: true)')
    @discord.default_permissions(manage_guild=True)
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def cmd_set_thread_creating(self, ctx: discord.ApplicationContext, thread_creating: bool):
        try:
            await set_setting(ctx.guild.id, "suggestions_thread_creating", 'true' if thread_creating else 'false')
            await ctx.respond(await trl(ctx.user.id, ctx.guild.id, "suggestions_thread_creating_enabled" if thread_creating else "suggestions_thread_creating_disabled", append_tip=True), ephemeral=True)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(await trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @suggestions_group.command(name='emoji', description='Choose emoji')
    @discord.default_permissions(manage_guild=True)
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @discord.option(name='emoji', description='The emoji to use', choices=['👎👍', '✅❌'])
    async def cmd_choose_emoji(self, ctx: discord.ApplicationContext, emoji: str):
        try:
            await set_setting(ctx.guild.id, 'suggestion_emoji', emoji)
            await ctx.respond((await trl(ctx.user.id, ctx.guild.id, "suggestions_emoji_set")).format(emoji=emoji),
                              ephemeral=True)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(await trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @suggestions_group.command(name='message_reminder', description="Message reminder for people posting suggestions")
    @discord.default_permissions(manage_guild=True)
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    async def cmd_message_reminder(self, ctx: discord.ApplicationContext, enabled: bool, message: str):
        try:
            if len(message) < 1:
                await ctx.respond("Invalid message input.", ephemeral=True)
            await set_setting(ctx.guild.id, 'suggestion_reminder_enabled', str(enabled).lower())
            await set_setting(ctx.guild.id, 'suggestion_reminder_message', message)
            await ctx.respond(
                (await trl(ctx.user.id, ctx.guild.id, 'suggestions_message_reminder_set', append_tip=True)).format(
                    enabled=enabled, message=message),
                ephemeral=True)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(await trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @suggestions_group.command(name='update_message', description='Refresh all suggestions messages in this channel')
    @commands.guild_only()
    @analytics('suggestions update_message')
    @commands.cooldown(1, 300, commands.BucketType.guild)  # Cooldown to prevent abuse
    async def cmd_update_message(self, ctx: discord.ApplicationContext):
        if get_key('Message_Intent', "false") == "false":
            await ctx.respond("This instance of Akabot doesn\'t support the message intent.", ephemeral=True)
            return

        await ctx.defer(ephemeral=True)

        tasks = []
        async for msg in ctx.history(limit=1000):
            tasks.append(update_existing_suggestions_message(msg))

        await asyncio.gather(*tasks)

        await ctx.respond(await trl(ctx.user.id, ctx.guild.id, 'suggestions_v2_refreshed', append_tip=True))
