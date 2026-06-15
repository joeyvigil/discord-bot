# Deploying to Fly.io

This bot runs as a single always-on worker (no web server). These steps get it
running 24/7 on Fly.io's free-ish small tier.

## One-time setup

### 1. Install the Fly CLI

```bash
curl -L https://fly.io/install.sh | sh
```

Then open a new terminal (or follow the printed instruction to add `flyctl` to
your PATH).

### 2. Sign up / log in

```bash
fly auth signup   # first time
# or
fly auth login
```

### 3. Create the app

From this project folder:

```bash
fly launch --no-deploy
```

- When asked, **don't** add a database or Redis — this bot needs neither.
- It will detect the `Dockerfile` and `fly.toml`. Accept the existing config
  (or let it tweak the app name / region — both are fine).
- `--no-deploy` lets us set the secret token *before* the first launch.

### 4. Set your bot token as a secret

```bash
fly secrets set DISCORD_TOKEN=your-real-token-here
```

> Do **not** set `DEV_GUILD_ID` in production. Leaving it unset makes the bot
> register commands **globally**, which is what you want once the bot is live.
> (Global command propagation can take up to an hour the first time.)

## Deploy

```bash
fly deploy
```

## Verify it's running

```bash
fly logs        # should show "Loaded cog ...", "Synced N commands", "Logged in as ..."
fly status      # shows the machine state (should be "started")
```

Your bot should appear **online** in Discord. 🎉

## Updating the bot later

After changing code:

```bash
fly deploy
```

That rebuilds and restarts the machine with your new code. No need to manage the
process yourself — Fly restarts it automatically if it ever crashes.

## Handy commands

| Command | What it does |
|---------|--------------|
| `fly logs` | Live logs |
| `fly status` | Machine state |
| `fly secrets list` | Show secret names (not values) |
| `fly apps destroy <app>` | Tear the whole thing down |
