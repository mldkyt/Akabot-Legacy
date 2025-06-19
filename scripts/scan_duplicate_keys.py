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

import json

if __name__ == '__main__':
    print("Scanning for duplicate translation keys...")

    with open("../lang/en.json", "r") as f:
        translations = json.load(f)

    duplicate_keys = []

    for key, value in translations.items():
        if list(translations.values()).count(value) > 1:
            duplicate_keys.append(key)

    print("Duplicate keys:", duplicate_keys)
