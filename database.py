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

from pymongo import MongoClient

from utils.config import get_key

name = get_key("DB_Username", "")
password = get_key("DB_Password", "")
host = get_key("DB_Host", "localhost")
port = get_key("DB_Port", "27017")
db = get_key("DB_Database", "akabot")

client = MongoClient(f'mongodb://{name}:{password}@{host}:{port}/', 27017)[db]
