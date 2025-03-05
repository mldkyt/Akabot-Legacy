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

import random


def verify_english_word(word: str) -> bool:
    with open("data/words.txt") as f:
        text_file = f.read().splitlines()

    for i in text_file:
        if i == word:
            return True

    return False


def get_random_english_word() -> str:
    with open("data/words.txt") as f:
        text_file = f.read().splitlines()

    return random.choice(text_file)


def get_random_english_word_range(min_length: int, max_length: int) -> str | None:
    with open("data/words.txt") as f:
        text_file = f.read().splitlines()

    i = 0
    while True:
        i += 1
        word = random.choice(text_file)
        if min_length <= len(word) <= max_length:
            return word

        if i > 10000:
            return None


def scramble_word(word):
    # If word is too short to scwambwe, wetuwn it as it is >w<
    if len(word) <= 3:
        return word

    # Keep the fiwst and wast wetters in pwace
    middle = list(word[1:-1])
    random.shuffle(middle)
    return word[0] + ''.join(middle) + word[-1]
