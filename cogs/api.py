"""Fun commands powered by free public APIs.

Uses aiohttp (bundled with discord.py). Each command defers its response
because a network call can take longer than Discord's 3-second reply window,
and each one fails gracefully if the upstream API is unavailable.
"""

import logging
from urllib.parse import quote

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
        """GET a URL and return parsed JSON, or None on any failure.

        Some APIs (e.g. adviceslip) reply with a non-JSON content type, so we
        pass content_type=None to parse the body regardless of the header.
        """
        assert self.session is not None
        try:
            async with self.session.get(url) as resp:
                if resp.status != 200:
                    log.warning("API %s returned status %s", url, resp.status)
                    return None
                return await resp.json(content_type=None)
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

    # --- Random text ---------------------------------------------------------

    @app_commands.command(name="fact", description="Get a random useless fact.")
    async def fact(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        data = await self._get_json("https://uselessfacts.jsph.pl/api/v2/facts/random")
        if not isinstance(data, dict) or "text" not in data:
            await self._fail(interaction)
            return
        await interaction.followup.send(f"💡 {data['text']}")

    @app_commands.command(name="advice", description="Get a random piece of advice.")
    async def advice(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        data = await self._get_json("https://api.adviceslip.com/advice")
        if not isinstance(data, dict) or "slip" not in data:
            await self._fail(interaction)
            return
        await interaction.followup.send(f"🧠 {data['slip']['advice']}")

    @app_commands.command(name="quote", description="Get an inspirational quote.")
    async def quote(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        data = await self._get_json("https://zenquotes.io/api/random")
        if not isinstance(data, list) or not data or "q" not in data[0]:
            await self._fail(interaction)
            return
        await interaction.followup.send(f"💬 *{data[0]['q']}*\n— **{data[0]['a']}**")

    @app_commands.command(name="bored", description="Get something to do when you're bored.")
    async def bored(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        data = await self._get_json("https://bored-api.appbrewery.com/random")
        if not isinstance(data, dict) or "activity" not in data:
            await self._fail(interaction)
            return
        await interaction.followup.send(f"🎯 {data['activity']}")

    @app_commands.command(name="insult", description="Get a (playful) random insult.")
    async def insult(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        data = await self._get_json(
            "https://evilinsult.com/generate_insult.php?lang=en&type=json"
        )
        if not isinstance(data, dict) or "insult" not in data:
            await self._fail(interaction)
            return
        await interaction.followup.send(f"😈 {data['insult']}")

    # --- Random images -------------------------------------------------------

    @app_commands.command(name="fox", description="Get a random fox picture.")
    async def fox(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        data = await self._get_json("https://randomfox.ca/floof/")
        if not isinstance(data, dict) or "image" not in data:
            await self._fail(interaction)
            return
        embed = discord.Embed(title="🦊 What does the fox say?")
        embed.set_image(url=data["image"])
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="duck", description="Get a random duck picture.")
    async def duck(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        data = await self._get_json("https://random-d.uk/api/random")
        if not isinstance(data, dict) or "url" not in data:
            await self._fail(interaction)
            return
        embed = discord.Embed(title="🦆 Quack")
        embed.set_image(url=data["url"])
        await interaction.followup.send(embed=embed)

    # --- With arguments ------------------------------------------------------

    @app_commands.command(name="weather", description="Get the current weather for a city.")
    @app_commands.describe(city="City name, e.g. London or New York")
    async def weather(self, interaction: discord.Interaction, city: str) -> None:
        await interaction.response.defer()
        url = f"https://wttr.in/{quote(city)}?format=j1"
        data = await self._get_json(url)
        if not isinstance(data, dict) or not data.get("current_condition"):
            await self._fail(interaction)
            return
        current = data["current_condition"][0]
        area = data.get("nearest_area", [{}])[0]
        name = area.get("areaName", [{}])[0].get("value", city)
        country = area.get("country", [{}])[0].get("value", "")
        desc = current.get("weatherDesc", [{}])[0].get("value", "—")
        location = f"{name}, {country}" if country else name

        embed = discord.Embed(title=f"🌤️ Weather in {location}", description=desc)
        embed.add_field(
            name="Temperature",
            value=f"{current['temp_C']}°C / {current['temp_F']}°F",
        )
        embed.add_field(
            name="Feels like",
            value=f"{current['FeelsLikeC']}°C / {current['FeelsLikeF']}°F",
        )
        embed.add_field(name="Humidity", value=f"{current['humidity']}%")
        embed.add_field(name="Wind", value=f"{current['windspeedKmph']} km/h")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="define", description="Look up the definition of a word.")
    @app_commands.describe(word="The word to define")
    async def define(self, interaction: discord.Interaction, word: str) -> None:
        await interaction.response.defer()
        url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{quote(word.strip())}"
        data = await self._get_json(url)
        if not isinstance(data, list) or not data or "meanings" not in data[0]:
            await interaction.followup.send(f"📖 No definition found for **{word}**.")
            return
        entry = data[0]
        embed = discord.Embed(
            title=f"📖 {entry.get('word', word)}",
            description=entry.get("phonetic", ""),
        )
        # Show up to three parts of speech, first definition of each.
        for meaning in entry["meanings"][:3]:
            pos = meaning.get("partOfSpeech", "")
            defs = meaning.get("definitions", [])
            if defs:
                embed.add_field(
                    name=pos or "definition",
                    value=defs[0].get("definition", "—"),
                    inline=False,
                )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="pokemon", description="Look up a Pokémon's stats.")
    @app_commands.describe(name="Pokémon name or number, e.g. pikachu or 25")
    async def pokemon(self, interaction: discord.Interaction, name: str) -> None:
        await interaction.response.defer()
        url = f"https://pokeapi.co/api/v2/pokemon/{quote(name.strip().lower())}"
        data = await self._get_json(url)
        if not isinstance(data, dict) or "stats" not in data:
            await interaction.followup.send(f"❓ Couldn't find a Pokémon called **{name}**.")
            return

        types = ", ".join(t["type"]["name"].title() for t in data["types"])
        stats = "\n".join(
            f"{s['stat']['name'].replace('-', ' ').title()}: **{s['base_stat']}**"
            for s in data["stats"]
        )
        embed = discord.Embed(
            title=f"#{data['id']} {data['name'].title()}",
            description=f"**Type:** {types}",
        )
        # height is in decimetres, weight in hectograms.
        embed.add_field(name="Height", value=f"{data['height'] / 10:g} m")
        embed.add_field(name="Weight", value=f"{data['weight'] / 10:g} kg")
        embed.add_field(name="Base stats", value=stats, inline=False)
        art = data.get("sprites", {}).get("other", {}).get("official-artwork", {}).get("front_default")
        if art:
            embed.set_thumbnail(url=art)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="urban", description="Look up a term on Urban Dictionary.")
    @app_commands.describe(term="The term to look up")
    async def urban(self, interaction: discord.Interaction, term: str) -> None:
        await interaction.response.defer()
        url = f"https://api.urbandictionary.com/v0/define?term={quote(term.strip())}"
        data = await self._get_json(url)
        entries = data.get("list") if isinstance(data, dict) else None
        if not entries:
            await interaction.followup.send(f"🤷 No Urban Dictionary entry for **{term}**.")
            return
        top = entries[0]
        # Urban Dictionary wraps cross-referenced terms in [brackets]; drop them.
        definition = top["definition"].replace("[", "").replace("]", "")
        embed = discord.Embed(
            title=f"📚 {top['word']}",
            url=top.get("permalink"),
            description=definition[:1000],
        )
        example = top.get("example", "").replace("[", "").replace("]", "").strip()
        if example:
            embed.add_field(name="Example", value=example[:1000], inline=False)
        embed.set_footer(
            text=f"👍 {top.get('thumbs_up', 0)}  👎 {top.get('thumbs_down', 0)}"
        )
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="wiki", description="Get a Wikipedia summary.")
    @app_commands.describe(term="What to look up")
    async def wiki(self, interaction: discord.Interaction, term: str) -> None:
        await interaction.response.defer()
        title = quote(term.strip().replace(" ", "_"))
        data = await self._get_json(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
        )
        if not isinstance(data, dict) or not data.get("extract"):
            await interaction.followup.send(
                f"📚 No Wikipedia article found for **{term}**."
            )
            return
        embed = discord.Embed(
            title=data.get("title", term),
            description=data["extract"][:1500],
            url=data.get("content_urls", {}).get("desktop", {}).get("page"),
        )
        thumb = data.get("thumbnail", {}).get("source")
        if thumb:
            embed.set_thumbnail(url=thumb)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="github", description="Look up a GitHub repository.")
    @app_commands.describe(repo="owner/repo, e.g. python/cpython")
    async def github(self, interaction: discord.Interaction, repo: str) -> None:
        await interaction.response.defer()
        slug = repo.strip().strip("/")
        if slug.count("/") != 1:
            await interaction.followup.send(
                "❌ Use `owner/repo`, e.g. `python/cpython`."
            )
            return
        data = await self._get_json(f"https://api.github.com/repos/{quote(slug)}")
        if not isinstance(data, dict) or "full_name" not in data:
            await interaction.followup.send(f"❓ Couldn't find repo **{slug}**.")
            return
        embed = discord.Embed(
            title=data["full_name"],
            description=data.get("description") or "",
            url=data.get("html_url"),
        )
        embed.add_field(name="⭐ Stars", value=f"{data.get('stargazers_count', 0):,}")
        embed.add_field(name="🍴 Forks", value=f"{data.get('forks_count', 0):,}")
        embed.add_field(
            name="🐛 Open issues", value=f"{data.get('open_issues_count', 0):,}"
        )
        if data.get("language"):
            embed.add_field(name="Language", value=data["language"])
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="npm", description="Look up an npm package.")
    @app_commands.describe(package="Package name, e.g. discord.js")
    async def npm(self, interaction: discord.Interaction, package: str) -> None:
        await interaction.response.defer()
        name = package.strip()
        data = await self._get_json(
            f"https://registry.npmjs.org/{quote(name, safe='@/')}/latest"
        )
        if not isinstance(data, dict) or "name" not in data:
            await interaction.followup.send(f"❓ Couldn't find npm package **{name}**.")
            return
        embed = discord.Embed(
            title=f"📦 {data['name']} v{data.get('version', '?')}",
            description=data.get("description") or "",
            url=data.get("homepage") or f"https://www.npmjs.com/package/{name}",
        )
        license_ = data.get("license")
        if isinstance(license_, dict):
            license_ = license_.get("type")
        if license_:
            embed.add_field(name="License", value=str(license_))
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="crypto", description="Get a cryptocurrency price.")
    @app_commands.describe(coin="Coin id, e.g. bitcoin, ethereum, dogecoin")
    async def crypto(self, interaction: discord.Interaction, coin: str) -> None:
        await interaction.response.defer()
        cid = quote(coin.strip().lower())
        data = await self._get_json(
            "https://api.coingecko.com/api/v3/simple/price"
            f"?ids={cid}&vs_currencies=usd&include_24hr_change=true"
        )
        if not isinstance(data, dict) or not data:
            await interaction.followup.send(
                f"❓ Couldn't find **{coin}** — try the full id, e.g. `bitcoin`."
            )
            return
        key = next(iter(data))
        info = data[key]
        change = info.get("usd_24h_change") or 0
        arrow = "📈" if change >= 0 else "📉"
        await interaction.followup.send(
            f"💰 **{key.title()}**: ${info.get('usd'):,} USD  "
            f"{arrow} {change:+.2f}% (24h)"
        )

    @app_commands.command(name="translate", description="Translate text to another language.")
    @app_commands.describe(text="Text to translate", to="Target language code (default: en)")
    async def translate(
        self, interaction: discord.Interaction, text: str, to: str = "en"
    ) -> None:
        await interaction.response.defer()
        target = quote(to.strip() or "en")
        data = await self._get_json(
            "https://translate.googleapis.com/translate_a/single"
            f"?client=gtx&sl=auto&tl={target}&dt=t&q={quote(text)}"
        )
        if not isinstance(data, list) or not data or not data[0]:
            await self._fail(interaction)
            return
        translated = "".join(chunk[0] for chunk in data[0] if chunk and chunk[0])
        source = data[2] if len(data) > 2 else "auto"
        embed = discord.Embed(title="🌐 Translation", color=discord.Color.blue())
        embed.add_field(name=f"From ({source})", value=text[:1000], inline=False)
        embed.add_field(name=f"To ({to})", value=translated[:1000], inline=False)
        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Api(bot))
