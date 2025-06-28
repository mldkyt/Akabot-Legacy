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
import datetime
import logging

import discord
import sentry_sdk
from discord import Cog, Bot, TextChannel, Interaction, Embed, EmbedAuthor, SlashCommandGroup, \
    ApplicationContext, Message, ButtonStyle
from discord.ext.commands import has_guild_permissions, guild_only
from discord.ui import Modal, InputText, View, button, Button
from sentry_sdk import capture_exception

from database import get_client
from utils.config import get_key
from utils.languages import get_translation_for_key_localized as trl
from utils.logging_util import log_into_logs
from utils.settings import get_setting, set_setting


class CreateModal(Modal):
    def __init__(self, channel: TextChannel, modal_text_label: str, modal_title: str):
        super().__init__(
            InputText(label=modal_text_label,
                      placeholder=modal_text_label, min_length=1,
                      max_length=1000, required=True),
            title=modal_title
        )

        self.channel = channel

    async def callback(self, interaction: Interaction):
        try:
            text = self.children[0].value

            msg = await self.channel.send(
                embed=Embed(
                    title=await trl(0, self.channel.guild.id, 'quefessions_embed_title'),
                    description=text,
                    author=EmbedAuthor(
                        name=interaction.user.display_name,
                        icon_url=interaction.user.display_avatar.url
                    ),
                    timestamp=datetime.datetime.now(datetime.timezone.utc)
                ),
                view=InfoButtonView(interaction.guild.id, interaction.channel.id)
            )

            client = get_client()

            await client['AnonymousQuefessions'].insert_one({
                'GuildID': str(interaction.guild.id),
                'ChannelID': str(interaction.channel.id),
                'MessageID': str(msg.id),
                'AuthorID': str(interaction.user.id),
                'Text': text
            })

            await interaction.respond(
                await trl(interaction.user.id, interaction.guild.id, 'quefessions_created', append_tip=True), ephemeral=True)
        except Exception as e:
            capture_exception(e)
            await interaction.respond(await trl(interaction.user.id, interaction.guild.id, 'command_error_generic'),
                                      ephemeral=True)


class ReportTextModal(Modal):
    def __init__(self, author: tuple[str, str, str], message: Message, original_content: str, report_label: str, report_placeholder: str, report_title: str):
        super().__init__(
            InputText(label=report_label,
                      placeholder=report_placeholder),
            title=report_title.format(user=author[0]))

        self.author = author
        self.mod_message = message
        self.original_content = original_content

    async def callback(self, interaction: Interaction):
        try:
            client = get_client()

            await client['AnonymousQuefessionsReports'].insert_one({
                'GuildID': str(interaction.guild.id),
                'ChannelID': str(interaction.channel.id),
                'MessageID': str(self.mod_message.id),
                'ReporterID': str(interaction.user.id)
            })

            log_embed = Embed(
                title=await trl(0, interaction.guild.id, 'quefessions_log_report_title'),
                description=(await trl(0, interaction.guild.id, 'quefessions_log_report_description')).format(
                    jump_url=self.mod_message.jump_url, author=self.author[0], author_username=self.author[1],
                    author_id=self.author[2], reporter=interaction.user.display_name,
                    reporter_username=interaction.user.name, reporter_id=interaction.user.id,
                    original_content=self.original_content),
            )

            await log_into_logs(interaction.guild, log_embed, view=LogsView(self.mod_message))
            await interaction.respond(
                trl(interaction.user.id, interaction.guild.id, 'quefessions_report_sent', append_tip=True),
                ephemeral=True)
        except Exception as e:
            capture_exception(e)
            await interaction.respond(await trl(interaction.user.id, interaction.guild.id, 'command_error_generic'),
                                      ephemeral=True)

