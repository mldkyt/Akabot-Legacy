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

import datetime

import discord

from database import client
from utils.settings import get_setting
from utils.tzutil import get_now_for_server


def calc_multiplier(guild_id: int):
    multiplier = int(get_setting(guild_id, 'leveling_xp_multiplier', '1'))

    multipliers = mult_list(guild_id)
    for m in multipliers:
        start_month, start_day = map(int, m['StartDate'].split('-'))
        end_month, end_day = map(int, m['EndDate'].split('-'))

        now = get_now_for_server(guild_id)
        start_date = datetime.datetime(now.year, start_month, start_day)
        end_date = datetime.datetime(now.year, end_month, end_day, hour=23, minute=59, second=59)

        if end_date < start_date:
            end_date = end_date.replace(year=end_date.year + 1)

        if start_date <= now <= end_date:
            multiplier *= m['Multiplier']

    return multiplier


def get_xp(guild_id: int, user_id: int):
    data = client['Leveling'].find_one({'GuildID': str(guild_id), 'UserID': str(user_id)})
    return data['XP'] if data else 1


def add_xp(guild_id: int, user_id: int, xp: int):
    data = client['Leveling'].find_one({'GuildID': str(guild_id), 'UserID': str(user_id)})
    if data:
        multiplier = calc_multiplier(guild_id)
        client['Leveling'].update_one({'GuildID': str(guild_id), 'UserID': str(user_id)},
                                      {'$inc': {'XP': xp * multiplier}}, upsert=True)
    else:
        multiplier = calc_multiplier(guild_id)
        client['Leveling'].insert_one({'GuildID': str(guild_id), 'UserID': str(user_id), 'XP': xp * multiplier})


def get_level_for_xp(guild_id: int, xp: int):
    level = 0
    xp_needed = calc_multiplier(guild_id) * int(get_setting(guild_id, 'leveling_xp_per_level', '500'))
    while xp >= xp_needed:
        level += 1
        xp -= xp_needed
        xp_needed = calc_multiplier(guild_id) * int(get_setting(guild_id, 'leveling_xp_per_level', '500'))

    return level


def get_xp_for_level(guild_id: int, level: int):
    xp = 0
    xp_needed = calc_multiplier(guild_id) * int(get_setting(guild_id, 'leveling_xp_per_level', '500'))
    for _ in range(level):
        xp += xp_needed
        xp_needed = calc_multiplier(guild_id) * int(get_setting(guild_id, 'leveling_xp_per_level', '500'))

    return xp


def add_mult(guild_id: int, name: str, multiplier: int, start_date_month: int, start_date_day: int,
             end_date_month: int, end_date_day: int):
    client['LevelingMultiplier'].insert_one({'GuildID': str(guild_id), 'Name': name, 'Multiplier': multiplier,
                                             'StartDate': '{:02d}-{:02d}'.format(start_date_month, start_date_day),
                                             'EndDate': '{:02d}-{:02d}'.format(end_date_month, end_date_day)})


def mult_exists(guild_id: int, name: str):
    data = client['LevelingMultiplier'].count_documents({'GuildID': str(guild_id), 'Name': name})
    return data > 0


def mult_change_name(guild_id: int, old_name: str, new_name: str):
    client['LevelingMultiplier'].update_one({'GuildID': str(guild_id), 'Name': old_name}, {'$set': {'Name': new_name}})


def mult_change_multiplier(guild_id: int, name: str, multiplier: int):
    client['LevelingMultiplier'].update_one({'GuildID': str(guild_id), 'Name': name},
                                            {'$set': {'Multiplier': multiplier}})


def mult_change_start(guild_id: int, name: str, start_date: datetime.datetime):
    client['LevelingMultiplier'].update_one({'GuildID': str(guild_id), 'Name': name},
                                            {'$set': {'StartDate': start_date}})


def mult_change_end(guild_id: int, name: str, end_date: datetime.datetime):
    client['LevelingMultiplier'].update_one({'GuildID': str(guild_id), 'Name': name}, {'$set': {'EndDate': end_date}})


def mult_del(guild_id: int, name: str):
    client['LevelingMultiplier'].delete_one({'GuildID': str(guild_id), 'Name': name})


def mult_list(guild_id: int):
    data = client['LevelingMultiplier'].find({'GuildID': str(guild_id)}).to_list()
    return data


def mult_get(guild_id: int, name: str):
    data = client['LevelingMultiplier'].find_one({'GuildID': str(guild_id), 'Name': name})
    return data


async def update_roles_for_member(guild: discord.Guild, member: discord.Member):
    xp = get_xp(guild.id, member.id)
    level = get_level_for_xp(guild.id, xp)

    for i in range(1, level + 1):  # Add missing roles
        role_id = get_setting(guild.id, f'leveling_reward_{i}', '0')
        if role_id != '0':
            role = guild.get_role(int(role_id))
            if role.position > guild.me.top_role.position:
                return

            if role is not None and role not in member.roles:
                await member.add_roles(role)

    for i in range(level + 1, 100):  # Remove excess roles
        role_id = get_setting(guild.id, f'leveling_reward_{i}', '0')
        if role_id != '0':
            role = guild.get_role(int(role_id))
            if role.position > guild.me.top_role.position:
                return

            if role is not None and role in member.roles:
                await member.remove_roles(role)
