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

from database import client
from utils.analytics import analytics
from utils.birthdays import set_broadcast
from utils.blocklist import blocklist
from utils.languages import get_language_names, language_name_to_code, get_language_name
from utils.languages import get_translation_for_key_localized as trl
from utils.per_user_settings import set_per_user_setting, get_per_user_setting

akabot_logger = logging.getLogger("akabot")

def days_in_month(month: int, year: int):
    if month == 2:
        return 29 if year % 4 == 0 and year % 100 != 0 else 28

    if month in [1, 3, 5, 7, 8, 10, 12]:
        return 31
    else:
        return 30


class ConfirmDeletionView(discord.ui.View):
    def __init__(self, member_id: int):
        super().__init__()
        self.member_id = member_id

    @discord.ui.button(label="Confirm deletion", style=discord.ButtonStyle.danger)
    async def confirm_delete(self, button: discord.ui.Button, interaction: discord.Interaction):
        # Delete all data
        client['UserBirthday'].delete_one({
            'UserID': str(interaction.user.id)
        })

        # Disable button list
        self.disable_all_items()
        self.stop()
        await interaction.edit(
            content=trl(interaction.user.id, interaction.guild.id, "birthday_announcements_delete_success",
                        append_tip=True), view=self)


class PerUserSettings(discord.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    user_settings_group = discord.SlashCommandGroup(name='user_settings', description='Per user settings')

    @user_settings_group.command(name='chat_streaks_alerts', description='Enable or disable chat streaks alerts')
    @discord.option(name='state', description='How notifications should be sent',
                    choices=['enabled', 'only when lost', 'off'])
    @analytics("user_settings chat_streaks_alerts")
    @blocklist()
    async def chat_streaks_alerts(self, ctx: discord.ApplicationContext, state: str):
        try:
            set_per_user_setting(ctx.user.id, 'chat_streaks_alerts', state)
            if state == 'enabled':
                state = trl(ctx.user.id, ctx.guild.id, "per_user_chat_streak_state_enabled")
            elif state == 'only when lost':
                state = trl(ctx.user.id, ctx.guild.id, "per_user_chat_streak_state_only_when_lost")
            else:
                state = trl(ctx.user.id, ctx.guild.id, "per_user_chat_streak_state_disabled")
            await ctx.respond(
                trl(ctx.user.id, ctx.guild.id, "per_user_chat_streak_response", append_tip=True, state=state),
                ephemeral=True)
        except Exception as e:
            akabot_logger.exception("An error occured:")
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @user_settings_group.command(name='chat_streaks_ping_reply', description='Enable or disable ping when chat streaks reply to you')
    @discord.option(name='state', description='Enable or disable')
    @analytics("user_settings chat_streaks_alerts")
    @blocklist()
    async def chat_streaks_alerts(self, ctx: discord.ApplicationContext, state: bool):
        try:
            set_per_user_setting(ctx.user.id, 'chat_streaks_reply_to_user', state)
            await ctx.respond(
                trl(ctx.user.id, ctx.guild.id,
                    "per_user_chat_streak_replies_response_on" if state else "per_user_chat_streak_replies_response_off",
                    append_tip=True, state=state),
                ephemeral=True)
        except Exception as e:
            akabot_logger.exception("An error occured:")
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @user_settings_group.command(name='langauge',
                                 description='Set your personal language, applies across servers for you')
    @discord.option(name='lang', description='Your language', choices=get_language_names())
    @analytics("user_settings language")
    @blocklist()
    async def set_language(self, ctx: discord.ApplicationContext, lang: str):
        try:
            lang_code = language_name_to_code(lang)

            set_per_user_setting(ctx.user.id, 'language', lang_code)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "per_user_language_set", append_tip=True,
                                  lang=get_language_name(lang_code, completeness=False)), ephemeral=True)
        except Exception as e:
            akabot_logger.exception("An error occured:")
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @user_settings_group.command(name='birthday', description='Set your birthday for Birthday Announcements.')
    @discord.option(name='birthday', description='Your birthday in the format YYYY-MM-DD')
    @analytics("user_settings birthday")
    @blocklist()
    async def set_birthdate(self, ctx: discord.ApplicationContext, year: int, month: int, day: int):
        try:
            now = datetime.datetime.now()
            if now.year - 100 < year > now.year - 13:
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, 'birthday_invalid_year'), ephemeral=True)
                return

            if 1 >= month <= 12:
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, 'birthday_invalid_month'), ephemeral=True)
                return

            if 1 >= day <= days_in_month(month, year):
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, 'birthday_invalid_day'), ephemeral=True)
                return

            client['UserBirthday'].update_one({'UserID': str(ctx.author.id)},
                                              {'$set': {'Birth.Year': year, 'Birth.Month': month, 'Birth.Day': day}},
                                              upsert=True)
            await ctx.respond(
                trl(ctx.user.id, ctx.guild.id, 'birthday_set', append_tip=True, birthday=f'{year}/{month}/{day}'),
                ephemeral=True)
        except Exception as e:
            akabot_logger.exception("An error occured:")
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @user_settings_group.command(name="birthday_settings", description="Personalize your birthday settings")
    @discord.option(name="send_dm", type=bool, description="Whether to allow this bot to send DMs to you")
    @analytics("user_settings birthday_settings")
    @blocklist()
    async def set_birthday_settings(self, ctx: discord.ApplicationContext, send_dm: bool | None = None):
        try:
            if send_dm is not None:
                set_per_user_setting(ctx.user.id, 'birthday_send_dm', str(send_dm).lower())

            send_dm = get_per_user_setting(ctx.user.id, 'birthday_send_dm', "false")

            send_dm = trl(ctx.user.id, ctx.guild.id, "per_user_birthday_send_dm_enabled", append_tip=True) \
                if send_dm else trl(ctx.user.id, ctx.guild.id, "per_user_birthday_send_dm_disabled", append_tip=True)

            await ctx.respond(f"{send_dm}", ephemeral=True)
        except Exception as e:
            akabot_logger.exception("An error occured:")
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @user_settings_group.command(name="birthday_announcements",
                                 description="Whether to announce birthdays in the server you're currently in")
    @discord.option(name="state", description="Send announcements in this server")
    @analytics("user_settings birthday_announcements")
    @blocklist()
    async def set_birthday_announcement(self, ctx: discord.ApplicationContext, state: bool):
        try:
            set_broadcast(ctx.user.id, ctx.guild.id, state)

            if state:
                state_str = trl(ctx.user.id, ctx.guild.id, "per_user_birthday_announcements_enabled", append_tip=True)
            else:
                state_str = trl(ctx.user.id, ctx.guild.id, "per_user_birthday_announcements_disabled", append_tip=True)
            await ctx.respond(state_str, ephemeral=True)
        except Exception as e:
            akabot_logger.exception("An error occured:")
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @user_settings_group.command(name='clear_birthday', description='Clear all data about your birthday from the bot')
    @analytics("user_settings clear_birthday")
    @blocklist()
    async def clear_birthday(self, ctx: discord.ApplicationContext):
        try:
            view = ConfirmDeletionView(ctx.user.id)

            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "per_user_birthday_question", append_tip=True),
                              view=view, ephemeral=True)
        except Exception as e:
            akabot_logger.exception("An error occured:")
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @user_settings_group.command(name='tips', description='Enable or disable tips')
    @analytics('user_settings tips')
    async def set_tips(self, ctx: discord.ApplicationContext, state: bool):
        try:
            set_per_user_setting(ctx.user.id, 'tips_enabled', str(state).lower())
            if state:
                state_str = trl(ctx.user.id, ctx.guild.id, "per_user_tips_enabled", append_tip=True)
            else:
                state_str = trl(ctx.user.id, ctx.guild.id, "per_user_tips_disabled", append_tip=True)
            await ctx.respond(state_str, ephemeral=True)
        except Exception as e:
            akabot_logger.exception("An error occured:")
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)
