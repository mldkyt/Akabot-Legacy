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

import discord
import sentry_sdk
from bson import ObjectId

from database import get_client
from utils.generic import get_date_time_str, pretty_time_delta
from utils.languages import get_translation_for_key_localized as trl
from utils.settings import get_setting


async def add_warning(user: discord.Member, guild: discord.Guild, reason: str) -> ObjectId:
    id = await db_add_warning(guild.id, user.id, reason)

    warning_should_dm = await get_setting(guild.id, 'send_warning_message', 'true')
    if warning_should_dm == 'true':
        warning_message = await get_setting(guild.id, 'warning_message', 'You have been warned in {guild} for {reason}.')

        warning_message = warning_message.replace('{name}', user.display_name)
        warning_message = warning_message.replace('{guild}', guild.name)
        warning_message = warning_message.replace('{reason}', reason)
        warning_message = warning_message.replace('{warnings}', str(len(await db_get_warnings(guild.id, user.id))))

        # try dm user
        try:
            await user.send(warning_message)
        except Exception as e:
            sentry_sdk.capture_exception(e)
            pass

    warnings = await db_get_warnings(guild.id, user.id)
    actions = await db_get_warning_actions(guild.id)

    if not actions:
        return id

    for action in actions:
        if len(warnings) == action['Warnings']:  # only apply if the number of warnings matches, not if below
            if action['Action'] == 'kick':
                # try dm user
                try:
                    await user.send(
                        (await trl(user.id, guild.id, "warn_actions_auto_kick_dm")).format(name=guild.name,
                                                                                   warnings=action['Warnings']))
                except Exception as e:
                    sentry_sdk.capture_exception(e)
                    pass
                await user.kick(
                    reason=(await trl(user.id, guild.id, "warn_actions_auto_kick_reason")).format(warnings=action['Warnings']))
            elif action['Action'] == 'ban':
                # try dm user
                try:
                    await user.send(
                        (await trl(user.id, guild.id, "warn_actions_auto_ban_dm")).format(name=guild.name,
                                                                                  warnings=action['Warnings']))
                except Exception as e:
                    sentry_sdk.capture_exception(e)
                    pass
                await user.ban(
                    reason=(await trl(user.id, guild.id, "warn_actions_auto_ban_reason")).format(warnings=action['Warnings']),
                    delete_message_seconds=604800)
            elif action['Action'].startswith('timeout'):
                time = action['Action'].split(' ')[1]
                total_seconds = 0
                if time == '12h':
                    total_seconds = 43200
                elif time == '1d':
                    total_seconds = 86400
                elif time == '7d':
                    total_seconds = 604800
                elif time == '28d':
                    total_seconds = 2419200

                # try dm
                try:
                    await user.send(
                        (await trl(user.id, guild.id, "warn_actions_auto_timeout_dm")).format(name=guild.name,
                                                                                      warnings=action['Warnings'],
                                                                                      time=pretty_time_delta(
                                                                                          total_seconds,
                                                                                          user_id=user.id,
                                                                                          server_id=guild.id)))
                except Exception as e:
                    sentry_sdk.capture_exception(e)
                    pass

                await user.timeout_for(datetime.timedelta(seconds=total_seconds),
                                       reason=(await trl(user.id, guild.id, "warn_actions_auto_timeout_reason")).format(
                                           warnings=action['Warnings']))

    return id


async def db_add_warning(guild_id: int, user_id: int, reason: str) -> ObjectId:
    client = get_client()
    res = await client['Warnings'].insert_one(
        {'GuildID': str(guild_id), 'UserID': str(user_id), 'Reason': reason, 'Timestamp': get_date_time_str(guild_id)})
    return res.inserted_id


async def db_get_warnings(guild_id: int, user_id: int) -> list[dict]:
    client = get_client()
    res = await client['Warnings'].find({'GuildID': str(guild_id), 'UserID': str(user_id)}).to_list()
    return res


async def db_remove_warning(guild_id: int, warning_id: str):
    if not ObjectId.is_valid(warning_id):
        return

    client = get_client()
    await client['Warnings'].delete_one({'GuildID': str(guild_id), '_id': ObjectId(warning_id)})


async def db_add_warning_action(guild_id: int, action: str, warnings: int):
    client = get_client()
    await client['WarningActions'].insert_one({'GuildID': str(guild_id), 'Action': action, 'Warnings': warnings})


async def db_get_warning_actions(guild_id: int) -> list[dict]:
    client = get_client()
    client = get_client()
    res = await client['WarningActions'].find({'GuildID': str(guild_id)}).to_list()
    return res


async def db_remove_warning_action(id: str):
    if not ObjectId.is_valid(id):
        return

    client = get_client()
    await client['WarningActions'].delete_one({'_id': id})
