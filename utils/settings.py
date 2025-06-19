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

from database import client


def get_setting(server_id: int, key: str, default):
    res = client['ServerSettings'].find_one({'GuildID': str(server_id)})
    if not res:
        return default
    if key not in res:
        return default

    return res[key] if res and key in res else default


def set_setting(server_id: int, key: str, value) -> None:
    if client['ServerSettings'].count_documents({'GuildID': str(server_id)}) == 0:
        client['ServerSettings'].insert_one({'GuildID': str(server_id)})

    if value is not None:
        client['ServerSettings'].update_one({'GuildID': str(server_id)}, {'$set': {key: value}})
    else:
        client['ServerSettings'].update_one({'GuildID': str(server_id)}, {'$unset': {key: 1}})
