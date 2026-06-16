"""Text transformer commands. Self-contained — pure string manipulation."""

import random
import re

import discord
import pyfiglet
from discord import app_commands
from discord.ext import commands

# Keep outputs comfortably under Discord's 2000-char message limit.
MAX_INPUT = 400

_LEET = str.maketrans(
    {"a": "4", "b": "8", "e": "3", "g": "9", "i": "1", "o": "0", "s": "5", "t": "7"}
)
_KEYCAPS = {str(i): f"{i}\N{COMBINING ENCLOSING KEYCAP}" for i in range(10)}
_OWO_FACES = [" owo", " uwu", " >w<", " ^w^", " :3"]


def _mock(text: str) -> str:
    return "".join(c.upper() if random.random() < 0.5 else c.lower() for c in text)


def _owoify(text: str) -> str:
    text = re.sub(r"[rl]", "w", text)
    text = re.sub(r"[RL]", "W", text)
    text = re.sub(r"n([aeiou])", r"ny\1", text)
    text = re.sub(r"N([aeiou])", r"Ny\1", text)
    text = text.replace("ove", "uv")
    return text + random.choice(_OWO_FACES)


def _vaporwave(text: str) -> str:
    out = []
    for ch in text:
        if ch == " ":
            out.append("　")  # full-width space
        elif "!" <= ch <= "~":
            out.append(chr(ord(ch) + 0xFEE0))  # ASCII -> full-width range
        else:
            out.append(ch)
    return "".join(out)


def _emojify(text: str) -> str:
    out = []
    for ch in text.lower():
        if "a" <= ch <= "z":
            out.append(chr(0x1F1E6 + ord(ch) - ord("a")))  # regional indicator
        elif ch in _KEYCAPS:
            out.append(_KEYCAPS[ch])
        elif ch == " ":
            out.append("  ")
        else:
            out.append(ch)
    # Space-separate so repeated letters don't merge into flag emoji.
    return " ".join(out)


class Text(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def _send(self, interaction: discord.Interaction, text: str, out: str) -> None:
        if not text.strip():
            await interaction.response.send_message(
                "❌ Give me some text to transform.", ephemeral=True
            )
            return
        if len(text) > MAX_INPUT:
            await interaction.response.send_message(
                f"❌ Keep it under {MAX_INPUT} characters.", ephemeral=True
            )
            return
        await interaction.response.send_message(out[:1990])

    @app_commands.command(name="mock", description="SpOnGeBoB-cAsE some text.")
    @app_commands.describe(text="The text to mock")
    async def mock(self, interaction: discord.Interaction, text: str) -> None:
        await self._send(interaction, text, _mock(text))

    @app_commands.command(name="clap", description="Put 👏 claps 👏 between words.")
    @app_commands.describe(text="The text to clap")
    async def clap(self, interaction: discord.Interaction, text: str) -> None:
        out = " 👏 ".join(text.split())
        await self._send(interaction, text, out)

    @app_commands.command(name="owoify", description="Twanslate text into owo-speak.")
    @app_commands.describe(text="The text to owoify")
    async def owoify(self, interaction: discord.Interaction, text: str) -> None:
        await self._send(interaction, text, _owoify(text))

    @app_commands.command(name="vaporwave", description="Convert text to ｆｕｌｌ-ｗｉｄｔｈ.")
    @app_commands.describe(text="The text to convert")
    async def vaporwave(self, interaction: discord.Interaction, text: str) -> None:
        await self._send(interaction, text, _vaporwave(text))

    @app_commands.command(name="leet", description="Convert text to l33t speak.")
    @app_commands.describe(text="The text to convert")
    async def leet(self, interaction: discord.Interaction, text: str) -> None:
        await self._send(interaction, text, text.lower().translate(_LEET))

    @app_commands.command(name="emojify", description="Spell text with emoji letters.")
    @app_commands.describe(text="The text to emojify")
    async def emojify(self, interaction: discord.Interaction, text: str) -> None:
        # Emoji letters are wide, so cap the input harder than the others.
        if len(text) > 100:
            await interaction.response.send_message(
                "❌ Keep emojify under 100 characters.", ephemeral=True
            )
            return
        await self._send(interaction, text, _emojify(text))

    @app_commands.command(name="ascii", description="Render text as a big ASCII banner.")
    @app_commands.describe(text="The text to render (short works best)")
    async def ascii(self, interaction: discord.Interaction, text: str) -> None:
        if not text.strip():
            await interaction.response.send_message(
                "❌ Give me some text to render.", ephemeral=True
            )
            return
        if len(text) > 25:
            await interaction.response.send_message(
                "❌ Keep ASCII art under 25 characters.", ephemeral=True
            )
            return
        art = pyfiglet.figlet_format(text)
        if len(art) > 1990:
            await interaction.response.send_message(
                "❌ That came out too big — try shorter text.", ephemeral=True
            )
            return
        await interaction.response.send_message(f"```\n{art}\n```")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Text(bot))
