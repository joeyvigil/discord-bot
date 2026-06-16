"""Interactive commands built on discord.py UI components (buttons).

These keep their state in the View object that lives with the message, so
they are not persistent — a bot restart drops any in-progress polls/games.
That's an acceptable trade-off for these lightweight, short-lived features.
"""

import html
import logging
import random

import aiohttp
import discord
from discord import app_commands
from discord.ext import commands

log = logging.getLogger("bot")

REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=10)


# --- /poll -------------------------------------------------------------------


class PollView(discord.ui.View):
    def __init__(self, question: str, options: list[str]) -> None:
        super().__init__(timeout=86400)  # polls stay live for a day
        self.question = question
        self.options = options
        self.votes: dict[int, int] = {}  # user_id -> option index
        for index, option in enumerate(options):
            self.add_item(PollButton(index, option))

    def build_embed(self) -> discord.Embed:
        total = len(self.votes)
        counts = [0] * len(self.options)
        for choice in self.votes.values():
            counts[choice] += 1

        embed = discord.Embed(title=f"📊 {self.question}", color=discord.Color.blurple())
        for index, option in enumerate(self.options):
            count = counts[index]
            pct = (count / total * 100) if total else 0
            filled = round(pct / 10)
            bar = "█" * filled + "░" * (10 - filled)
            embed.add_field(
                name=option, value=f"`{bar}` {count} ({pct:.0f}%)", inline=False
            )
        embed.set_footer(text=f"{total} vote(s) • one vote each, change anytime")
        return embed


class PollButton(discord.ui.Button):
    def __init__(self, index: int, label: str) -> None:
        super().__init__(label=label[:80], style=discord.ButtonStyle.primary)
        self.index = index

    async def callback(self, interaction: discord.Interaction) -> None:
        view: PollView = self.view  # type: ignore[assignment]
        view.votes[interaction.user.id] = self.index
        await interaction.response.edit_message(embed=view.build_embed(), view=view)


# --- /trivia -----------------------------------------------------------------


class TriviaView(discord.ui.View):
    def __init__(self, answers: list[str], correct_index: int) -> None:
        super().__init__(timeout=30)
        self.correct_index = correct_index
        self.answered = False
        for index, answer in enumerate(answers):
            self.add_item(TriviaButton(index, answer))


class TriviaButton(discord.ui.Button):
    def __init__(self, index: int, label: str) -> None:
        super().__init__(label=label[:80], style=discord.ButtonStyle.secondary)
        self.index = index

    async def callback(self, interaction: discord.Interaction) -> None:
        view: TriviaView = self.view  # type: ignore[assignment]
        if view.answered:
            await interaction.response.send_message(
                "Someone already answered this one!", ephemeral=True
            )
            return
        view.answered = True

        correct_label = ""
        for child in view.children:
            if isinstance(child, TriviaButton):
                child.disabled = True
                if child.index == view.correct_index:
                    child.style = discord.ButtonStyle.success
                    correct_label = child.label
                elif child is self:
                    child.style = discord.ButtonStyle.danger

        if self.index == view.correct_index:
            result = f"✅ {interaction.user.mention} got it right!"
        else:
            result = (
                f"❌ {interaction.user.mention} missed it — "
                f"the answer was **{correct_label}**."
            )
        view.stop()
        await interaction.response.edit_message(content=result, view=view)


# --- /tictactoe --------------------------------------------------------------


class TicTacToe(discord.ui.View):
    def __init__(self, player_x: discord.Member, player_o: discord.Member) -> None:
        super().__init__(timeout=300)
        self.player_x = player_x
        self.player_o = player_o
        self.current = player_x
        self.symbols = {player_x.id: "X", player_o.id: "O"}
        self.board = [["" for _ in range(3)] for _ in range(3)]
        for y in range(3):
            for x in range(3):
                self.add_item(TicTacToeButton(x, y))

    def status(self) -> str:
        return (
            f"⭕ Tic-Tac-Toe: {self.player_x.mention} (X) vs {self.player_o.mention} (O)\n"
            f"**{self.current.mention}**'s turn ({self.symbols[self.current.id]})"
        )

    def winner(self) -> bool:
        lines = list(self.board)  # rows
        lines.extend([self.board[r][c] for r in range(3)] for c in range(3))  # cols
        lines.append([self.board[i][i] for i in range(3)])  # main diagonal
        lines.append([self.board[i][2 - i] for i in range(3)])  # anti-diagonal
        return any(line[0] and line[0] == line[1] == line[2] for line in lines)

    def is_full(self) -> bool:
        return all(cell for row in self.board for cell in row)


