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
import secrets
import string
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, unquote

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


# Morse code table (letters, digits, common punctuation).
_MORSE = {
    "a": ".-", "b": "-...", "c": "-.-.", "d": "-..", "e": ".", "f": "..-.",
    "g": "--.", "h": "....", "i": "..", "j": ".---", "k": "-.-", "l": ".-..",
    "m": "--", "n": "-.", "o": "---", "p": ".--.", "q": "--.-", "r": ".-.",
    "s": "...", "t": "-", "u": "..-", "v": "...-", "w": ".--", "x": "-..-",
    "y": "-.--", "z": "--..", "0": "-----", "1": ".----", "2": "..---",
    "3": "...--", "4": "....-", "5": ".....", "6": "-....", "7": "--...",
    "8": "---..", "9": "----.", ".": ".-.-.-", ",": "--..--", "?": "..--..",
    "'": ".----.", "!": "-.-.--", "/": "-..-.", "(": "-.--.", ")": "-.--.-",
    "&": ".-...", ":": "---...", ";": "-.-.-.", "=": "-...-", "+": ".-.-.",
    "-": "-....-", "_": "..--.-", '"': ".-..-.", "@": ".--.-.",
}
_MORSE_REVERSE = {code: char for char, code in _MORSE.items()}

# Unit conversion: each unit maps to (dimension, factor-to-base-unit).
# Base units are metre (length), gram (mass), litre (volume). Temperature is
# handled separately because it isn't a simple multiplicative scale.
_UNITS = {
    "m": ("length", 1.0), "km": ("length", 1000.0), "cm": ("length", 0.01),
    "mm": ("length", 0.001), "mi": ("length", 1609.344), "yd": ("length", 0.9144),
    "ft": ("length", 0.3048), "in": ("length", 0.0254),
    "g": ("mass", 1.0), "kg": ("mass", 1000.0), "mg": ("mass", 0.001),
    "lb": ("mass", 453.59237), "oz": ("mass", 28.349523125),
    "l": ("volume", 1.0), "ml": ("volume", 0.001), "gal": ("volume", 3.785411784),
    "qt": ("volume", 0.946352946), "cup": ("volume", 0.2365882365),
}
_TEMP_UNITS = {"c", "f", "k"}


def _to_celsius(value: float, unit: str) -> float:
    return {"c": value, "f": (value - 32) * 5 / 9, "k": value - 273.15}[unit]


def _from_celsius(value: float, unit: str) -> float:
    return {"c": value, "f": value * 9 / 5 + 32, "k": value + 273.15}[unit]


def _convert_units(value: float, frm: str, to: str) -> float:
    """Convert between two compatible units, or raise ValueError."""
    frm, to = frm.lower(), to.lower()
    if frm in _TEMP_UNITS and to in _TEMP_UNITS:
        return _from_celsius(_to_celsius(value, frm), to)
    if frm not in _UNITS or to not in _UNITS:
        raise ValueError("unknown unit")
    dim_from, factor_from = _UNITS[frm]
    dim_to, factor_to = _UNITS[to]
    if dim_from != dim_to:
        raise ValueError("incompatible units")
    return value * factor_from / factor_to


def _convert_base(number: str, from_base: int, to_base: int) -> str:
    """Convert an integer string from one base (2-36) to another."""
    value = int(number.strip(), from_base)
    if value == 0:
        return "0"
    digits = string.digits + string.ascii_lowercase
    sign = "-" if value < 0 else ""
    value = abs(value)
    out = ""
    while value:
        value, rem = divmod(value, to_base)
        out = digits[rem] + out
    return sign + out


# A time offset like "+2h", "-30m", or "1h30m" (relative to now).
_OFFSET_RE = re.compile(r"^[+-]?(?:\s*\d+\s*[smhd])+$", re.IGNORECASE)


def _parse_offset(text: str) -> int | None:
    """Parse a UTC offset like '+5', '-8', or '+5:30' into total minutes."""
    match = re.fullmatch(r"\s*([+-]?\d{1,2})(?::(\d{2}))?\s*", text)
    if not match:
        return None
    hours = int(match.group(1))
    minutes = int(match.group(2) or 0)
    if not -12 <= hours <= 14:
        return None
    return hours * 60 + (minutes if hours >= 0 else -minutes)


