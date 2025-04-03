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

import discord
import sentry_sdk

from database import client
from utils.analytics import analytics
from utils.blocklist import blocklist
from utils.config import get_key
from utils.languages import get_translation_for_key_localized as trl


class RolesOnJoin(discord.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @discord.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        try:
            roles = client['RolesOnJoin'].find({'GuildID': str(member.guild.id)})
            for row in roles:
                role = member.guild.get_role(row['RoleID'])
                # check role position
                if role is not None:
                    if role.position > member.guild.me.top_role.position:
                        continue
                    try:
                        await member.add_roles(role)
                    except discord.Forbidden:
                        pass
                else:
                    # remove
                    client['RolesOnJoin'].delete_one({'GuildID': str(member.guild.id)})
        except Exception as e:
            sentry_sdk.capture_exception(e)

    roles_on_join_commands = discord.SlashCommandGroup(name="roles_on_join", description="Add roles on join")

    @roles_on_join_commands.command(name="add", description="Add a role on join")
    @analytics("roles_on_join add")
    @blocklist()
    async def add_role_on_join(self, ctx: discord.ApplicationContext, role: discord.Role):
        try:
            # check amount of roles
            res = client['RolesOnJoin'].count_documents({'GuildID': str(ctx.guild.id)})
            if res > int(get_key("Max_RolesOnJoin", "3")):
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "limits_max_rolesonjoin"), ephemeral=True)
                return
            # check role position
            if role.position > ctx.me.top_role.position:
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "roles_on_join_role_above_bot"), ephemeral=True)
                return

            if client['RolesOnJoin'].count_documents({'GuildID': str(ctx.guild.id), 'RoleID': str(role.id)}) == 0:
                client['RolesOnJoin'].insert_one({'GuildID': str(ctx.guild.id), 'RoleID': str(role.id)})
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "roles_on_join_role_added", append_tip=True),
                                  ephemeral=True)
            else:
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "roles_on_join_role_already_in_join_roles"),
                                  ephemeral=True)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @roles_on_join_commands.command(name="remove", description="Remove a role on join")
    @analytics("roles_on_join remove")
    @blocklist()
    async def remove_role_on_join(self, ctx: discord.ApplicationContext, role: discord.Role):
        try:
            if client['RolesOnJoin'].count_documents({'GuildID': str(ctx.guild.id)}) == 0:
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "roles_on_join_role_not_in_join_roles"),
                                  ephemeral=True)
            else:
                client['RolesOnJoin'].delete_one({'GuildID': str(ctx.guild.id)})
                await ctx.respond(trl(ctx.user.id, ctx.guild.id, "roles_on_join_role_removed", append_tip=True),
                                  ephemeral=True)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)

    @roles_on_join_commands.command(name="list", description="List roles on join")
    @analytics("roles_on_join list")
    @blocklist()
    async def list_roles_on_join(self, ctx: discord.ApplicationContext):
        try:
            res = client['RolesOnJoin'].find({'GuildID': str(ctx.guild.id)}).to_list()
            if not res:
                await ctx.respond(
                    trl(ctx.user.id, ctx.guild.id, "roles_on_join_list_no_roles_on_join", append_tip=True),
                    ephemeral=True)
                return

            msg = ""
            # format - {mention}
            for doc in res:
                role = ctx.guild.get_role(doc['RoleID'])
                if role is None:
                    client['RolesOnJoin'].delete_one({'GuildID': str(ctx.guild.id), 'RoleID': doc['RoleID']})
                    continue
                msg = f"{msg}\n{role.mention}"

            embed = discord.Embed(title="Roles on Join", description=msg, color=discord.Color.blurple())
            await ctx.respond(embed=embed, ephemeral=True)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            await ctx.respond(trl(ctx.user.id, ctx.guild.id, "command_error_generic"), ephemeral=True)
