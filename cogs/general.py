"""General-purpose commands."""

import discord
from discord import app_commands
from discord.ext import commands


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
        # updates itself automatically as cogs are added or removed.
        for cog_name, cog in sorted(self.bot.cogs.items()):
            cmds = cog.get_app_commands()
            if not cmds:
                continue
            lines = [
                f"`/{cmd.name}` — {cmd.description}"
                for cmd in sorted(cmds, key=lambda c: c.name)
            ]
            embed.add_field(name=cog_name, value="\n".join(lines), inline=False)

        # Only the user who ran it sees the help, to avoid channel clutter.
        await interaction.response.send_message(embed=embed, ephemeral=True)


# Every cog file needs this entry point — the bot calls it when loading.
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(General(bot))
