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


async def get_per_user_setting(user_id: int, setting_name: str, default_value) -> str:
    client = get_client()
    res = await client['UserSettings'].find_one({'UserID': str(user_id)})
    return res[setting_name] if res and setting_name in res else default_value


async def set_per_user_setting(user_id: int, setting_name: str, setting_value):
    if setting_name == "_id" or setting_name == "UserID":
        raise Exception('Invalid setting name')

    client = get_client()

    if await client['UserSettings'].count_documents({'UserID': str(user_id)}) == 0:
        await client['UserSettings'].insert_one({'UserID': str(user_id)})

    if setting_value is not None:
        await client['UserSettings'].update_one({'UserID': str(user_id)}, {'$set': {setting_name: setting_value}})
    else:
        await client['UserSettings'].update_one({'UserID': str(user_id)}, {'$unset': {setting_name: 1}})

