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
    "Text": "🔤 Text",
    "Comics": "📰 Comics",
    "Api": "🌐 Web & Lookups",
    "Utility": "🧰 Utility",
}

# Dropdown options for /help — one per known section, in the same order.
HELP_CHOICES = [
    app_commands.Choice(name=title, value=key) for key, title in COG_SECTIONS.items()
]


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

    def _ordered_cogs(self) -> list[tuple[str, commands.Cog]]:
        """Cogs in COG_SECTIONS order; unlisted ones sorted by name at the end."""
        order = list(COG_SECTIONS)

        def sort_key(item: tuple[str, commands.Cog]) -> tuple[int, str]:
            name = item[0]
            return (order.index(name) if name in order else len(order), name)

        return sorted(self.bot.cogs.items(), key=sort_key)

    def _compact_help(self) -> discord.Embed:
        """One field per section listing just command names — fits everything."""
        embed = discord.Embed(
            title="📖 Command Help",
            description="Use `/help category:<name>` for details on a section.",
            color=discord.Color.blurple(),
        )
        total = 0
        for cog_name, cog in self._ordered_cogs():
            cmds = cog.get_app_commands()
            if not cmds:
                continue
            total += len(cmds)
            names = ", ".join(f"`/{c.name}`" for c in sorted(cmds, key=lambda c: c.name))
            title = COG_SECTIONS.get(cog_name, cog_name)
            embed.add_field(name=f"{title} ({len(cmds)})", value=names, inline=False)
        embed.set_footer(text=f"{total} commands")
        return embed

    def _category_help(self, cog_name: str) -> discord.Embed:
        """Full command + description list for a single section."""
        title = COG_SECTIONS.get(cog_name, cog_name)
        embed = discord.Embed(title=title, color=discord.Color.blurple())
        cog = self.bot.get_cog(cog_name)
        cmds = sorted(cog.get_app_commands(), key=lambda c: c.name) if cog else []
        if not cmds:
            embed.description = "No commands in this section."
            return embed
        embed.description = "\n".join(
            f"`/{cmd.name}` — {cmd.description}" for cmd in cmds
        )
        return embed

    @app_commands.command(
        name="help", description="Show commands; pick a category for details."
    )
    @app_commands.describe(category="Show detailed help for one category")
    @app_commands.choices(category=HELP_CHOICES)
    async def help(
        self,
        interaction: discord.Interaction,
        category: app_commands.Choice[str] | None = None,
    ) -> None:
        embed = (
            self._compact_help()
            if category is None
            else self._category_help(category.value)
        )
        # Only the user who ran it sees the help, to avoid channel clutter.
        await interaction.response.send_message(embed=embed, ephemeral=True)


# Every cog file needs this entry point — the bot calls it when loading.
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(General(bot))