def _parse_when(text: str | None, offset_minutes: int = 0) -> datetime | None:
    """Parse a time spec into an aware UTC datetime, or None.

    Accepts: empty/"now"; an offset like "+2h"/"-30m"/"1h30m"; a Unix epoch
    in seconds; or an ISO date/time like "2026-06-16" or "2026-06-16 14:30".
    A bare clock time is assumed to be in offset_minutes from UTC (default UTC).
    """
    text = (text or "").strip()
    if not text or text.lower() == "now":
        return discord.utils.utcnow()
    if _OFFSET_RE.match(text):
        sign = -1 if text[0] == "-" else 1
        seconds = _parse_duration(text.lstrip("+-"))
        if seconds is None:
            return None
        return discord.utils.utcnow() + timedelta(seconds=sign * seconds)
    if re.fullmatch(r"-?\d+", text):
        try:
            return datetime.fromtimestamp(int(text), tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo:
        return parsed
    return parsed.replace(tzinfo=timezone(timedelta(minutes=offset_minutes)))


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

    # --- Text & encoding -----------------------------------------------------

    @app_commands.command(name="url", description="URL-encode or decode text.")
    @app_commands.describe(mode="Encode or decode", text="The text to convert")
    @app_commands.choices(
        mode=[
            app_commands.Choice(name="Encode", value="encode"),
            app_commands.Choice(name="Decode", value="decode"),
        ]
    )
    async def url(
        self,
        interaction: discord.Interaction,
        mode: app_commands.Choice[str],
        text: str,
    ) -> None:
        out = quote(text) if mode.value == "encode" else unquote(text)
        await interaction.response.send_message(f"```\n{out[:1900]}\n```")

    @app_commands.command(name="morse", description="Translate to or from Morse code.")
    @app_commands.describe(mode="Encode or decode", text="Text, or Morse using . - and spaces")
    @app_commands.choices(
        mode=[
            app_commands.Choice(name="Encode", value="encode"),
            app_commands.Choice(name="Decode", value="decode"),
        ]
    )
    async def morse(
        self,
        interaction: discord.Interaction,
        mode: app_commands.Choice[str],
        text: str,
    ) -> None:
        if mode.value == "encode":
            out = " ".join(_MORSE.get(ch, "") for ch in text.lower()).strip()
            out = re.sub(r" +", " ", out)
        else:
            # Words are separated by " / " or multiple spaces.
            words = re.split(r"\s*/\s*|\s{2,}", text.strip())
            out = " ".join(
                "".join(_MORSE_REVERSE.get(code, "") for code in word.split())
                for word in words
            )
        if not out:
            await interaction.response.send_message(
                "❌ Nothing translatable in that input.", ephemeral=True
            )
            return
        await interaction.response.send_message(f"```\n{out[:1900]}\n```")

    @app_commands.command(name="binary", description="Convert text to or from binary.")
    @app_commands.describe(mode="Encode or decode", text="Text, or 8-bit binary groups")
    @app_commands.choices(
        mode=[
            app_commands.Choice(name="Encode", value="encode"),
            app_commands.Choice(name="Decode", value="decode"),
        ]
    )
    async def binary(
        self,
        interaction: discord.Interaction,
        mode: app_commands.Choice[str],
        text: str,
    ) -> None:
        try:
            if mode.value == "encode":
                out = " ".join(format(b, "08b") for b in text.encode())
            else:
                bits = text.replace(" ", "")
                if not bits or len(bits) % 8 or set(bits) - {"0", "1"}:
                    raise ValueError
                out = bytes(
                    int(bits[i : i + 8], 2) for i in range(0, len(bits), 8)
                ).decode()
        except (ValueError, UnicodeDecodeError):
            await interaction.response.send_message(
                "❌ That isn't valid binary (need whole 8-bit bytes).", ephemeral=True
            )
            return
        await interaction.response.send_message(f"```\n{out[:1900]}\n```")

    @app_commands.command(name="reverse", description="Reverse a string.")
    @app_commands.describe(text="The text to reverse")
    async def reverse(self, interaction: discord.Interaction, text: str) -> None:
        await interaction.response.send_message(text[::-1][:2000])

    @app_commands.command(name="case", description="Change the case of text.")
    @app_commands.describe(style="Which case to apply", text="The text to convert")
    @app_commands.choices(
        style=[
            app_commands.Choice(name="UPPER", value="upper"),
            app_commands.Choice(name="lower", value="lower"),
            app_commands.Choice(name="Title", value="title"),
            app_commands.Choice(name="aLtErNaTiNg", value="alternating"),
        ]
    )
    async def case(
        self,
        interaction: discord.Interaction,
        style: app_commands.Choice[str],
        text: str,
    ) -> None:
        if style.value == "upper":
            out = text.upper()
        elif style.value == "lower":
            out = text.lower()
        elif style.value == "title":
            out = text.title()
        else:
            out = "".join(
                ch.upper() if i % 2 else ch.lower() for i, ch in enumerate(text)
            )
        await interaction.response.send_message(out[:2000])

    @app_commands.command(name="wordcount", description="Count characters, words, and lines.")
    @app_commands.describe(text="The text to measure")
    async def wordcount(self, interaction: discord.Interaction, text: str) -> None:
        chars = len(text)
        words = len(text.split())
        lines = text.count("\n") + 1 if text else 0
        await interaction.response.send_message(
            f"📝 **Characters:** {chars}  **Words:** {words}  **Lines:** {lines}"
        )

    @app_commands.command(name="uuid", description="Generate a random UUID.")
    async def uuid(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(f"`{uuid.uuid4()}`")

    @app_commands.command(name="password", description="Generate a secure random password.")
    @app_commands.describe(length="Password length, 8-128 (default 16)")
    async def password(
        self, interaction: discord.Interaction, length: int = 16
    ) -> None:
        if not 8 <= length <= 128:
            await interaction.response.send_message(
                "❌ Length must be between 8 and 128.", ephemeral=True
            )
            return
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"
        pwd = "".join(secrets.choice(alphabet) for _ in range(length))
        # Ephemeral so the password isn't broadcast to the whole channel.
        await interaction.response.send_message(f"🔐 ||`{pwd}`||", ephemeral=True)

    # --- Numbers & conversion ------------------------------------------------

    @app_commands.command(name="convert", description="Convert between units.")
    @app_commands.describe(
        value="The number to convert",
        from_unit="Unit to convert from (e.g. km, lb, c)",
        to_unit="Unit to convert to (e.g. mi, kg, f)",
    )
    async def convert(
        self,
        interaction: discord.Interaction,
        value: float,
        from_unit: str,
        to_unit: str,
    ) -> None:
        try:
            result = _convert_units(value, from_unit, to_unit)
        except ValueError:
            await interaction.response.send_message(
                "❌ Unknown or incompatible units. Try length (km, mi, m, ft, in), "
                "mass (kg, lb, g, oz), volume (l, gal, cup), or temp (c, f, k).",
                ephemeral=True,
            )
            return
        await interaction.response.send_message(
            f"🔁 **{value:g} {from_unit.lower()}** = **{result:g} {to_unit.lower()}**"
        )

    @app_commands.command(name="base", description="Convert a number between bases (2-36).")
    @app_commands.describe(
        number="The number to convert",
        from_base="Base it's currently in (2-36)",
        to_base="Base to convert to (2-36)",
    )
    async def base(
        self,
        interaction: discord.Interaction,
        number: str,
        from_base: int,
        to_base: int,
    ) -> None:
        if not (2 <= from_base <= 36 and 2 <= to_base <= 36):
            await interaction.response.send_message(
                "❌ Bases must be between 2 and 36.", ephemeral=True
            )
            return
        try:
            out = _convert_base(number, from_base, to_base)
        except ValueError:
            await interaction.response.send_message(
                f"❌ `{number}` isn't a valid base-{from_base} number.", ephemeral=True
            )
            return
        await interaction.response.send_message(
            f"🔢 `{number}` (base {from_base}) = `{out}` (base {to_base})"
        )

    @app_commands.command(name="random", description="Pick a random number in a range.")
    @app_commands.describe(minimum="Lowest value", maximum="Highest value")
    async def random(
        self, interaction: discord.Interaction, minimum: int, maximum: int
    ) -> None:
        if minimum > maximum:
            minimum, maximum = maximum, minimum
        await interaction.response.send_message(
            f"🎲 **{secrets.randbelow(maximum - minimum + 1) + minimum}** "
            f"(between {minimum} and {maximum})"
        )

    @app_commands.command(name="percent", description="What percent is X of Y?")
    @app_commands.describe(x="The part", y="The whole")
    async def percent(
        self, interaction: discord.Interaction, x: float, y: float
    ) -> None:
        if y == 0:
            await interaction.response.send_message(
                "❌ The whole can't be zero.", ephemeral=True
            )
            return
        await interaction.response.send_message(
            f"📊 **{x:g}** is **{x / y * 100:g}%** of **{y:g}**"
        )

    @app_commands.command(name="tip", description="Calculate a tip and optional split.")
    @app_commands.describe(
        bill="The bill amount",
        percent="Tip percentage (default 18)",
        split="Number of people to split between (default 1)",
    )
    async def tip(
        self,
        interaction: discord.Interaction,
        bill: float,
        percent: float = 18.0,
        split: int = 1,
    ) -> None:
        if bill < 0 or percent < 0 or split < 1:
            await interaction.response.send_message(
                "❌ Bill/percent must be ≥ 0 and split ≥ 1.", ephemeral=True
            )
            return
        tip_amount = bill * percent / 100
        total = bill + tip_amount
        lines = [
            f"💵 **Bill:** {bill:.2f}",
            f"➕ **Tip ({percent:g}%):** {tip_amount:.2f}",
            f"🧾 **Total:** {total:.2f}",
        ]
        if split > 1:
            lines.append(f"👥 **Each of {split}:** {total / split:.2f}")
        await interaction.response.send_message("\n".join(lines))

    # --- Time & dates --------------------------------------------------------

    @app_commands.command(name="timestamp", description="Generate Discord timestamp codes.")
    @app_commands.describe(
        when="now, an offset like +2h, a Unix time, or 2026-06-16 14:30 (default: now)"
    )
    async def timestamp(
        self, interaction: discord.Interaction, when: str = ""
    ) -> None:
        moment = _parse_when(when)
        if moment is None:
            await interaction.response.send_message(
                "❌ Couldn't read that time. Try `now`, `+2h`, a Unix time, or "
                "`2026-06-16 14:30`.",
                ephemeral=True,
            )
            return
        epoch = int(moment.timestamp())
        styles = ["t", "T", "d", "D", "f", "F", "R"]
        lines = [f"`<t:{epoch}:{s}>` → <t:{epoch}:{s}>" for s in styles]
        await interaction.response.send_message(
            "🕒 Copy a code below:\n" + "\n".join(lines), ephemeral=True
        )

    @app_commands.command(name="unixtime", description="Show the current Unix timestamp.")
    async def unixtime(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(
            f"⏱️ `{int(discord.utils.utcnow().timestamp())}`"
        )

    @app_commands.command(name="timein", description="Current time at a UTC offset.")
    @app_commands.describe(offset="UTC offset like +5, -8, or +5:30")
    async def timein(self, interaction: discord.Interaction, offset: str) -> None:
        total = _parse_offset(offset)
        if total is None:
            await interaction.response.send_message(
                "❌ Use an offset like `+5`, `-8`, or `+5:30` (hours -12 to +14).",
                ephemeral=True,
            )
            return
        local = discord.utils.utcnow() + timedelta(minutes=total)
        await interaction.response.send_message(
            f"🌍 Time at UTC{offset.strip()}: **{local:%H:%M}** ({local:%a %d %b})"
        )

    @app_commands.command(name="countdown", description="Show a live countdown to a time.")
    @app_commands.describe(when="An offset like +2h, a Unix time, or 2026-06-16 14:30")
    async def countdown(self, interaction: discord.Interaction, when: str) -> None:
        moment = _parse_when(when)
        if moment is None:
            await interaction.response.send_message(
                "❌ Couldn't read that time. Try `+2h`, a Unix time, or "
                "`2026-06-16 14:30`.",
                ephemeral=True,
            )
            return
        epoch = int(moment.timestamp())
        await interaction.response.send_message(
            f"⏳ <t:{epoch}:F> — <t:{epoch}:R>"
        )

    @app_commands.command(
        name="event", description="Announce an event in everyone's local time."
    )
    @app_commands.describe(
        title="What's happening",
        when="now, +2h, a Unix time, or 2026-06-16 14:30",
        utc_offset="If you gave a clock time, which UTC offset it's in (e.g. -5 or +5:30)",
    )
    async def event(
        self,
        interaction: discord.Interaction,
        title: str,
        when: str,
        utc_offset: str = "",
    ) -> None:
        offset_minutes = 0
        if utc_offset.strip():
            parsed = _parse_offset(utc_offset)
            if parsed is None:
                await interaction.response.send_message(
                    "❌ Use a UTC offset like `-5`, `+1`, or `+5:30`.", ephemeral=True
                )
                return
            offset_minutes = parsed
        moment = _parse_when(when, offset_minutes)
        if moment is None:
            await interaction.response.send_message(
                "❌ Couldn't read that time. Try `+2h`, a Unix time, or "
                "`2026-06-16 14:30`.",
                ephemeral=True,
            )
            return
        # A Discord timestamp renders in each viewer's own local time, so one
        # announcement shows correctly for everyone — no per-user timezones.
        epoch = int(moment.timestamp())
        embed = discord.Embed(title=f"🗓️ {title}", color=discord.Color.blurple())
        embed.add_field(name="When", value=f"<t:{epoch}:F>", inline=False)
        embed.add_field(name="Starts", value=f"<t:{epoch}:R>", inline=False)
        embed.set_footer(
            text=f"Shown in your local time • posted by {interaction.user.display_name}"
        )
        await interaction.response.send_message(embed=embed)

    # --- Discord helpers -----------------------------------------------------

    @app_commands.command(name="say", description="Make the bot say something.")
    @app_commands.describe(text="What the bot should say")
    async def say(self, interaction: discord.Interaction, text: str) -> None:
        channel = interaction.channel
        if channel is None or not hasattr(channel, "send"):
            await interaction.response.send_message(text)
            return
        await interaction.response.send_message("✅ Sent.", ephemeral=True)
        await channel.send(text)

    @app_commands.command(name="membercount", description="Show the server's member count.")
    async def membercount(self, interaction: discord.Interaction) -> None:
        guild = interaction.guild
        if guild is None:
            await interaction.response.send_message(
                "❌ This command only works in a server.", ephemeral=True
            )
            return
        await interaction.response.send_message(
            f"👥 **{guild.name}** has **{guild.member_count}** members."
        )

    @app_commands.command(name="snowflake", description="Decode the creation date of a Discord ID.")
    @app_commands.describe(id="A user, message, channel, or other Discord ID")
    async def snowflake(self, interaction: discord.Interaction, id: str) -> None:
        if not id.strip().isdigit():
            await interaction.response.send_message(
                "❌ That doesn't look like a Discord ID.", ephemeral=True
            )
            return
        created = discord.utils.snowflake_time(int(id))
        await interaction.response.send_message(
            f"❄️ ID `{id}` was created {discord.utils.format_dt(created, 'F')} "
            f"({discord.utils.format_dt(created, 'R')})"
        )

    @app_commands.command(name="colorinfo", description="Show details for a hex color.")
    @app_commands.describe(hex="A hex color like #3498db or 3498db")
    async def colorinfo(self, interaction: discord.Interaction, hex: str) -> None:
        value = hex.strip().lstrip("#")
        if not re.fullmatch(r"[0-9a-fA-F]{6}", value):
            await interaction.response.send_message(
                "❌ Give a 6-digit hex color, like `#3498db`.", ephemeral=True
            )
            return
        r, g, b = (int(value[i : i + 2], 16) for i in (0, 2, 4))
        embed = discord.Embed(
            title=f"#{value.lower()}", color=discord.Color.from_rgb(r, g, b)
        )
        embed.add_field(name="HEX", value=f"#{value.upper()}")
        embed.add_field(name="RGB", value=f"{r}, {g}, {b}")
        embed.description = "The bar on the left shows the color."
        await interaction.response.send_message(embed=embed)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Utility(bot))