class ReplyModal(discord.ui.Modal):
    def __init__(self, message: discord.Message, reply_title: str, reply_label: str, reply_placeholder: str):
        super().__init__(title=reply_title)

        self.message_field = InputText(label=reply_label,
                      placeholder=reply_placeholder, min_length=1, max_length=1000)
        self.add_item(self.message_field)

        self.message = message

    async def callback(self, interaction: Interaction):
        try:
            if isinstance(self.message.channel, discord.Thread):
                data = await self.message.reply(
                    embed=discord.Embed(
                        title="Anonymous Quefession Reply",
                        description=self.message_field.value
                    ),
                    view=InfoButtonView(self.message.guild.id, self.message.channel.id)
                )
            else:
                thread = self.message.thread or (await self.message.create_thread(name="Quefession Replies"))

                data = await thread.send(
                    embed=discord.Embed(
                        title="Anonymous Quefession Reply",
                        description=self.message_field.value
                    ),
                    view=InfoButtonView(self.message.guild.id, self.message.channel.id)
                )

            client = get_client()

            await client['AnonymousQuefessions'].insert_one({
                'GuildID': str(data.guild.id),
                'ChannelID': str(data.channel.id),
                'MessageID': str(data.id),
                'AuthorID': str(data.author.id)
            })

            await interaction.respond("Reply sent!", ephemeral=True)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await interaction.respond(await trl(self.message.author.id, self.message.guild.id, "command_error_generic"), ephemeral=True)

class CreateButtonView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @button(label='Submit Anonymous Quefession', custom_id='anonymous_quefession')
    async def create_anonymous_quefession(self, button: Button, interaction: Interaction):
        try:
            client = get_client()

            # Let's check bans
            del_result = await client['AnonymousQuefessionsBans'].delete_many({
                '$and': [
                    {'BanEnd': {'$exists': True}},
                    {'BanEnd': {'$lt': datetime.datetime.now()}}
                ]
            })

            logging.debug(str(del_result))

            ban = await client['AnonymousQuefessionsBans'].find_one({
                'MemberID': str(interaction.user.id)
            })

            logging.debug(str(ban))

            if ban is not None:
                await interaction.respond(await trl(interaction.user.id, interaction.guild.id, 'quefessions_banned'),
                                          ephemeral=True)
                return

            await interaction.response.send_modal(
                CreateModal(interaction.channel,
                            modal_text_label=await trl(0, interaction.guild.id, 'quefessions_submit_modal_text_label'),
                            modal_title=await trl(0, interaction.guild.id, 'quefessions_submit_modal_title')))
        except Exception as e:
            capture_exception(e)
            await interaction.respond(await trl(interaction.user.id, interaction.guild.id, 'command_error_generic'),
                                      ephemeral=True)


class AdminView(View):
    def __init__(self, message: Message):
        super().__init__()
        self.mod_message = message

    @button(label='Delete', style=ButtonStyle.danger)
    async def delete_quefession(self, button: Button, interaction: Interaction):
        await self.mod_message.delete()
        self.disable_all_items()
        await interaction.edit(view=self)
        self.stop()

    @button(label='Quefession Ban...', style=ButtonStyle.danger)
    async def quefession_ban(self, button: Button, interaction: Interaction):
        await interaction.edit(view=AdminBanSelectTypeView(self.mod_message))
        pass


class AdminBanSelectTypeView(View):
    def __init__(self, message: Message):
        super().__init__()
        self.mod_message = message

    @button(label='Quefession Ban...', style=ButtonStyle.danger)
    async def quefession_ban(self, button: Button, interaction: Interaction):
        try:
            await interaction.edit(view=AdminQuefessionBanDurationChoice(self.mod_message))
        except Exception as e:
            capture_exception(e)
            await interaction.respond(await trl(interaction.user.id, interaction.guild.id, 'command_error_generic'),
                                      ephemeral=True)

    @button(label='Server Ban', style=ButtonStyle.danger)
    async def server_ban(self, button: Button, interaction: Interaction):
        try:
            await interaction.edit(view=AdminBanSelectTypeView(self.mod_message))
        except Exception as e:
            capture_exception(e)
            await interaction.respond(await trl(interaction.user.id, interaction.guild.id, 'command_error_generic'),
                                      ephemeral=True)


