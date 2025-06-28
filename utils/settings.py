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

from database import get_client


async def get_setting(server_id: int, key: str, default):
    client = get_client()
    res = await client['ServerSettings'].find_one({'GuildID': str(server_id)})
    if not res:
        return default
    if key not in res:
        return default

    return res[key] if res and key in res else default


async def set_setting(server_id: int, key: str, value) -> None:
    client = get_client()
    if await client['ServerSettings'].count_documents({'GuildID': str(server_id)}) == 0:
        await client['ServerSettings'].insert_one({'GuildID': str(server_id)})

    if value is not None:
        await client['ServerSettings'].update_one({'GuildID': str(server_id)}, {'$set': {key: value}})
    else:
        await client['ServerSettings'].update_one({'GuildID': str(server_id)}, {'$unset': {key: 1}})

