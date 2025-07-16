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
import datetime
import logging

import discord
from discord.ext import commands as commands_ext

from utils.analytics import analytics
from utils.blocklist import blocklist
from utils.languages import get_translation_for_key_localized as trl
from utils.logging_util import log_into_logs
from utils.per_server_settings import get_setting, set_setting

akabot_logger = logging.getLogger("akabot")

class WelcomingCache:
    def __init__(self):
        self.cache = []

    def member_join(self, member: discord.Member, welcome_message: discord.Message):
        grace_period_minutes = get_setting(member.guild.id, "welcome_grace_period_minutes", "5")
        self.cache.append({
            "GuildID": str(member.guild.id),
            "MemberID": str(member.id),
            "GracePeriod": datetime.datetime.now() + datetime.timedelta(minutes=int(grace_period_minutes)),
            "WelcomeMessage": welcome_message.id
        })

    def is_member_in_grace_period(self, member: discord.Member):
        self.cache = [i for i in self.cache if i["GracePeriod"] > datetime.datetime.now()]
        return any(i["GuildID"] == str(member.guild.id) and i["MemberID"] == str(member.id) for i in self.cache)

    def get_welcome_message(self, member: discord.Member):
        for i in self.cache:
            if i["GuildID"] == str(member.guild.id) and i["MemberID"] == str(member.id):
                return i["WelcomeMessage"]

        return None

    def remove_from_cache(self, member: discord.Member):
        self.cache = [i for i in self.cache if i["GuildID"] != str(member.guild.id) and i["MemberID"] != str(member.id)]

