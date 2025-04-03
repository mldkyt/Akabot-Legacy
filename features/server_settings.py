#      Akabot is a general purpose bot with a ton of features.
#      Copyright (C) 2023-2025 mldchan
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

import re

import discord
import sentry_sdk

from utils.analytics import analytics
from utils.blocklist import blocklist
from utils.languages import get_translation_for_key_localized as trl
from utils.languages import language_name_to_code, get_language_names, get_language_name
from utils.settings import set_setting


class ServerSettings(discord.Cog):
    server_settings_group = discord.SlashCommandGroup(name='server_settings', description='Server settings')

    @server_settings_group.command(name='language', description="Change the server language.")
    @discord.option(name='lang', description="The language to set the server to.", choices=get_language_names())
    @analytics("server_settings language")
    @blocklist()
    async def server_language(self, ctx: discord.ApplicationContext, lang: str):
        try:
            lang_code = language_name_to_code(lang)
            set_setting(ctx.guild.id, 'language', lang_code)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "server_language_response", append_tip=True).format(
                lang=get_language_name(lang_code, completeness=False)), ephemeral=True)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @server_settings_group.command(name='tz', description='Timezone setting')
    @discord.option(name='tz', description='Timezone')
    @analytics("server_settings timezone")
    @blocklist()
    async def tz_setting(self, ctx: discord.ApplicationContext, tz: float):
        try:
            if not re.match(r"^[+-]?\d+(\.\d)?$", str(tz)):
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "server_tz_invalid"), ephemeral=True)
                return

            # check range
            if tz > 14 or tz < -12:
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "server_tz_invalid"), ephemeral=True)
                return

            set_setting(ctx.guild.id, 'timezone_offset', str(tz))

            tz_formatted = str(tz)
            if re.match(r'^[+-]?\d+\.0$', tz_formatted):
                tz_formatted = tz_formatted[:-2]
            await ctx.respond(
                trl(ctx.user.id, ctx.guild.id, "server_tz_response", append_tip=True).format(tz=tz_formatted),
                ephemeral=True)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)
