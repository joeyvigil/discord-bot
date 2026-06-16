# joey-bot

A friendly little Discord bot built with [discord.py](https://discordpy.readthedocs.io/)
using slash commands. It brings games, randomizers, handy utilities, and fun
API-powered toys to your server — no privileged intents required.

## ➕ Add it to your server

**[Click here to invite joey-bot](https://discord.com/oauth2/authorize?client_id=1516042370439839784)**

Once it's in, type `/` in any channel to see everything it can do, or run `/help`.

## Commands

### 🎲 Fun & Games
| Command | What it does |
|---------|--------------|
| `/8ball <question>` | Ask the magic 8-ball a yes/no question |
| `/roll [dice]` | Roll dice in `NdM` format, e.g. `2d6` or `d20` |
| `/coinflip` | Flip a coin |
| `/choose <options>` | Pick one from a comma-separated list |
| `/rps <choice>` | Play rock-paper-scissors against the bot |
| `/ship <a> <b>` | Calculate the love compatibility of two people |
| `/rate <thing>` | Get the bot's official rating of anything |
| `/computa <command>` | Give the computa a command and it gets done |

### 🕹️ Interactive
| Command | What it does |
|---------|--------------|
| `/poll <question> <options>` | Create a live button poll (2–5 options) |
| `/trivia` | Answer a multiple-choice trivia question |
| `/tictactoe <opponent>` | Challenge someone to tic-tac-toe |
| `/embed` | Build a custom embed from a form |

### 🔤 Text
| Command | What it does |
|---------|--------------|
| `/mock <text>` | sPoNgEbOb-cAsE some text |
| `/clap <text>` | Put 👏 claps 👏 between words |
| `/owoify <text>` | Twanslate text into owo-speak |
| `/vaporwave <text>` | Convert text to ｆｕｌｌ-ｗｉｄｔｈ |
| `/leet <text>` | Convert text to l33t speak |
| `/emojify <text>` | Spell text with emoji letters |
| `/ascii <text>` | Render text as a big ASCII banner |

### 🌐 Web & Lookups
| Command | What it does |
|---------|--------------|
| `/joke` | A random joke |
| `/dadjoke` | A random dad joke |
| `/meme` | A random meme from Reddit |
| `/cat` | A random cat picture |
| `/dog` | A random dog picture |
| `/fox` | A random fox picture |
| `/duck` | A random duck picture |
| `/fact` | A random useless fact |
| `/advice` | A random piece of advice |
| `/quote` | An inspirational quote |
| `/bored` | Something to do when you're bored |
| `/insult` | A (playful) random insult |
| `/weather <city>` | Current weather for a city |
| `/define <word>` | Dictionary definition of a word |
| `/pokemon <name>` | Look up a Pokémon's stats |
| `/urban <term>` | Urban Dictionary lookup |
| `/wiki <term>` | Get a Wikipedia summary |
| `/github <owner/repo>` | Look up a GitHub repository |
| `/npm <package>` | Look up an npm package |
| `/crypto <coin>` | Get a cryptocurrency price |
| `/translate <text> [to]` | Translate text to another language |

### 📰 Comics
| Command | What it does |
|---------|--------------|
| `/xkcd [number]` | Get an xkcd comic |
| `/smbc` | Latest Saturday Morning Breakfast Cereal |
| `/dinosaur` | Latest Dinosaur Comics strip |
| `/poorlydrawnlines` | Latest Poorly Drawn Lines comic |
| `/savagechickens` | Latest Savage Chickens cartoon |
| `/warandpeas` | Latest War and Peas comic |
| `/pbf` | Latest Perry Bible Fellowship comic |
| `/buttersafe` | Latest Buttersafe comic |
| `/exocomics` | Latest Exocomics comic |
| `/loadingartist` | Latest Loading Artist comic |

### 🧰 Utility
| Command | What it does |
|---------|--------------|
| `/avatar [user]` | Show a user's avatar |
| `/userinfo [user]` | Show info about a user |
| `/serverinfo` | Show info about this server |
| `/membercount` | Show the server's member count |
| `/snowflake <id>` | Decode the creation date of a Discord ID |
| `/roleinfo <role>` | Show info about a role |
| `/channelinfo [channel]` | Show info about a channel |
| `/emojiinfo <emoji>` | Show info about a custom emoji |
| `/servericon` | Show this server's icon |
| `/banner [user]` | Show a user's profile banner |
| `/firstmessage [channel]` | Link to the first message in a channel |
| `/calc <expression>` | Evaluate a math expression |
| `/convert <value> <from> <to>` | Convert units (length, mass, volume, temp) |
| `/base <number> <from> <to>` | Convert a number between bases (2–36) |
| `/random <min> <max>` | Pick a random number in a range |
| `/percent <x> <y>` | What percent is X of Y |
| `/tip <bill> [percent] [split]` | Calculate a tip and optional split |
| `/url <mode> <text>` | URL-encode or decode text |
| `/base64 <mode> <text>` | Encode or decode base64 |
| `/morse <mode> <text>` | Translate to or from Morse code |
| `/binary <mode> <text>` | Convert text to or from binary |
| `/hash <algorithm> <text>` | Hash text (MD5, SHA-1/256/512) |
| `/case <style> <text>` | Change the case of text |
| `/reverse <text>` | Reverse a string |
| `/wordcount <text>` | Count characters, words, and lines |
| `/uuid` | Generate a random UUID |
| `/password [length]` | Generate a secure random password |
| `/qr <text>` | Generate a QR code |
| `/colorinfo <hex>` | Show details for a hex color |
| `/event <title> <when>` | Announce an event in everyone's local time |
| `/timestamp [when]` | Generate Discord timestamp codes |
| `/countdown <when>` | Show a live countdown to a time |
| `/timein <offset>` | Current time at a UTC offset |
| `/unixtime` | Show the current Unix timestamp |
| `/remindme <when> <text>` | Get pinged after a delay |
| `/say <text>` | Make the bot say something |

### ⚙️ General
| Command | What it does |
|---------|--------------|
| `/ping` | Check if the bot is alive and see its latency |
| `/echo <message>` | Repeat back what you say |
| `/help [category]` | Compact command overview, or one section in detail |

## Running your own

Want to host your own copy? See **[SETUP.md](SETUP.md)** for setup, configuration,
and deployment instructions.