class Welcoming(discord.Cog):
    def __init__(self, bot: discord.Bot) -> None:
        self.bot = bot
        self.cache = WelcomingCache()

    @discord.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        try:
            target_channel_id = get_setting(member.guild.id, 'welcome_channel', '0')
            if target_channel_id == '0':
                return  # The channel was not set and was initialised as we just ran this
            message_type = get_setting(member.guild.id, 'welcome_type', 'embed')  # embed or text
            message_title = get_setting(member.guild.id, 'welcome_title', 'Welcome')  # embed title (if type is embed)
            message_text = get_setting(member.guild.id, 'welcome_text',
                                       'Welcome {user} to {server}!')  # text of the message or description of embed

            target_channel = member.guild.get_channel(int(target_channel_id))
            if target_channel is None:
                return  # Cannot find channel, don't do any further actions

            message_title = message_title.replace('{user}', member.display_name)
            message_title = message_title.replace('{server}', member.guild.name)
            message_title = message_title.replace('{memberCount}', str(member.guild.member_count))
            message_title = message_title.replace('{mention}', member.mention)

            message_text = message_text.replace('{user}', member.display_name)
            message_text = message_text.replace('{server}', member.guild.name)
            message_text = message_text.replace('{memberCount}', str(member.guild.member_count))
            message_text = message_text.replace('{mention}', member.mention)

            if not target_channel.can_send():
                return 

            if message_type == 'embed':
                embed = discord.Embed(title=message_title, description=message_text,
                                      color=discord.Color.green())  # Create the embed
                msg = await target_channel.send(embed=embed)  # Send it in the welcoming channel
                self.cache.member_join(member, msg)
            if message_type == 'text':
                msg = await target_channel.send(content=message_text)  # Send it as text only
                self.cache.member_join(member, msg)

        except Exception as e:
            akabot_logger.exception("An error occured:")

    async def delete_welcome_message(self, member: discord.Member):
        try:
            welcome_message_id = self.cache.get_welcome_message(member)
            if welcome_message_id is None:
                return

            welcome_channel_id = get_setting(member.guild.id, 'welcome_channel', '0')
            if welcome_channel_id == '0':
                return

            welcome_channel = member.guild.get_channel(int(welcome_channel_id))
            if welcome_channel is None:
                return

            message = await welcome_channel.fetch_message(int(welcome_message_id))
            if message is None:
                return

            grace_period_minutes = get_setting(member.guild.id, 'welcome_grace_period_minutes', '5')

            await message.delete()
            self.cache.remove_from_cache(member)

            emb = discord.Embed(
                title=trl(0, member.guild.id, "welcome_grace_period_log_title").format(minutes=str(grace_period_minutes)),
                description=trl(0, member.guild.id, "welcome_grace_period_log_description").format(minutes=str(grace_period_minutes), mention=member.mention, displayname=member.display_name, name=member.name, id=str(member.id)),
                color=discord.Color.red()
            )

            await log_into_logs(member.guild, emb)
        except Exception as e:
            akabot_logger.exception("An error occured:")

    @discord.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        try:
            if self.cache.is_member_in_grace_period(member):
                await self.delete_welcome_message(member)
                return

            target_channel_id = get_setting(member.guild.id, 'goodbye_channel', '0')
            if target_channel_id == '0':
                return  # The channel was not set and was initialised as we just ran this
            message_type = get_setting(member.guild.id, 'goodbye_type', 'embed')  # embed or text
            message_title = get_setting(member.guild.id, 'goodbye_title', 'Goodbye')  # embed title (if type is embed)
            message_text = get_setting(member.guild.id, 'goodbye_text',
                                       'Goodbye {user}!')  # text of the message or description of embed

            target_channel = member.guild.get_channel(int(target_channel_id))
            if target_channel is None:
                return  # Cannot find channel, don't do any further actions

            message_title = message_title.replace('{user}', member.display_name)
            message_title = message_title.replace('{server}', member.guild.name)
            message_title = message_title.replace('{memberCount}', str(member.guild.member_count))
            message_title = message_title.replace('{mention}', member.mention)

            message_text = message_text.replace('{user}', member.display_name)
            message_text = message_text.replace('{server}', member.guild.name)
            message_text = message_text.replace('{memberCount}', str(member.guild.member_count))
            message_text = message_text.replace('{mention}', member.mention)

            if not target_channel.can_send():
                return

            if message_type == 'embed':
                embed = discord.Embed(title=message_title, description=message_text,
                                      color=discord.Color.red())  # Create the embed
                await target_channel.send(embed=embed)  # Send it in the welcoming channel
            if message_type == 'text':
                await target_channel.send(content=message_text)  # Send it as text only
        except Exception as e:
            akabot_logger.exception("An error occured:")

    welcome_subcommands = discord.SlashCommandGroup(name="welcome", description="Change the welcoming message")

    @welcome_subcommands.command(name="list", description="List the welcoming settings")
    @discord.default_permissions(manage_guild=True)
    @commands_ext.has_permissions(manage_guild=True)
    @commands_ext.guild_only()
    @analytics("welcome list")
    @blocklist()
    async def welcome_list_settings(self, ctx: discord.ApplicationContext):
        try:
            welcome_channel = get_setting(ctx.guild.id, 'welcome_channel', '0')
            welcome_type = get_setting(ctx.guild.id, 'welcome_type', 'embed')
            welcome_title = get_setting(ctx.guild.id, 'welcome_title', 'Welcome')
            welcome_text = get_setting(ctx.guild.id, 'welcome_text', 'Welcome {user} to {server}!')

            embed = discord.Embed(title=trl(ctx.user.id, ctx.guild.id, "welcome_settings_embed_title"),
                                  color=discord.Color.blurple())
            embed.add_field(name=trl(ctx.user.id, ctx.guild.id, "logging_channel"), value=welcome_channel)
            embed.add_field(name=trl(ctx.user.id, ctx.guild.id, "welcome_settings_type"), value=welcome_type)
            embed.add_field(name=trl(ctx.user.id, ctx.guild.id, "welcome_settings_title"), value=welcome_title)
            embed.add_field(name=trl(ctx.user.id, ctx.guild.id, "welcome_settings_text"), value=welcome_text)

            await ctx.respond(embed=embed, ephemeral=True)
        except Exception as e:
            akabot_logger.exception("An error occured:")
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @welcome_subcommands.command(name='channel', description="Set the welcoming channel")
    @discord.default_permissions(manage_guild=True)
    @commands_ext.has_permissions(manage_guild=True)
    @commands_ext.guild_only()
    @commands_ext.bot_has_permissions(view_channel=True, send_messages=True)
    @analytics("welcome channel")
    @blocklist()
    async def welcome_channel(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
        try:
            # Get old channel
            old_welcome_channel_id = get_setting(ctx.guild.id, "welcome_channel", '0')
            old_welcome_channel = ctx.guild.get_channel(int(old_welcome_channel_id))

            # Set new channel
            set_setting(ctx.guild.id, 'welcome_channel', str(channel.id))

            # Logging embed
            logging_embed = discord.Embed(title=trl(ctx.user.id, ctx.guild.id, "welcome_channel_log_title"))
            logging_embed.add_field(name=trl(ctx.user.id, ctx.guild.id, "logging_user"), value=f"{ctx.user.mention}")
            if old_welcome_channel is None:
                logging_embed.add_field(name=trl(ctx.user.id, ctx.guild.id, "logging_channel"),
                                        value=f"{channel.mention}")
            else:
                logging_embed.add_field(name=trl(ctx.user.id, ctx.guild.id, "logging_channel"),
                                        value=f"{old_welcome_channel.mention} -> {channel.mention}")

            # Send log
            await log_into_logs(ctx.guild, logging_embed)

            # Respond
            await ctx.respond(
                trl(ctx.user.id, ctx.guild.id, "welcome_channel_set", append_tip=True).format(channel=channel.mention),
                ephemeral=True)
        except Exception as e:
            akabot_logger.exception("An error occured:")
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @welcome_subcommands.command(name='type', description="Set whether you want to use message content or embed")
    @discord.default_permissions(manage_guild=True)
    @commands_ext.has_permissions(manage_guild=True)
    @commands_ext.guild_only()
    @discord.option(name="message_type", description="The type of the message (embed or text)",
                    choices=['embed', 'text'])
    @analytics("welcome type")
    @blocklist()
    async def welcome_type(self, ctx: discord.ApplicationContext, message_type: str):
        try:
            # Get old response type
            old_welcome_type = get_setting(ctx.guild.id, "welcome_type", '0')

            # Set new response type
            set_setting(ctx.guild.id, 'welcome_type', message_type)

            # Logging embed
            logging_embed = discord.Embed(title=trl(0, ctx.guild.id, "welcome_type_log_title"))
            logging_embed.add_field(name=trl(0, ctx.guild.id, "logging_user"), value=f"{ctx.user.mention}")
            logging_embed.add_field(name=trl(0, ctx.guild.id, "logging_response_type"),
                                    value=f"{old_welcome_type} -> {message_type}")

            # Send log
            await log_into_logs(ctx.guild, logging_embed)

            # Respond
            await ctx.respond(
                trl(ctx.user.id, ctx.guild.id, "welcome_type_set", append_tip=True).format(type=message_type),
                ephemeral=True)
        except Exception as e:
            akabot_logger.exception("An error occured:")
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @welcome_subcommands.command(name='title', description="Set the title of the welcoming message")
    @discord.default_permissions(manage_guild=True)
    @commands_ext.has_permissions(manage_guild=True)
    @commands_ext.guild_only()
    @discord.option(name="title", description="The title of the message")
    @analytics("welcome title")
    @blocklist()
    async def welcome_title(self, ctx: discord.ApplicationContext, title: str):
        try:
            # Get old response title
            old_welcome_title = get_setting(ctx.guild.id, "welcome_title", '0')

            # Set new message
            set_setting(ctx.guild.id, 'welcome_title', title)

            # Logging embed
            logging_embed = discord.Embed(title=trl(0, ctx.guild.id, "welcome_title_log_title"))
            logging_embed.add_field(name=trl(0, ctx.guild.id, "logging_user"), value=f"{ctx.user.mention}")
            logging_embed.add_field(name=trl(0, ctx.guild.id, "title"), value=f"{old_welcome_title} -> {title}")

            # Send log
            await log_into_logs(ctx.guild, logging_embed)

            # Respond
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "welcome_title_set", append_tip=True).format(title=title),
                              ephemeral=True)
        except Exception as e:
            akabot_logger.exception("An error occured:")
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @welcome_subcommands.command(name='text', description="Set the text of the welcoming message")
    @discord.default_permissions(manage_guild=True)
    @commands_ext.has_permissions(manage_guild=True)
    @commands_ext.guild_only()
    @discord.option(name="text", description="The content of the message or description of the embed")
    @analytics("welcome text")
    @blocklist()
    async def welcome_text(self, ctx: discord.ApplicationContext, text: str):
        try:
            # Get old welcome text
            old_welcome_text = get_setting(ctx.guild.id, "welcome_text", '0')

            # Set new welcome text
            set_setting(ctx.guild.id, 'welcome_text', text)

            # Logging embed
            logging_embed = discord.Embed(title=trl(0, ctx.guild.id, "welcome_text_log_title"))
            logging_embed.add_field(name=trl(0, ctx.guild.id, "logging_user"), value=f"{ctx.user.mention}")
            logging_embed.add_field(name=trl(0, ctx.guild.id, "logging_text"), value=f"{old_welcome_text} -> {text}")

            # Send log
            await log_into_logs(ctx.guild, logging_embed)

            # Respond
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "welcome_text_sent", append_tip=True).format(text=text),
                              ephemeral=True)
        except Exception as e:
            akabot_logger.exception("An error occured:")
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @welcome_subcommands.command(name="grace_period", description="Set up a grace period. If a member leaves within this time, the welcome message is deleted")
    @discord.default_permissions(manage_guild=True)
    @commands_ext.has_permissions(manage_guild=True)
    @commands_ext.guild_only()
    @discord.option(name="minutes", description="The minutes of the grace period of the message")
    @analytics("welcome grace period")
    @blocklist()
    async def welcome_grace_period(self, ctx: discord.ApplicationContext, minutes: int):
        try:
            # Old grace period
            old_grace_period = get_setting(ctx.guild.id, "welcome_grace_period_minutes", '5')

            # Set new grace period
            set_setting(ctx.guild.id, 'welcome_grace_period_minutes', minutes)

            # logging embed
            emb = discord.Embed(
                title=trl(0, ctx.guild.id, "welcome_grace_period_log_setting_title"),
                fields=[
                    discord.EmbedField(
                        name=trl(0, ctx.guild.id, "welcome_grace_period_log_minutes_label"),
                        value=f"{old_grace_period} -> {minutes}"
                    )
                ],
                color=discord.Color.blurple()
            )

            # Send log
            await log_into_logs(ctx.guild, emb)

            # Respond
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "welcome_grace_period_set", append_tip=True).format(minutes=minutes), ephemeral=True)
        except Exception as e:
            akabot_logger.exception("An error occured:")
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)



    goodbye_subcommands = discord.SlashCommandGroup(name="goodbye", description="Change the goodbye message")

    @goodbye_subcommands.command(name="list", description="List the goodbye settings")
    @discord.default_permissions(manage_guild=True)
    @commands_ext.has_permissions(manage_guild=True)
    @commands_ext.guild_only()
    @analytics("goodbye list")
    @blocklist()
    async def goodbye_list_settings(self, ctx: discord.ApplicationContext):
        try:
            goodbye_channel = get_setting(ctx.guild.id, 'goodbye_channel', '0')
            goodbye_type = get_setting(ctx.guild.id, 'goodbye_type', 'embed')
            goodbye_title = get_setting(ctx.guild.id, 'goodbye_title', 'Welcome')
            goodbye_text = get_setting(ctx.guild.id, 'goodbye_text', 'Welcome {user} to {server}!')

            embed = discord.Embed(title=trl(ctx.user.id, ctx.guild.id, "goodbye_settings_embed_title"),
                                  color=discord.Color.blurple())
            embed.add_field(name=trl(ctx.user.id, ctx.guild.id, "logging_channel"), value=goodbye_channel)
            embed.add_field(name=trl(ctx.user.id, ctx.guild.id, "goodbye_settings_type"), value=goodbye_type)
            embed.add_field(name=trl(ctx.user.id, ctx.guild.id, "goodbye_settings_title"), value=goodbye_title)
            embed.add_field(name=trl(ctx.user.id, ctx.guild.id, "goodbye_settings_text"), value=goodbye_text)

            await ctx.respond(embed=embed, ephemeral=True)
        except Exception as e:
            akabot_logger.exception("An error occured:")
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @goodbye_subcommands.command(name='channel', description="Set the goodbye channel")
    @discord.default_permissions(manage_guild=True)
    @commands_ext.has_permissions(manage_guild=True)
    @commands_ext.guild_only()
    @commands_ext.bot_has_permissions(view_channel=True, send_messages=True)
    @analytics("goodbye channel")
    @blocklist()
    async def goodbye_channel(self, ctx: discord.ApplicationContext, channel: discord.TextChannel):
        try:
            # Get old goodbye channel
            old_goodbye_channel = get_setting(ctx.guild.id, "goodbye_channel", '0')

            # Set new goodbye channel
            set_setting(ctx.guild.id, 'goodbye_channel', str(channel.id))

            # Logging embed
            logging_embed = discord.Embed(title=trl(0, ctx.guild.id, "goodbye_channel_log_title"))
            logging_embed.add_field(name=trl(0, ctx.guild.id, "logging_user"), value=f"{ctx.user.mention}")
            logging_embed.add_field(name=trl(0, ctx.guild.id, "logging_channel"),
                                    value=f"{old_goodbye_channel} -> {channel.mention}")

            # Send log
            await log_into_logs(ctx.guild, logging_embed)

            # Respond
            await ctx.respond(
                trl(ctx.user.id, ctx.guild.id, "goodbye_channel_set", append_tip=True).format(channel=channel.mention),
                ephemeral=True)
        except Exception as e:
            akabot_logger.exception("An error occured:")
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @goodbye_subcommands.command(name='type', description="Set whether you want to use message content or embed")
    @discord.default_permissions(manage_guild=True)
    @commands_ext.has_permissions(manage_guild=True)
    @commands_ext.guild_only()
    @discord.option(name="message_type", description="The type of the message (embed or text)",
                    choices=['embed', 'text'])
    @analytics("goodbye type")
    @blocklist()
    async def goodbye_type(self, ctx: discord.ApplicationContext, message_type: str):
        try:
            # Get old goodbye type
            old_goodbye_type = get_setting(ctx.guild.id, "goodbye_type", 'embed')

            # Set new goodbye type
            set_setting(ctx.guild.id, 'goodbye_type', message_type)

            # Logging embed
            logging_embed = discord.Embed(title=trl(0, ctx.guild.id, "goodbye_type_log_title"))
            logging_embed.add_field(name=trl(0, ctx.guild.id, "logging_user"), value=f"{ctx.user.mention}")
            logging_embed.add_field(name=trl(0, ctx.guild.id, "logging_response_type"),
                                    value=f"{old_goodbye_type} -> {message_type}")

            # Send log
            await log_into_logs(ctx.guild, logging_embed)

            # Respond
            await ctx.respond(
                trl(ctx.user.id, ctx.guild.id, "goodbye_type_set", append_tip=True).format(type=message_type),
                ephemeral=True)
        except Exception as e:
            akabot_logger.exception("An error occured:")
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @goodbye_subcommands.command(name='title', description="Set the title of the goodbye message")
    @discord.default_permissions(manage_guild=True)
    @commands_ext.has_permissions(manage_guild=True)
    @commands_ext.guild_only()
    @discord.option(name="title", description="The title of the message")
    @analytics("goodbye title")
    @blocklist()
    async def goodbye_title(self, ctx: discord.ApplicationContext, title: str):
        try:
            # Get old goodbye title
            old_goodbye_title = get_setting(ctx.guild.id, "goodbye_title", 'Welcome')

            # Set new goodbye title
            set_setting(ctx.guild.id, 'goodbye_title', title)

            # Logging embed
            logging_embed = discord.Embed(title=trl(0, ctx.guild.id, "goodbye_title_log_title"))
            logging_embed.add_field(name=trl(0, ctx.guild.id, "logging_user"), value=f"{ctx.user.mention}")
            logging_embed.add_field(name=trl(0, ctx.guild.id, "title"), value=f"{old_goodbye_title} -> {title}")

            # Send log
            await log_into_logs(ctx.guild, logging_embed)

            # Respond
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "goodbye_title_set", append_tip=True).format(title=title),
                              ephemeral=True)
        except Exception as e:
            akabot_logger.exception("An error occured:")
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @goodbye_subcommands.command(name='text', description="Set the text of the goodbye message")
    @discord.default_permissions(manage_guild=True)
    @commands_ext.has_permissions(manage_guild=True)
    @commands_ext.guild_only()
    @discord.option(name="text", description="The content of the message or description of the embed")
    @analytics("goodbye text")
    @blocklist()
    async def goodbye_text(self, ctx: discord.ApplicationContext, text: str):
        try:
            # Get old goodbye text
            old_goodbye_text = get_setting(ctx.guild.id, "goodbye_text", 'Welcome {user} to {server}!')

            # Set new goodbye text
            set_setting(ctx.guild.id, 'goodbye_text', text)

            # Logging embed
            logging_embed = discord.Embed(title=trl(0, ctx.guild.id, "goodbye_text_log_title"))
            logging_embed.add_field(name=trl(0, ctx.guild.id, "logging_user"), value=f"{ctx.user.mention}")
            logging_embed.add_field(name=trl(0, ctx.guild.id, "logging_text"), value=f"{old_goodbye_text} -> {text}")

            # Send log
            await log_into_logs(ctx.guild, logging_embed)

            # Respond
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "goodbye_text_set", append_tip=True).format(text=text),
                              ephemeral=True)
        except Exception as e:
            akabot_logger.exception("An error occured:")
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)
