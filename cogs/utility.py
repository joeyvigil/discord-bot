"""Utility commands. Self-contained — no external APIs or state.

Covers quick everyday helpers: user/server info, a safe calculator,
encoding/hashing tools, QR codes, and simple reminders.
"""

import ast
import asyncio
import base64 as base64_lib
import binascii
import hashlib
import operator
import re
from datetime import timedelta
from urllib.parse import quote

import discord
from discord import app_commands
from discord.ext import commands

# Operators the calculator is allowed to evaluate. Anything else is rejected,
# so /calc can never run arbitrary code the way a bare eval() would.
_CALC_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

# Reminder duration like "10s", "5m", "1h30m", "1d". Capped at one day.
_DURATION_RE = re.compile(r"(\d+)\s*([smhd])", re.IGNORECASE)
_UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400}
_MAX_REMINDER = 86400


def _safe_eval(node: ast.AST) -> float:
    """Recursively evaluate a parsed arithmetic expression, math only."""
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
            return node.value
        raise ValueError("only numbers are allowed")
    if isinstance(node, ast.BinOp) and type(node.op) in _CALC_OPS:
        right = _safe_eval(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 100:
            raise ValueError("exponent too large")
        return _CALC_OPS[type(node.op)](_safe_eval(node.left), right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _CALC_OPS:
        return _CALC_OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError("unsupported expression")


def _parse_duration(text: str) -> int | None:
    """Turn '1h30m' into seconds, or None if nothing valid was found."""
    matches = _DURATION_RE.findall(text)
    if not matches:
        return None
    total = sum(int(value) * _UNIT_SECONDS[unit.lower()] for value, unit in matches)
    return total if total > 0 else None


class Utility(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="avatar", description="Show a user's avatar.")
    @app_commands.describe(user="Whose avatar to show (defaults to you)")
    async def avatar(
        self, interaction: discord.Interaction, user: discord.User | None = None
    ) -> None:
        target = user or interaction.user
        embed = discord.Embed(title=f"{target.display_name}'s avatar")
        embed.set_image(url=target.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="userinfo", description="Show info about a user.")
    @app_commands.describe(user="The user to inspect (defaults to you)")
    async def userinfo(
        self, interaction: discord.Interaction, user: discord.Member | None = None
    ) -> None:
        member = user or interaction.user
        embed = discord.Embed(title=f"👤 {member.display_name}", color=member.color)
        embed.set_thumbnail(url=member.display_avatar.url)
        embed.add_field(name="Username", value=str(member), inline=False)
        embed.add_field(name="ID", value=member.id)
        embed.add_field(
            name="Account created",
            value=discord.utils.format_dt(member.created_at, "R"),
        )
        if isinstance(member, discord.Member) and member.joined_at:
            embed.add_field(
                name="Joined server",
                value=discord.utils.format_dt(member.joined_at, "R"),
            )
            # Skip @everyone, show highest roles first.
            roles = [r.mention for r in reversed(member.roles) if r.name != "@everyone"]
            if roles:
                embed.add_field(
                    name=f"Roles ({len(roles)})",
                    value=" ".join(roles[:10]),
                    inline=False,
                )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="serverinfo", description="Show info about this server.")
    async def serverinfo(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message(
                "❌ This command only works in a server.", ephemeral=True
            )
            return
        embed = discord.Embed(title=f"🏠 {guild.name}", color=discord.Color.blurple())
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        embed.add_field(name="Owner", value=f"<@{guild.owner_id}>")
        embed.add_field(name="Members", value=guild.member_count)
        embed.add_field(
            name="Created", value=discord.utils.format_dt(guild.created_at, "R")
        )
        embed.add_field(name="Channels", value=len(guild.channels))
        embed.add_field(name="Roles", value=len(guild.roles))
        embed.add_field(name="ID", value=guild.id)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="calc", description="Evaluate a math expression.")
    @app_commands.describe(expression="e.g. 2 + 2 * 5 or (3 ** 4) / 2")
    async def calc(self, interaction: discord.Interaction, expression: str) -> None:
        try:
            result = _safe_eval(ast.parse(expression, mode="eval").body)
        except ZeroDivisionError:
            await interaction.response.send_message(
                "❌ Can't divide by zero.", ephemeral=True
            )
            return
        except Exception:
            await interaction.response.send_message(
                "❌ That's not a valid math expression.", ephemeral=True
            )
            return
        # Trim a trailing .0 so 4.0 shows as 4.
        if isinstance(result, float) and result.is_integer():
            result = int(result)
        await interaction.response.send_message(f"🧮 `{expression}` = **{result}**")

    @app_commands.command(name="base64", description="Encode or decode base64 text.")
    @app_commands.describe(mode="Encode or decode", text="The text to convert")
    @app_commands.choices(
        mode=[
            app_commands.Choice(name="Encode", value="encode"),
            app_commands.Choice(name="Decode", value="decode"),
        ]
    )
    async def base64(
        self,
        interaction: discord.Interaction,
        mode: app_commands.Choice[str],
        text: str,
    ) -> None:
        try:
            if mode.value == "encode":
                out = base64_lib.b64encode(text.encode()).decode()
            else:
                out = base64_lib.b64decode(text, validate=True).decode()
        except (binascii.Error, UnicodeDecodeError, ValueError):
            await interaction.response.send_message(
                "❌ That isn't valid base64.", ephemeral=True
            )
            return
        await interaction.response.send_message(f"```\n{out[:1900]}\n```")

    @app_commands.command(name="hash", description="Hash text with a chosen algorithm.")
    @app_commands.describe(algorithm="Which hash to use", text="The text to hash")
    @app_commands.choices(
        algorithm=[
            app_commands.Choice(name="MD5", value="md5"),
            app_commands.Choice(name="SHA-1", value="sha1"),
            app_commands.Choice(name="SHA-256", value="sha256"),
            app_commands.Choice(name="SHA-512", value="sha512"),
        ]
    )
    async def hash(
        self,
        interaction: discord.Interaction,
        algorithm: app_commands.Choice[str],
        text: str,
    ) -> None:
        digest = hashlib.new(algorithm.value, text.encode()).hexdigest()
        await interaction.response.send_message(
            f"**{algorithm.name}**\n```\n{digest}\n```"
        )

    @app_commands.command(name="qr", description="Generate a QR code for some text.")
    @app_commands.describe(text="Text or URL to encode")
    async def qr(self, interaction: discord.Interaction, text: str) -> None:
        url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={quote(text)}"
        embed = discord.Embed(title="📱 QR Code")
        embed.set_image(url=url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="remindme", description="Get pinged after a delay.")
    @app_commands.describe(
        when="How long to wait, e.g. 10m, 1h30m, 2h (max 1 day)",
        text="What to remind you about",
    )
    async def remindme(
        self, interaction: discord.Interaction, when: str, text: str
    ) -> None:
        seconds = _parse_duration(when)
        if seconds is None:
            await interaction.response.send_message(
                "❌ Use a duration like `10m`, `1h30m`, or `2h`.", ephemeral=True
            )
            return
        if seconds > _MAX_REMINDER:
            await interaction.response.send_message(
                "❌ Reminders can be at most 1 day out.", ephemeral=True
            )
            return

        stamp = discord.utils.format_dt(
            discord.utils.utcnow() + timedelta(seconds=seconds), "R"
        )
        await interaction.response.send_message(f"⏰ Okay! I'll remind you {stamp}.")
        # Fire-and-forget; reminders don't survive a bot restart, which is fine
        # for short delays. Use the channel so it works past the 15-min webhook
        # window, falling back to a DM if the channel is gone.
        self.bot.loop.create_task(
            self._deliver(interaction.channel, interaction.user, text, seconds)
        )

    async def _deliver(
        self,
        channel: discord.abc.Messageable | None,
        user: discord.User | discord.Member,
        text: str,
        seconds: int,
    ) -> None:
        await asyncio.sleep(seconds)
        message = f"⏰ {user.mention} reminder: {text}"
        try:
            if channel is not None:
                await channel.send(message)
            else:
                await user.send(message)
        except discord.HTTPException:
            pass


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Utility(bot))