class AdminGuildBanConfirm(View):
    def __init__(self, message: Message):
        super().__init__()
        self.mod_message = message

    @button(label='Confirm Guild Ban', style=ButtonStyle.danger)
    async def confirm_guild_ban(self, button: Button, interaction: Interaction):
        try:
            client = get_client()

            data = await client['AnonymousQuefessions'].find_one(
                {'GuildID': str(interaction.guild.id), 'ChannelID': str(interaction.channel.id),
                 'MessageID': str(self.mod_message.id)})

            if data is None:
                await interaction.respond(await trl(interaction.user.id, interaction.guild.id, 'quefessions_not_found'),
                                          ephemeral=True)
                return

            member = interaction.guild.get_member(int(data['MemberID']))

            await member.ban(reason=await trl(0, interaction.guild.id, 'quefessions_ban_reason'), delete_message_seconds=604800)

            self.stop()
            self.disable_all_items()
            await interaction.edit(view=self)
        except Exception as e:
            capture_exception(e)
            await interaction.respond(await trl(interaction.user.id, interaction.guild.id, 'command_error_generic'),
                                      ephemeral=True)

    @button(label='Cancel Guild Ban', style=ButtonStyle.secondary)
    async def cancel_guild_ban(self, button: Button, interaction: Interaction):
        try:
            await interaction.edit(view=AdminView(message=self.mod_message))
        except Exception as e:
            capture_exception(e)
            await interaction.respond(await trl(interaction.user.id, interaction.guild.id, 'command_error_generic'),
                                      ephemeral=True)


class AdminQuefessionBanDurationChoice(View):
    def __init__(self, message: Message):
        super().__init__()
        self.mod_message = message

    async def fetch_author(self):
        client = get_client()
        data = await client['AnonymousQuefessions'].find_one({
            'GuildID': str(self.mod_message.guild.id),
            'ChannelID': str(self.mod_message.channel.id),
            'MessageID': str(self.mod_message.id)
        })

        if data is None:
            return None

        return data['AuthorID']

    async def ban_temp(self, minutes: int):
        author = await self.fetch_author()
        if author is None:
            return

        client = get_client()
        await client['AnonymousQuefessionsBans'].insert_one({
            'MemberID': author,
            'BanEnd': datetime.datetime.now() + datetime.timedelta(minutes=minutes)
        })

    async def ban_perm(self):
        author = await self.fetch_author()
        if author is None:
            return

        client = get_client()
        await client['AnonymousQuefessionsBans'].insert_one({
            'MemberID': author,
            'Permanent': True
        })

    @button(label='10 minutes', style=ButtonStyle.danger)
    async def ban_10_minutes(self, button: Button, interaction: Interaction):
        try:
            await self.ban_temp(10)
            self.stop()
            self.disable_all_items()
            await interaction.edit(view=self)
            await interaction.respond(await trl(interaction.user.id, interaction.guild.id, 'quefessions_ban_10_minutes'),
                                      ephemeral=True)
        except Exception as e:
            capture_exception(e)
            await interaction.respond(await trl(interaction.guild.id, interaction.user.id, 'command_error_generic'),
                                      ephemeral=True)

    @button(label='1 hour', style=ButtonStyle.danger)
    async def ban_1_hour(self, button: Button, interaction: Interaction):
        try:
            await self.ban_temp(60)
            self.stop()
            self.disable_all_items()
            await interaction.edit(view=self)
            await interaction.respond(await trl(interaction.user.id, interaction.guild.id, 'quefessions_ban_1_hour'),
                                      ephemeral=True)
        except Exception as e:
            capture_exception(e)
            await interaction.respond(await trl(interaction.guild.id, interaction.user.id, 'command_error_generic'),
                                      ephemeral=True)

    @button(label='12 hour', style=ButtonStyle.danger)
    async def ban_12_hours(self, button: Button, interaction: Interaction):
        try:
            await self.ban_temp(720)
            self.stop()
            self.disable_all_items()
            await interaction.edit(view=self)
            await interaction.respond(await trl(interaction.user.id, interaction.guild.id, 'quefessions_ban_12_hours'),
                                      ephemeral=True)
        except Exception as e:
            capture_exception(e)
            await interaction.respond(await trl(interaction.guild.id, interaction.user.id, 'command_error_generic'),
                                      ephemeral=True)

    @button(label='1 day', style=ButtonStyle.danger)
    async def ban_1_day(self, button: Button, interaction: Interaction):
        try:
            await self.ban_temp(1440)
            self.stop()
            self.disable_all_items()
            await interaction.edit(view=self)
            await interaction.respond(await trl(interaction.user.id, interaction.guild.id, 'quefessions_ban_1_day'),
                                      ephemeral=True)
        except Exception as e:
            capture_exception(e)
            await interaction.respond(await trl(interaction.guild.id, interaction.user.id, 'command_error_generic'),
                                      ephemeral=True)

    @button(label='1 week', style=ButtonStyle.danger)
    async def ban_1_week(self, button: Button, interaction: Interaction):
        try:
            await self.ban_temp(10080)
            self.stop()
            self.disable_all_items()
            await interaction.edit(view=self)
            await interaction.respond(await trl(interaction.user.id, interaction.guild.id, 'quefessions_ban_1_week'),
                                      ephemeral=True)
        except Exception as e:
            capture_exception(e)
            await interaction.respond(await trl(interaction.guild.id, interaction.user.id, 'command_error_generic'),
                                      ephemeral=True)

    @button(label='1 month', style=ButtonStyle.danger)
    async def ban_1_month(self, button: Button, interaction: Interaction):
        try:
            await self.ban_temp(40320)
            self.stop()
            self.disable_all_items()
            await interaction.edit(view=self)
            await interaction.respond(await trl(interaction.user.id, interaction.guild.id, 'quefessions_ban_1_month'),
                                      ephemeral=True)
        except Exception as e:
            capture_exception(e)
            await interaction.respond(await trl(interaction.guild.id, interaction.user.id, 'command_error_generic'),
                                      ephemeral=True)

    @button(label='Permanent', style=ButtonStyle.danger)
    async def ban_permanent(self, button: Button, interaction: Interaction):
        try:
            await self.ban_perm()
            self.stop()
            self.disable_all_items()
            await interaction.edit(view=self)
            await interaction.respond(await trl(interaction.user.id, interaction.guild.id, 'quefessions_ban_permanent'),
                                      ephemeral=True)
        except Exception as e:
            capture_exception(e)
            await interaction.respond(await trl(interaction.guild.id, interaction.user.id, 'command_error_generic'),
                                      ephemeral=True)


