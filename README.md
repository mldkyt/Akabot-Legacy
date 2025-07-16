# Akabot

[![Discord](https://img.shields.io/discord/1217145199151681656?label=support%20Discord%20server)
](https://discord.gg/YFksXpXnn6)
[![Gitea Issues](https://img.shields.io/gitea/issues/open/Lunya/Akabot?gitea_url=https%3A%2F%2Fgit.lunya.pet)
](https://git.lunya.pet/Lunya/Akabot/issues)
[![Gitea Pull Requests](https://img.shields.io/gitea/pull-requests/open/Lunya/Akabot?gitea_url=https%3A%2F%2Fgit.lunya.pet)
](https://git.lunya.pet/Lunya/Akabot/pulls)
[![Gitea Release](https://img.shields.io/gitea/v/release/Lunya/Akabot?gitea_url=https%3A%2F%2Fgit.lunya.pet%2F)
](https://git.lunya.pet/Lunya/Akabot/releases)


Akabot is a Discord bot that's made to be customizable and has a lot of features. It's made with Python and uses the
`py-cord` library.

## Features

- Anti Raid - The Antiraid module prevents way too many joins in a
  short period of time.
- Automod Actions - Create automod actions for specific rules
  executing specific actions and perform tasks when a member triggers an automod rule.
- Anonymous Quefessions - Have people send you anonymous quefessions in your Discord server, with moderation abilities.
- Auto React - React to messages automatically on a keyword.
- Auto Response - Respond with a message automatically on a keyword.
- Chat Revive - The Chat Revive commands revives commands if
  there's no seen activity for a set period of time.
- Chat Streaks - The Chat Streaks module counts how many days
  you've sent a message consecutively in a Discord server.
- Chat Summary - The chat summary module counts messages and then
  sends a message at the end of the day.
- Economy - This module introduces an economy system to Akabot, allowing users to earn, spend, and manage virtual currency within their Discord server. 
- Giveaways - The Giveaways module allows server administrators to
  create and manage giveaways directly within their Discord server.
- Heartbeat - Configure the bot to send messages to another server on intervals to let the server know it's alive and
  online.
- Help - Get help with the bot directly from the bot! Will direct you to a wiki anyone can contribute to.
- Leveling - The Leveling module allows server administrators to
  implement and manage a leveling system within their Discord server.
- Logging - This module adds logging for a Discord server. It sends
  events into a logging channel.
- Message Time Capsule - This module allows users to schedule messages, reminders, and collection messages in Discord servers and DMs. 
- Moderation - This module provides commands to perform moderation
  actions such as kicking, banning, timing out, and removing timeouts for users in a Discord server.
- Reaction Roles - This module allows users to assign or remove
  roles by reacting to messages containing specific buttons. It provides commands to create different types of reaction
  role setups, such as normal, add-only, remove-only, and single-choice reaction roles.
- Roles on Join - Give members roles immediately on join.
- Send Server Count - Admins can configure the bot to send messages to top.gg and various other sites to update the
  server count.
- Suggestions - Akabot accepts suggestions directly from the bot! Using the public instance `/suggest` command will
  create issues here.
- Statistics Channels - Channels that display various server statistics.
- Temporary Voice Channels - Create as many voice channels in your Discord server without needing to ask admins to
  create them for you.
- Tickets - Handle tickets in your Discord server. Let members open tickets, get help and close tickets. Comes with an
  auto close feature and archive feature.
- Verification - This module adds user verification in Discord
  servers. It prevents bots from accessing your Discord server.
- Welcome and Goodbye messages - Welcome new members, and say goodbye to the ones who leave.
- Word Scramble - Scrambles random English words or words from
  previous messagse in chat and lets your members unscramble them for extra rewards in the leveling system.

## Available Public Instances

There is a public instance of Akabot you can invite.

The recommended instance is the last stable version of Akabot. This instance is more stable and receives bug fixes added
in the next stable version. This version is always made sure to be stable and
secure.

This bot instance can be invited using [this link](https://discord.com/oauth2/authorize?client_id=1172922944033411243).
A [terms of service](https://lunya.pet/project/akabot/tos)
and [privacy policy](https://lunya.pet/project/akabot/privacy) apply.

## Self-Hosting an instance of your own

1. Clone this repository
2. Build the Docker image from the Dockerfile located in the root of the project, using `docker build -t akabot:latest`
3. Set the environment variables `DB_USERNAME`, `DB_PASSWORD`, `DB_HOST`, `BOT_VERSION` and `BOT_TOKEN` for the bare functionality of the bot. The bot uses a MongoDB database.
4. Start the Docker container.

## Contributing to Akabot

You can check the [CONTRIBUTING.md](CONTRIBUTING.md) file for more information on how to contribute to the bot.

## Developer Contact

- Mastodon: [@Akabot@fedi.lunya.pet](https://fedi.lunya.pet/@akabot) - You can follow this account to receive updated about
  Akabot. Additionally, you can ask here for help!
- Developer's account: [@Lunya@fedi.lunya.pet](https://fedi.lunya.pet/) - You can ask here for help. I check fedi
  as one of the few social media and I'll respond.
- E-mail: [lunya.pet@proton.me](mailto:lunya.pet@proton.me) - I respond quickly here. Please make sure your e-mail has a
  subject.

## Setting up a development environment

1. Clone the repository
2. Switch to the next version branch if you're contributing a new feature or the default branch if you're contributing a
   bug fix.
3. Create a Python virtual environment using `python -m venv .venv`
4. Enable the virtual environment using `source .venv/bin/activate` on Linux or `.venv\Scripts\activate` on Windows
5. Install the dependencies using `pip install -r requirements.txt`
6. Copy `config.example.conf` to `config.conf` and fill in the necessary information
7. Run the bot using `python main.py` and restart it whenever you make changes to the code
8. Make your changes
9. Push your changes to your fork

### Auto restart on changes in code

1. To set up Auto-restart, install `nodemo` using `npm install -g nodemon`
2. Run the bot using `nodemon -e py --exec python main.py` and it will restart the bot whenever you make changes to the
   code
