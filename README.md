### Discord-TicketBot 📝
[![Version Badge](https://warehouse-camo.ingress.cmh1.psfhosted.org/e21c149917b21ef666e263301355bec38dc9cdc7/68747470733a2f2f696d672e736869656c64732e696f2f707970692f762f646973636f72642e70792e737667)](https://pypi.org/project/discord.py/)
- A discord bot that is designed to manage and create ticket channels on behalf of server members using the [Rapptz discord.py API](https://github.com/Rapptz/discord.py).
- Compilied on Python 3.8.1.  

---
### Screenshots

<p align="center"><img src="https://cdn.discordapp.com/attachments/825594967777869838/1106811576897503282/ticket-bot-demo.gif" /></p><p align="center"><img src="https://media.discordapp.net/attachments/828110039956455444/1107065883756605481/ezgif-5-164059f8ff.gif" /></p>

---
### Features
- Slash Commands and Interactions
- The ability to place Tickets in different categories depending on their status (Active, Onhold, Archived)
- Claim, Rename, Add, or Remove members from a ticket channel
- System-Logging
- Embedded Ticket Transcription Logs (using [chat-exporter](https://pypi.org/project/chat-exporter/))
- Customizable Embeds
- Customizable Ticket Options that members can select while creating tickets
- Complex ticket permission system that can be customized per ticket option
- Embedded "Create a ticket" button
- GUI-like Ticket Options menu
- A **/create** command that staff can use to manually create tickets
- Something else that I'm probably missing!

---
### [Python](https://www.python.org/downloads/) Packages Required (Install with [Pip](https://pip.pypa.io/en/stable/installing/)):
- [Discord](https://pypi.org/project/discord.py/)
- [chat-exporter](https://pypi.org/project/chat-exporter/)

---
### Setup
- Place all bot related files into a seperate folder (this is **important** to do so, or else the python compiler will not be able to find the bot files necessary for the ticket bot to work)
- Create a bot application at the [discord developer panel](https://discord.com/developers/applications) and enable all intents. 
- Add the bot to your discord server by generating a OAuth2 invite link for your application and make sure to enable **bot** and **apps.commands**. Then for the permissions, tick Administrator.
- Copy your bot token from the [discord developer panel](https://discord.com/developers/applications) under the bot tab and add it to the token.json file.
- Adjust the config.py file to your liking.
- Run the main.py file in python and the bot should start up. The bot will be fully running once the "Bot is up and running" message is outputted to the console.
- Run the **/sync** command in order to sync the bot's slash commands with discord.
- **ON FIRST RUN, THE BOT WILL EXIT PYTHON AUTOMATICALLY IN ORDER TO SAVE THE MESSAGE ID OF THE "CREATE A TICKET" EMBED IN THE BOT'S CONFIG.** Simply restart the bot again in order to apply the necessary config changes.

---
### Support
- Please open up a issue to report any bugs with the TicketBot.

---
### Known Errors
- Interaction fail on unknown slash command. (There is no error handling in the API for this yet, therefore a interaction fail will occur on the users side and a compiler error will be outputted to the console)

---
### Creators Note
- This bot is protected and licensed under the GNU General Public License v3.0. I am not liable for any damage that my bots may cause to your computer or discord server. I have the right to deny support for my bots at anytime for any reason. Even though this bot is open-sourced, it's source-code may be used for inspiration but may not be used for malicious intent.  

- This is the fourth iteration of this bot, all previous versions have been used in private closed environments and will not be released to the public. This is the first public version of this bot.

- I would like to say a huge thanks to my good friend [Reb](https://rebsdesigns.com/). Without him, this whole idea of me making a "Ticket Bot" for discord would of never been possible. Thank you for giving me the opportunity to make a bot for you in the first place, kickstarting my devving career.

- Thank you to my good friend [Jake](https://github.com/jfmcdavitt) who helped me setup some of the backend parts of the bot. Without him, I would still be pondering on how am I going to make some parts of this thing work.