class InfoButtonView(View):
    def __init__(self, guild_id: int, channel_id: int):
        super().__init__(timeout=None)

        asyncio.create_task(self.second_init(guild_id, channel_id))

    async def second_init(self, guild_id: int, channel_id: int):

        if guild_id == 0 or channel_id == 0 or await get_setting(guild_id, f"quefessions_replies_{channel_id}", False):
            btn = discord.ui.Button(label="Reply Anonymously", custom_id="anonymous_reply")
            btn.callback = self.reply_anonymously
            self.add_item(
                btn
            )

        btn_admin = discord.ui.Button(label='Admin View', custom_id='quefession_admin_view')
        btn_admin.callback = self.admin_view
        self.add_item(btn_admin)

        btn_report = discord.ui.Button(label='Report Quefession...', custom_id='quefession_report_view')
        btn_report.callback = self.report_quefession
        self.add_item(btn_report)


    async def reply_anonymously(self, interaction: discord.Interaction):
        try:
            reply_modal = ReplyModal(interaction.message,
                                     reply_title=await trl(interaction.user.id, interaction.guild.id, "quefessions_reply_title"),
                                     reply_label=await trl(interaction.user.id, interaction.guild.id, "quefessions_reply_label"),
                                     reply_placeholder=await trl(interaction.user.id, interaction.guild.id, "quefessions_reply_placeholder"))
            await interaction.response.send_modal(reply_modal)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await interaction.respond("An error occured")

    async def admin_view(self, button: Button, interaction: Interaction):
        if not interaction.user.guild_permissions.manage_channels and not interaction.user.guild_permissions.manage_guild and \
                not interaction.user.guild_permissions.administrator:
            await interaction.respond(await trl(interaction.user.id, interaction.guild.id, 'no_permission'), ephemeral=True)
            return

        client = get_client()
        data = await client['AnonymousQuefessions'].find_one(
            {'GuildID': str(interaction.guild.id), 'ChannelID': str(interaction.channel.id),
             'MessageID': str(interaction.message.id)})

        if data is None:
            await interaction.respond(await trl(interaction.user.id, interaction.guild.id, 'quefessions_not_found'),
                                      ephemeral=True)
            return

        author = interaction.guild.get_member(int(data['AuthorID']))
        if author is None:
            author = ('Unknown', 'Unknown', 'Unknown')
        else:
            author = (author.display_name, author.name, author.id)

        fmt = (f"# Anonymous Quefession by {author[0]}\n\n"
               f"**Created by**: {author[0]} ({author[1]}; {author[2]})\n")

        message = await interaction.guild.get_channel(int(data['ChannelID'])).fetch_message(int(data['MessageID']))
        logging.info(message)
        if message is None:
            await interaction.respond(await trl(interaction.user.id, interaction.guild.id, 'quefessions_not_found'),
                                      ephemeral=True)
            return

        await interaction.respond(fmt, ephemeral=True, view=AdminView(message=message))

    async def report_quefession(self, button: Button, interaction: Interaction):
        try:
            client = get_client()
            data = await client['AnonymousQuefessions'].find_one(
                {'GuildID': str(interaction.guild.id), 'ChannelID': str(interaction.channel.id),
                 'MessageID': str(interaction.message.id)})

            if data is None:
                await interaction.respond(await trl(interaction.user.id, interaction.guild.id, 'quefessions_not_found'),
                                          ephemeral=True)
                return

            author = interaction.guild.get_member(int(data['AuthorID']))
            if author is None:
                author = ('Unknown', 'Unknown', 'Unknown')
            else:
                author = (author.display_name, author.name, author.id)

            if get_key("Message_Intent", "false") == "true":
                channel = interaction.guild.get_channel(int(data['ChannelID']))
                if channel is None:
                    await interaction.respond(await trl(interaction.user.id, interaction.guild.id, 'quefessions_not_found'), ephemeral=True)
                    return

                message = await channel.fetch_message(int(data['MessageID']))
                if message is None:
                    await interaction.respond(await trl(interaction.user.id, interaction.guild.id, 'quefessions_not_found'), ephemeral=True)
                    return

                await interaction.response.send_modal(modal=ReportTextModal(author, interaction.message, message.content,
                                                                            report_label=await trl(int(author[2]), interaction.guild.id, "quefessions_report_description_label"),
                                                                            report_placeholder=await trl(int(author[2]), interaction.guild.id, "quefessions_report_description_placeholder"),
                                                                            report_title=await trl(int(author[2]), interaction.guild.id, "quefessions_report_title")))
            else:
                await interaction.response.send_modal(modal=ReportTextModal(author, interaction.message, data['Text'],
                                                                            report_label=await trl(int(author[2]), interaction.guild.id, "quefessions_report_description_label"),
                                                                            report_placeholder=await trl(int(author[2]), interaction.guild.id, "quefessions_report_description_placeholder"),
                                                                            report_title=await trl(int(author[2]), interaction.guild.id, "quefessions_report_title")))
        except Exception as e:
            capture_exception(e)
            await interaction.respond(await trl(interaction.user.id, interaction.guild.id, 'command_error_generic'),
                                      ephemeral=True)