class TicTacToeButton(discord.ui.Button):
    def __init__(self, x: int, y: int) -> None:
        super().__init__(style=discord.ButtonStyle.secondary, label="​", row=y)
        self.x = x
        self.y = y

    async def callback(self, interaction: discord.Interaction) -> None:
        view: TicTacToe = self.view  # type: ignore[assignment]
        if interaction.user.id not in view.symbols:
            await interaction.response.send_message(
                "This isn't your game!", ephemeral=True
            )
            return
        if interaction.user.id != view.current.id:
            await interaction.response.send_message(
                "It's not your turn.", ephemeral=True
            )
            return

        mark = view.symbols[view.current.id]
        view.board[self.y][self.x] = mark
        self.label = mark
        self.disabled = True
        self.style = (
            discord.ButtonStyle.danger if mark == "X" else discord.ButtonStyle.success
        )

        if view.winner():
            content = f"🎉 {view.current.mention} ({mark}) wins!"
            for child in view.children:
                child.disabled = True
            view.stop()
        elif view.is_full():
            content = "It's a draw! 🤝"
            view.stop()
        else:
            view.current = (
                view.player_o if view.current.id == view.player_x.id else view.player_x
            )
            content = view.status()
        await interaction.response.edit_message(content=content, view=view)


class Interactive(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.session: aiohttp.ClientSession | None = None

    async def cog_load(self) -> None:
        self.session = aiohttp.ClientSession(timeout=REQUEST_TIMEOUT)

    async def cog_unload(self) -> None:
        if self.session:
            await self.session.close()

    @app_commands.command(name="poll", description="Create a live button poll.")
    @app_commands.describe(
        question="What you're asking", options="2-5 options separated by commas"
    )
    async def poll(
        self, interaction: discord.Interaction, question: str, options: str
    ) -> None:
        opts = [o.strip() for o in options.split(",") if o.strip()]
        if not 2 <= len(opts) <= 5:
            await interaction.response.send_message(
                "❌ Give 2 to 5 options separated by commas.", ephemeral=True
            )
            return
        view = PollView(question, opts)
        await interaction.response.send_message(embed=view.build_embed(), view=view)

    @app_commands.command(name="trivia", description="Answer a trivia question.")
    async def trivia(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        assert self.session is not None
        try:
            async with self.session.get(
                "https://opentdb.com/api.php?amount=1&type=multiple"
            ) as resp:
                data = await resp.json(content_type=None)
        except Exception:
            log.exception("Trivia request failed")
            await interaction.followup.send("😴 Trivia is napping — try again shortly.")
            return

        results = data.get("results") if isinstance(data, dict) else None
        if not results:
            await interaction.followup.send("😴 Trivia is napping — try again shortly.")
            return

        q = results[0]
        correct = html.unescape(q["correct_answer"])
        answers = [html.unescape(a) for a in q["incorrect_answers"]] + [correct]
        random.shuffle(answers)
        correct_index = answers.index(correct)

        embed = discord.Embed(
            title="🧠 Trivia",
            description=html.unescape(q["question"]),
            color=discord.Color.blurple(),
        )
        embed.set_footer(
            text=f"{html.unescape(q['category'])} • {q['difficulty'].title()} • 30s to answer"
        )
        await interaction.followup.send(
            embed=embed, view=TriviaView(answers, correct_index)
        )

    @app_commands.command(name="tictactoe", description="Challenge someone to tic-tac-toe.")
    @app_commands.describe(opponent="Who you want to play against")
    async def tictactoe(
        self, interaction: discord.Interaction, opponent: discord.Member
    ) -> None:
        if opponent.bot:
            await interaction.response.send_message(
                "❌ You can't play against a bot.", ephemeral=True
            )
            return
        if opponent.id == interaction.user.id:
            await interaction.response.send_message(
                "❌ You can't play against yourself.", ephemeral=True
            )
            return
        view = TicTacToe(interaction.user, opponent)
        await interaction.response.send_message(content=view.status(), view=view)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Interactive(bot))
