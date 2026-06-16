"""Webcomic commands.

xkcd has an official JSON API; the rest are pulled from each comic's public
RSS feed, where the strip image lives in the item's HTML. These are all
freely-syndicated webcomics — no scraping of paywalled newspaper strips.
"""

import html
import logging
import re

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

log = logging.getLogger("bot")

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=10)


class Comics(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.session: aiohttp.ClientSession | None = None

    async def cog_load(self) -> None:
        self.session = aiohttp.ClientSession(
            timeout=REQUEST_TIMEOUT,
            headers={"User-Agent": "discord-bot (https://github.com/)"},
        )

    async def cog_unload(self) -> None:
        if self.session:
            await self.session.close()

    async def _get_json(self, url: str) -> dict | None:
        assert self.session is not None
        try:
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    log.warning("Comic API %s returned %s", url, resp.status)
                    return None
                return await resp.json(content_type=None)
        except Exception:
            log.exception("Request to %s failed", url)
            return None

    async def _get_text(self, url: str) -> str | None:
        assert self.session is not None
        try:
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    log.warning("Comic feed %s returned %s", url, resp.status)
                    return None
                return await resp.text()
        except Exception:
            log.exception("Request to %s failed", url)
            return None

    @staticmethod
    async def _fail(interaction: discord.Interaction) -> None:
        await interaction.followup.send(
            "😴 That comic is napping right now — try again in a bit."
        )

    async def _latest_from_rss(
        self, url: str, prefer: str | None = None
    ) -> tuple[str, str, str | None] | None:
        """Return (title, image_url, link) for the newest item in an RSS feed.

        Images live in the item's (often HTML-escaped) body. ``prefer`` picks
        the first image whose URL contains that substring — useful when a feed
        also embeds layout/avatar images alongside the strip.
        """
        text = await self._get_text(url)
        if not text:
            return None
        item_match = re.search(r"<item>(.*?)</item>", text, re.S)
        if not item_match:
            return None
        item = item_match.group(1)

        body = html.unescape(item)
        images = re.findall(r"<img[^>]*src=[\"']([^\"']+)", body)
        if prefer:
            images = [i for i in images if prefer in i] or images
        if not images:
            return None

        title_match = re.search(r"<title>(.*?)</title>", item, re.S)
        title = title_match.group(1) if title_match else "Comic"
        title = re.sub(r"^\s*<!\[CDATA\[|\]\]>\s*$", "", title)
        title = html.unescape(title).strip()

        link_match = re.search(r"<link>(.*?)</link>", item, re.S)
        link = link_match.group(1).strip() if link_match else None
        return title or "Comic", images[0], link

    async def _send_rss(
        self,
        interaction: discord.Interaction,
        url: str,
        prefer: str | None = None,
    ) -> None:
        await interaction.response.defer()
        result = await self._latest_from_rss(url, prefer)
        if result is None:
            await self._fail(interaction)
            return
        title, image, link = result
        embed = discord.Embed(title=title[:256], url=link)
        embed.set_image(url=image)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="xkcd", description="Get an xkcd comic.")
    @app_commands.describe(number="Comic number (leave blank for the latest)")
    async def xkcd(
        self, interaction: discord.Interaction, number: int | None = None
    ) -> None:
        await interaction.response.defer()
        url = (
            f"https://xkcd.com/{number}/info.0.json"
            if number
            else "https://xkcd.com/info.0.json"
        )
        data = await self._get_json(url)
        if not isinstance(data, dict) or "img" not in data:
            await interaction.followup.send("❓ Couldn't find that comic.")
            return
        embed = discord.Embed(
            title=f"#{data['num']}: {data['title']}",
            url=f"https://xkcd.com/{data['num']}",
        )
        embed.set_image(url=data["img"])
        if data.get("alt"):
            embed.set_footer(text=data["alt"][:2000])
        await interaction.followup.send(embed=embed)

    @app_commands.command(
        name="smbc", description="Get the latest Saturday Morning Breakfast Cereal."
    )
    async def smbc(self, interaction: discord.Interaction) -> None:
        await self._send_rss(
            interaction, "https://www.smbc-comics.com/comic/rss", prefer="/comics/"
        )

    @app_commands.command(
        name="dinosaur", description="Get the latest Dinosaur Comics strip."
    )
    async def dinosaur(self, interaction: discord.Interaction) -> None:
        await self._send_rss(
            interaction, "https://www.qwantz.com/rssfeed.php", prefer="/comics/"
        )

    @app_commands.command(
        name="poorlydrawnlines", description="Get the latest Poorly Drawn Lines comic."
    )
    async def poorlydrawnlines(self, interaction: discord.Interaction) -> None:
        await self._send_rss(
            interaction, "https://poorlydrawnlines.com/feed/", prefer="/uploads/"
        )

    @app_commands.command(
        name="savagechickens", description="Get the latest Savage Chickens cartoon."
    )
    async def savagechickens(self, interaction: discord.Interaction) -> None:
        await self._send_rss(
            interaction, "https://www.savagechickens.com/feed", prefer="/uploads/"
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Comics(bot))
