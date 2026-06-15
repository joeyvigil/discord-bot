"""A discord.py starter bot using slash commands, organized with cogs.

Run with: python bot.py

Commands live in the cogs/ folder. Each .py file there is loaded
automatically on startup, so adding a feature is just dropping in a new cog.
"""

import asyncio
import logging
import os
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
DEV_GUILD_ID = os.getenv("DEV_GUILD_ID")

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("bot")

COGS_DIR = Path(__file__).parent / "cogs"


class StarterBot(commands.Bot):
    def __init__(self) -> None:
        # Slash commands need no privileged intents, so the defaults are enough.
        # command_prefix is required by commands.Bot but unused here since we
        # only use slash commands; "!" is a harmless placeholder.
        super().__init__(command_prefix="!", intents=discord.Intents.default())

    async def setup_hook(self) -> None:
        # Load every cog in the cogs/ folder.
        for path in sorted(COGS_DIR.glob("*.py")):
            if path.stem == "__init__":
                continue
            extension = f"cogs.{path.stem}"
            try:
                await self.load_extension(extension)
                log.info("Loaded cog %s", extension)
            except Exception:
                log.exception("Failed to load cog %s", extension)

        # Sync slash commands. Syncing to a specific dev guild is near-instant;
        # global sync can take up to an hour to propagate.
        if DEV_GUILD_ID:
            guild = discord.Object(id=int(DEV_GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            synced = await self.tree.sync(guild=guild)
            log.info("Synced %d commands to dev guild %s", len(synced), DEV_GUILD_ID)
        else:
            synced = await self.tree.sync()
            log.info("Synced %d commands globally", len(synced))

    async def on_ready(self) -> None:
        log.info("Logged in as %s (id: %s)", self.user, self.user.id)


async def main() -> None:
    if not TOKEN:
        raise SystemExit(
            "DISCORD_TOKEN is not set. Copy .env.example to .env and add your bot token."
        )
    async with StarterBot() as bot:
        await bot.start(TOKEN)


if __name__ == "__main__":
    asyncio.run(main())
