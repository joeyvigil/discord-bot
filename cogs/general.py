"""General-purpose commands."""

import discord
from discord import app_commands
from discord.ext import commands


# Friendly section titles and display order for the help embed, keyed by cog
# class name. Cogs not listed here fall back to their class name, listed last.
COG_SECTIONS = {
    "General": "⚙️ General",
    "Fun": "🎲 Fun & Games",
    "Interactive": "🕹️ Interactive",
    "Api": "🌐 Web & Lookups",
    "Utility": "🧰 Utility",
}


class General(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="ping", description="Check if the bot is alive.")
    async def ping(self, interaction: discord.Interaction) -> None:
        latency_ms = round(self.bot.latency * 1000)
        await interaction.response.send_message(f"Pong! 🏓 ({latency_ms} ms)")

    @app_commands.command(name="echo", description="Repeat back what you say.")
    @app_commands.describe(message="The text you want the bot to repeat")
    async def echo(self, interaction: discord.Interaction, message: str) -> None:
        await interaction.response.send_message(message)

    @app_commands.command(name="help", description="List every command the bot has.")
    async def help(self, interaction: discord.Interaction) -> None:
        embed = discord.Embed(
            title="📖 Command Help",
            description="Here's everything I can do:",
            color=discord.Color.blurple(),
        )
        # Walk each cog so commands stay grouped by feature, and the list
        # updates itself automatically as cogs are added or removed. Cogs in
        # COG_SECTIONS show first in that order with friendly titles; any
        # others fall back to their class name, sorted, at the end.
        order = list(COG_SECTIONS)

        def sort_key(item: tuple[str, commands.Cog]) -> tuple[int, str]:
            name = item[0]
            return (order.index(name) if name in order else len(order), name)

        for cog_name, cog in sorted(self.bot.cogs.items(), key=sort_key):
            cmds = cog.get_app_commands()
            if not cmds:
                continue
            lines = [
                f"`/{cmd.name}` — {cmd.description}"
                for cmd in sorted(cmds, key=lambda c: c.name)
            ]
            title = COG_SECTIONS.get(cog_name, cog_name)
            embed.add_field(name=title, value="\n".join(lines), inline=False)

        # Only the user who ran it sees the help, to avoid channel clutter.
        await interaction.response.send_message(embed=embed, ephemeral=True)


# Every cog file needs this entry point — the bot calls it when loading.
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(General(bot))
