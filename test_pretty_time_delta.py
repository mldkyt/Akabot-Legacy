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

from utils.generic import pretty_time_delta

for no_seconds in [True, False]:
    for no_minutes in [True, False]:
        delta_1 = pretty_time_delta(59, 0, 0, show_seconds=no_seconds, show_minutes=no_minutes)
        print(f"show_seconds={no_seconds}, show_minutes={no_minutes}: {delta_1}")

        delta_2 = pretty_time_delta(60, 0, 0, show_seconds=no_seconds, show_minutes=no_minutes)
        print(f"show_seconds={no_seconds}, show_minutes={no_minutes}: {delta_2}")

        delta_3 = pretty_time_delta(3599, 0, 0, show_seconds=no_seconds, show_minutes=no_minutes)
        print(f"show_seconds={no_seconds}, show_minutes={no_minutes}: {delta_3}")

        delta_4 = pretty_time_delta(3600, 0, 0, show_seconds=no_seconds, show_minutes=no_minutes)
        print(f"show_seconds={no_seconds}, show_minutes={no_minutes}: {delta_4}")

        delta_5 = pretty_time_delta(86400, 0, 0, show_seconds=no_seconds, show_minutes=no_minutes)
        print(f"show_seconds={no_seconds}, show_minutes={no_minutes}: {delta_5}")
