"""Fun commands powered by free public APIs.

Uses aiohttp (bundled with discord.py). Each command defers its response
because a network call can take longer than Discord's 3-second reply window,
and each one fails gracefully if the upstream API is unavailable.
"""

import logging

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

log = logging.getLogger("bot")

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=10)


class Api(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.session: aiohttp.ClientSession | None = None

    async def cog_load(self) -> None:
        # icanhazdadjoke requires a User-Agent and a JSON Accept header.
        self.session = aiohttp.ClientSession(
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": "discord-bot (https://github.com/)", "Accept": "application/json"},
        )

    async def cog_unload(self) -> None:
        if self.session:
            await self.session.close()

    async def _get_json(self, url: str) -> dict | list | None:
        """GET a URL and return parsed JSON, or None on any failure."""
        assert self.session is not None
        try:
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    log.warning("API %s returned status %s", url, resp.status)
                    return None
                return await resp.json()
        except Exception:
            log.exception("Request to %s failed", url)
            return None

    @staticmethod
    async def _fail(interaction: discord.Interaction) -> None:
        await interaction.followup.send(
            "😴 That service is napping right now — try again in a bit."
        )

    @app_commands.command(name="joke", description="Get a random joke.")
    async def joke(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        data = await self._get_json("https://official-joke-api.appspot.com/random_joke")
        if not isinstance(data, dict) or "setup" not in data:
            await self._fail(interaction)
            return
        await interaction.followup.send(f"{data['setup']}\n\n||{data['punchline']}||")

    @app_commands.command(name="dadjoke", description="Get a random dad joke.")
    async def dadjoke(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        data = await self._get_json("https://icanhazdadjoke.com/")
        if not isinstance(data, dict) or "joke" not in data:
            await self._fail(interaction)
            return
        await interaction.followup.send(f"👨 {data['joke']}")

    @app_commands.command(name="meme", description="Get a random meme from Reddit.")
    async def meme(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        data = await self._get_json("https://meme-api.com/gimme")
        if not isinstance(data, dict) or "url" not in data:
            await self._fail(interaction)
            return
        embed = discord.Embed(title=data.get("title", "Meme"), url=data.get("postLink"))
        embed.set_image(url=data["url"])
        sub = data.get("subreddit")
        if sub:
            embed.set_footer(text=f"r/{sub}")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="cat", description="Get a random cat picture.")
    async def cat(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        data = await self._get_json("https://api.thecatapi.com/v1/images/search")
        if not isinstance(data, list) or not data or "url" not in data[0]:
            await self._fail(interaction)
            return
        embed = discord.Embed(title="🐱 Meow")
        embed.set_image(url=data[0]["url"])
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="dog", description="Get a random dog picture.")
    async def dog(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        data = await self._get_json("https://dog.ceo/api/breeds/image/random")
        if not isinstance(data, dict) or data.get("status") != "success":
            await self._fail(interaction)
            return
        embed = discord.Embed(title="🐶 Woof")
        embed.set_image(url=data["message"])
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Api(bot))
