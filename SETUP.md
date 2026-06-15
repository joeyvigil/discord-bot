# Discord Bot (discord.py starter)

Add the bot to your server:
https://discord.com/oauth2/authorize?client_id=1516042370439839784

A minimal Discord bot built with [discord.py](https://discordpy.readthedocs.io/),
using **slash commands** (no privileged intents required to start).

## Commands

| Command | What it does |
|---------|--------------|
| `/ping` | Replies with "Pong!" and the bot's latency |
| `/echo <message>` | Repeats your message back |

## Setup

### 1. Create the bot application

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications) → **New Application**.
2. Open the **Bot** tab → **Reset Token** → copy the token.
3. (Optional) Leave all **Privileged Gateway Intents** OFF — this starter only uses slash commands.

### 2. Invite the bot to your server

In the portal: **OAuth2 → URL Generator**, select scopes:

- `bot`
- `applications.commands`

Pick the permissions you need (for this starter, **Send Messages** is enough),
then open the generated URL and add the bot to a server you manage.

### 3. Install and configure locally

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env             # then edit .env and paste your token
```

For development, set `DEV_GUILD_ID` in `.env` to your server's ID so commands
appear instantly. (Enable Developer Mode in Discord → right-click your server →
Copy Server ID.) Leave it blank to register commands globally.

### 4. Run

```bash
python bot.py
```

You should see `Logged in as ...` in the console. Try `/ping` in your server.

## Adding a command

```python
@client.tree.command(name="hello", description="Say hello.")
async def hello(interaction: discord.Interaction) -> None:
    await interaction.response.send_message(f"Hi {interaction.user.mention}!")
```

Restart the bot after adding or changing commands so they re-sync.

## Notes

- **Never commit `.env`** — it holds your token. It's already in `.gitignore`.
- If you later read message text, run prefix commands, or track members, enable
  the matching **intent** both in `bot.py` and in the Developer Portal.
