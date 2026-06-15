"""Fun, self-contained commands. No external APIs — just Python's random."""

import random
import re

import discord
from discord import app_commands
from discord.ext import commands

EIGHTBALL_ANSWERS = [
    "It is certain.", "Without a doubt.", "Yes — definitely.", "You may rely on it.",
    "Most likely.", "Outlook good.", "Signs point to yes.",
    "Reply hazy, try again.", "Ask again later.", "Better not tell you now.",
    "Cannot predict now.", "Concentrate and ask again.",
    "Don't count on it.", "My reply is no.", "Very doubtful.", "Outlook not so good.",
]

RPS_CHOICES = ["rock", "paper", "scissors"]
RPS_BEATS = {"rock": "scissors", "paper": "rock", "scissors": "paper"}
RPS_EMOJI = {"rock": "🪨", "paper": "📄", "scissors": "✂️"}

# Caps to keep dice rolls sane and output short.
MAX_DICE = 100
MAX_SIDES = 1000


def stable_percent(*parts: str) -> int:
    """Deterministic 0-100 value for the given inputs (same inputs => same result)."""
    seed = "|".join(parts)
    return random.Random(seed).randint(0, 100)


class Fun(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="8ball", description="Ask the magic 8-ball a question.")
    @app_commands.describe(question="Your yes/no question")
    async def eightball(self, interaction: discord.Interaction, question: str) -> None:
        answer = random.choice(EIGHTBALL_ANSWERS)
        await interaction.response.send_message(
            f"🎱 **Question:** {question}\n**Answer:** {answer}"
        )

    @app_commands.command(name="roll", description="Roll dice, e.g. 2d6 or d20.")
    @app_commands.describe(dice="Dice in NdM format (default: 1d6)")
    async def roll(self, interaction: discord.Interaction, dice: str = "1d6") -> None:
        match = re.fullmatch(r"\s*(\d*)d(\d+)\s*", dice, re.IGNORECASE)
        if not match:
            await interaction.response.send_message(
                "❌ Use NdM format, like `2d6`, `d20`, or `1d100`.", ephemeral=True
            )
            return

        count = int(match.group(1)) if match.group(1) else 1
        sides = int(match.group(2))
        if count < 1 or sides < 1:
            await interaction.response.send_message(
                "❌ Dice count and sides must be at least 1.", ephemeral=True
            )
            return
        if count > MAX_DICE or sides > MAX_SIDES:
            await interaction.response.send_message(
                f"❌ Keep it under {MAX_DICE} dice and {MAX_SIDES} sides.", ephemeral=True
            )
            return

        rolls = [random.randint(1, sides) for _ in range(count)]
        total = sum(rolls)
        if count == 1:
            await interaction.response.send_message(f"🎲 You rolled a **{total}** (d{sides}).")
        else:
            shown = ", ".join(str(r) for r in rolls)
            await interaction.response.send_message(
                f"🎲 Rolling {count}d{sides}: [{shown}]\n**Total: {total}**"
            )

    @app_commands.command(name="coinflip", description="Flip a coin.")
    async def coinflip(self, interaction: discord.Interaction) -> None:
        result = random.choice(["Heads", "Tails"])
        emoji = "🪙"
        await interaction.response.send_message(f"{emoji} **{result}!**")

    @app_commands.command(name="choose", description="Let the bot pick from your options.")
    @app_commands.describe(options="Options separated by commas, e.g. pizza, tacos, sushi")
    async def choose(self, interaction: discord.Interaction, options: str) -> None:
        choices = [o.strip() for o in options.split(",") if o.strip()]
        if len(choices) < 2:
            await interaction.response.send_message(
                "❌ Give me at least two options separated by commas.", ephemeral=True
            )
            return
        pick = random.choice(choices)
        await interaction.response.send_message(f"🤔 I choose: **{pick}**")

    @app_commands.command(name="rps", description="Play rock-paper-scissors against the bot.")
    @app_commands.describe(choice="Your move")
    @app_commands.choices(
        choice=[
            app_commands.Choice(name="Rock 🪨", value="rock"),
            app_commands.Choice(name="Paper 📄", value="paper"),
            app_commands.Choice(name="Scissors ✂️", value="scissors"),
        ]
    )
    async def rps(self, interaction: discord.Interaction, choice: app_commands.Choice[str]) -> None:
        player = choice.value
        bot_choice = random.choice(RPS_CHOICES)

        if player == bot_choice:
            outcome = "It's a **tie**! 🤝"
        elif RPS_BEATS[player] == bot_choice:
            outcome = "You **win**! 🎉"
        else:
            outcome = "You **lose**! 😎"

        await interaction.response.send_message(
            f"You: {RPS_EMOJI[player]}  vs  Me: {RPS_EMOJI[bot_choice]}\n{outcome}"
        )

    @app_commands.command(name="ship", description="Calculate the love compatibility of two people.")
    @app_commands.describe(person1="First person", person2="Second person")
    async def ship(
        self,
        interaction: discord.Interaction,
        person1: discord.Member,
        person2: discord.Member,
    ) -> None:
        if person1 == person2:
            await interaction.response.send_message(
                "❤️ Self-love is **100%** the best love! 💯"
            )
            return

        # Sort IDs so the order of arguments doesn't change the result.
        a, b = sorted([str(person1.id), str(person2.id)])
        percent = stable_percent("ship", a, b)

        filled = round(percent / 10)
        bar = "█" * filled + "░" * (10 - filled)
        if percent >= 80:
            verdict = "A match made in heaven! 💞"
        elif percent >= 50:
            verdict = "There's definitely something here. 😏"
        elif percent >= 20:
            verdict = "It's... complicated. 😅"
        else:
            verdict = "Maybe just stay friends. 🙃"

        await interaction.response.send_message(
            f"💘 **{person1.display_name}** + **{person2.display_name}**\n"
            f"`{bar}` **{percent}%**\n{verdict}"
        )

    @app_commands.command(name="rate", description="Get the bot's official rating of anything.")
    @app_commands.describe(thing="What should I rate?")
    async def rate(self, interaction: discord.Interaction, thing: str) -> None:
        # Stable so re-rating the same thing gives the same score.
        score = stable_percent("rate", thing.lower().strip()) // 10
        await interaction.response.send_message(
            f"I'd rate **{thing}** a solid **{score}/10**."
        )


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Fun(bot))
