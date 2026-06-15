# Small, stable base image. discord.py runs fine on Python 3.12.
FROM python:3.12-slim

# Don't buffer stdout/stderr so logs show up immediately in `fly logs`.
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies first so this layer is cached when only code changes.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the bot.
COPY . .

# The bot is a long-running worker (no web server / no ports to expose).
CMD ["python", "bot.py"]
