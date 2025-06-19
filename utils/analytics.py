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
from discord.ext import commands as commands_ext

from database import client


def db_add_analytics(command: str):
    data = client['Analytics'].find_one({'Command': command})
    if data:
        client['Analytics'].update_one({'Command': command}, {'$inc': {'RunCount': 1}})
    else:
        client['Analytics'].insert_one({'Command': command, 'RunCount': 1})
        
def db_upsert_active_user(user_id: int):
    client['AnalyticsAkabotUsers'].update_one({
        'UserID': str(user_id)
    }, {
        '$set': {
            'LastBotUse': datetime.datetime.now()
        }
    }, upsert=True)


def analytics(command: str):
    def predicate(ctx: commands_ext.Context):
        db_add_analytics(command)
        db_upsert_active_user(ctx.author.id)
        return True

    return commands_ext.check(predicate)
