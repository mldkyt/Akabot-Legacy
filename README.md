# Akabot

Akabot is a Discord bot that's made to be customizable and has a lot of features. It's made with Python and uses the
`py-cord` library.

## Features

Individual modules have their documentation listed below.

- [Anti Raid](https://wiki.mldchan.dev/index.php/Akabot#Anti_Raid) - The Antiraid module prevents way too many joins in a
  short period of time.
- [Automod Actions](https://wiki.mldchan.dev/index.php/Akabot#Automod_Actions) - Create automod actions for specific rules
  executing specific actions and perform tasks when a member triggers an automod rule.
- Anonymous Quefessions - Have people send you anonymous quefessions in your Discord server, with moderation abilities.
- Auto React - React to messages automatically on a keyword.
- Auto Response - Respond with a message automatically on a keyword.
- [Chat Revive](https://wiki.mldchan.dev/index.php/Akabot#Chat_Revive) - The Chat Revive commands revives commands if
  there's no seen activity for a set period of time.
- [Chat Streaks](https://wiki.mldchan.dev/index.php/Akabot#Chat_Streaks) - The Chat Streaks module counts how many days
  you've sent a message consecutively in a Discord server.
- [Chat Summary](https://wiki.mldchan.dev/index.php/Akabot#Chat_Summary) - The chat summary module counts messages and then
  sends a message at the end of the day.
- [Economy](https://wiki.mldchan.dev/index.php/Akabot#Economy_Module) - This module introduces an economy system to Akabot, allowing users to earn, spend, and manage virtual currency within their Discord server. 
- [Giveaways](https://wiki.mldchan.dev/index.php/Akabot#Giveaways) - The Giveaways module allows server administrators to
  create and manage giveaways directly within their Discord server.
- Heartbeat - Configure the bot to send messages to another server on intervals to let the server know it's alive and
  online.
- Help - Get help with the bot directly from the bot! Will direct you to a wiki anyone can contribute to.
- [Leveling](https://wiki.mldchan.dev/index.php/Akabot#Leveling) - The Leveling module allows server administrators to
  implement and manage a leveling system within their Discord server.
- [Logging](https://github.com/mldchan/Akabot/wiki/Logging) - This module adds logging for a Discord server. It sends
  events into a logging channel.
- [Message Time Capsule](https://wiki.mldchan.dev/index.php/Akabot#Message_Scheduler) - This module allows users to schedule messages, reminders, and collection messages in Discord servers and DMs. 
- [Moderation](https://wiki.mldchan.dev/index.php/Akabot#Moderation) - This module provides commands to perform moderation
  actions such as kicking, banning, timing out, and removing timeouts for users in a Discord server.
- [Reaction Roles](https://wiki.mldchan.dev/index.php/Akabot#Reaction_Roles) - This module allows users to assign or remove
  roles by reacting to messages containing specific buttons. It provides commands to create different types of reaction
  role setups, such as normal, add-only, remove-only, and single-choice reaction roles.
- Roles on Join - Give members roles immediately on join.
- Roleplay commands - When enabled by admins, allows you to roleplay with other members. Please ask for consent!
- Send Server Count - Admins can configure the bot to send messages to top.gg and various other sites to update the
  server count.
- Suggestions - Akabot accepts suggestions directly from the bot! Using the public instance `/suggest` command will
  create issues here.
- Statistics Channels - Channels that display various server statistics.
- Temporary Voice Channels - Create as many voice channels in your Discord server without needing to ask admins to
  create them for you.
- Tickets - Handle tickets in your Discord server. Let members open tickets, get help and close tickets. Comes with an
  auto close feature and archive feature.
- [Verification](https://wiki.mldchan.dev/index.php/Akabot#Verification) - This module adds user verification in Discord
  servers. It prevents bots from accessing your Discord server.
- Welcome and Goodbye messages - Welcome new members, and say goodbye to the ones who leave.
- [Word Scramble](https://github.com/mldchan/Akabot/wiki/Word-Scramble) - Scrambles random English words or words from
  previous messagse in chat and lets your members unscramble them for extra rewards in the leveling system.
- [Announcement Channels](https://wiki.mldchan.dev/index.php/Akabot#Announcement_Channels) 

## Available Public Instances

There are 2 public available instances of Akabot you can invite.

### 1. The recommended one

The recommended instance is the last stable version of Akabot. This instance is more stable and receives bug fixes added
in the next stable version. This version is always made sure to be stable and
secure.

This bot instance can be invited using [this link](https://discord.com/oauth2/authorize?client_id=1172922944033411243).
A [terms of service](https://mldchan.dev/project/akabot/tos)
and [privacy policy](https://mldchan.dev/project/akabot/privacy) apply.

### 2. Less recommended version (Beta)

The beta instance is the latest version of Akabot. This instance is less stable and may contain bugs. This version is
not recommended for production servers.

This bot instance can be invited using [this link](https://discord.com/oauth2/authorize?client_id=1256907946261090354).
A [terms of service](https://mldchan.dev/project/akabot/tos)
and [privacy policy](https://mldchan.dev/project/akabot/privacy) apply.

## Self-Hosting an instance of your own

### Docker

Setting up an instance with Docker is the easiest way to set Akabot up. It's platform independent so you can start it on
anything running Docker.

You can start configuring using this method [here](https://github.com/mldchan/Akabot/wiki/Self-Host-Using-Docker).

### Virtualenv

Setting up an instance with Virtualenv can be a bit more tricky, especially if the Python version is not compatible.

This method was only tested on Python 3.11 and 3.12. These versions are confirmed to be working on Windows and Linux.

You can start configuring using this method [here](https://github.com/mldchan/Akabot/wiki/Self-Host-Using-Virtualenv)

## Contributing to Akabot

You can check the [CONTRIBUTING.md](CONTRIBUTING.md) file for more information on how to contribute to the bot.

## Developer Contact

- Mastodon: [@Akabot@floss.social](https://floss.social/@akabot) - You can follow this account to receive updated about
  Akabot. Additionally, you can ask here for help!
- Developer's account: [@mld@social.mldchan.dev](https://social.mldchan.dev/) - You can ask here for help. I check fedi
  as one of the few social media and I'll respond.
- E-mail: [mldkyt@proton.me](mailto:mldkyt@proton.me) - I respond quickly here. Please make sure your e-mail has a
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
