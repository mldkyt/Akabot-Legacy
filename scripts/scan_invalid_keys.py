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
import os
import re


def get_files(path: str) -> list[str]:
    # Get list of .py files, recursively in directories

    files = []
    for root, _, filenames in os.walk(path):
        for filename in filenames:
            if filename.endswith('.py'):
                files.append(os.path.join(root, filename))

    return files


if __name__ == '__main__':
    print("Scanning for invalid translation keys...")

    with open("../lang/en.json", "r") as f:
        translations = json.load(f)

    files = get_files("../")

    used_keys = []
    for i in files:
        with open(i, "r", encoding='utf8') as f:
            content = f.read()

        for j in re.findall('trl[(](.*?), (.*?), "(.*?)"[)]', content):
            used_keys.append(j[2])

    invalid_keys = []
    for i in used_keys:
        if i not in translations:
            invalid_keys.append(i)

    print("Invalid keys:", invalid_keys)