class LogsView(View):
    def __init__(self, message: Message):
        super().__init__(timeout=3600, disable_on_timeout=True)

        self.mod_message = message

    @button(label='Delete (Ban before you delete!)', style=ButtonStyle.danger)
    async def delete_quefession(self, button: Button, interaction: Interaction):
        try:
            await self.mod_message.delete()
            self.disable_all_items()
            await interaction.edit(view=self)
            self.stop()
        except Exception as e:
            capture_exception(e)
            await interaction.respond(await trl(interaction.user.id, interaction.guild.id, 'command_error_generic'),
                                      ephemeral=True)

    @button(label='Ban', style=ButtonStyle.danger)
    async def ban(self, button: Button, interaction: Interaction):
        try:
            await interaction.respond('Report actions', ephemeral=True,
                                      view=AdminBanSelectTypeView(message=self.mod_message))
        except Exception as e:
            capture_exception(e)
            await interaction.respond(await trl(interaction.user.id, interaction.guild.id, 'command_error_generic'),
                                      ephemeral=True)


class AnonymousQuefessions(Cog):
    def __init__(self, bot: Bot):
        self.bot = bot

    anonymous_quefessions_cmd = SlashCommandGroup(name='anonymous_quefessions',
                                                  description='Anonymous Quefessions Management')

    @anonymous_quefessions_cmd.command()
    @guild_only()
    @has_guild_permissions(manage_guild=True)
    async def set_quefessions(self, ctx: ApplicationContext, enabled: bool):
        if get_key("Message_Intent", "false") == "false":
            await ctx.respond("Sorry, this instance doesn\'t have message intent. Please use the `/create_quefessions_sending_msg` command instead.", ephemeral=True)
            return

        try:
            await set_setting(ctx.guild.id, f'quefessions_enabled_{ctx.channel.id}', enabled)
            await ctx.respond(
                trl(ctx.user.id, ctx.guild.id, 'quefessions_channel_enabled') if enabled else
                trl(ctx.user.id, ctx.guild.id, 'quefessions_channel_disabled'),
                ephemeral=True)
        except Exception as e:
            capture_exception(e)
            await ctx.respond(await trl(ctx.user.id, ctx.guild.id, 'command_error_generic'), ephemeral=True)

    @anonymous_quefessions_cmd.command()
    @guild_only()
    @has_guild_permissions(manage_guild=True)
    async def set_quefessions_reply(self, ctx: ApplicationContext, enabled: bool):
        try:
            await set_setting(ctx.guild.id, f'quefessions_replies_{ctx.channel.id}', enabled)
            await ctx.respond(
                trl(ctx.user.id, ctx.guild.id, 'quefessions_replies_enabled') if enabled else
                trl(ctx.user.id, ctx.guild.id, 'quefessions_replies_disabled'),
                ephemeral=True)
        except Exception as e:
            capture_exception(e)
            await ctx.respond(await trl(ctx.user.id, ctx.guild.id, 'command_error_generic'), ephemeral=True)

    @anonymous_quefessions_cmd.command()
    @has_guild_permissions(manage_guild=True)
    @guild_only()
    async def create_quefessions_sending_msg(self, ctx: ApplicationContext):
        if get_key("Message_Intent", "false") == "true":
            await ctx.respond("This instance has message intent. Please use the `/set_quefessions` command instead.", ephemeral=True)
            return

        try:
            await ctx.channel.send(
                embed=Embed(
                    title=trl(ctx.user.id, ctx.guild.id, 'quefessions_submit_title'),
                    description=trl(ctx.user.id, ctx.guild.id, 'quefessions_submit_description')
                ),
                view=CreateButtonView()
            )

            await ctx.respond(await trl(ctx.user.id, ctx.guild.id, 'quefessions_sent_successfully'), ephemeral=True)

        except Exception as e:
            capture_exception(e)
            await ctx.respond(await trl(ctx.user.id, ctx.guild.id, 'command_error_generic'), ephemeral=True)

    @Cog.listener()
    async def on_message(self, message: Message):
        if get_key('Message_Intent', "false") == "false":
            return

        try:
            if message.author.bot:
                return

            if not await get_setting(message.guild.id, f'quefessions_enabled_{message.channel.id}', False) == True:
                return

            client = get_client()
            await client['AnonymousQuefessionsBans'].delete_many({
                '$and': [
                    {'BanEnd': {'$exists': True}},
                    {'BanEnd': {'$lt': datetime.datetime.now()}}
                ]
            })

            ban = await client['AnonymousQuefessionsBans'].find_one({
                'MemberID': str(message.author.id)
            })

            if ban is not None:
                reply = await message.reply(await trl(message.author.id, message.guild.id, 'quefessions_banned'))
                await message.delete()
                await reply.delete(delay=5)
                return

            msg = await message.channel.send(
                embed=Embed(
                    title=trl(0, message.guild.id, 'quefessions_embed_title'),
                    description=message.content,
                    author=EmbedAuthor(
                        name=message.author.display_name,
                        icon_url=message.author.display_avatar.url
                    ),
                    timestamp=datetime.datetime.now(datetime.timezone.utc)
                ),
                view=InfoButtonView(message.guild.id, message.channel.id)
            )

            await client['AnonymousQuefessions'].insert_one({
                'GuildID': str(message.guild.id),
                'ChannelID': str(message.channel.id),
                'MessageID': str(msg.id),
                'AuthorID': str(message.author.id)
            })

            await message.delete()
        except Exception as e:
            capture_exception(e)

    @Cog.listener()
    async def on_message_delete(self, message: Message):
        try:
            client = get_client()

            await client['AnonymousQuefessions'].delete_many({
                'GuildID': str(message.guild.id),
                'ChannelID': str(message.channel.id),
                'MessageID': str(message.id)
            })
        except Exception as e:
            capture_exception(e)
