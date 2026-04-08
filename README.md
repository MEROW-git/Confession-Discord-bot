# Anonymous Confession Bot

A Discord bot for anonymous confessions with admin review.

## What It Does

- Users send confessions with `/confess`
- Admins review them in a private channel
- Approved confessions are posted publicly

## What You Need

- Python 3.10+
- A Discord bot token
- A Supabase project

## Quick Setup

### 1. Install packages

```bash
python -m pip install -r requirements.txt
```

### 2. Create a Discord bot

In the Discord Developer Portal:

- Create a new application
- Add a bot
- In the `Bot` tab, enable:
  - `Server Members Intent`
  - `Message Content Intent`
- Copy the bot token

When inviting the bot, give it these permissions:

- `View Channels`
- `Send Messages`
- `Embed Links`
- `Attach Files`
- `Read Message History`
- `Manage Messages`
- `Manage Channels`
- `Manage Roles`
- `Use Slash Commands`

Also include these scopes:

- `bot`
- `applications.commands`

### 3. Set up Supabase

- Create a Supabase project
- Open [database/schema.sql](/e:/bot/confession-bot/database/schema.sql)
- Run that SQL in the Supabase SQL Editor
- Go to `Settings -> API`
- Copy:
  - `Project URL`
  - your server-side secret key

Do not use a `postgresql://...` connection string for this bot.

### 4. Fill in `.env`

Use [.env.example](/e:/bot/confession-bot/.env.example) as a guide.

Required values:

```env
DISCORD_TOKEN=your_discord_bot_token
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_server_secret_key
```

### 5. Run the bot

```bash
python bot.py
```

## First Use

1. Invite the bot to your server
2. Run `/setup`
3. Choose:
   - the public confession channel
   - the private review channel
   - the admin role

## Common Problems

### `PrivilegedIntentsRequired`

Enable these in the Discord Developer Portal `Bot` tab:

- `Server Members Intent`
- `Message Content Intent`

### `SupabaseException: Invalid URL`

Your `SUPABASE_URL` is wrong.

Use:

```env
SUPABASE_URL=https://your-project-ref.supabase.co
```

Do not use:

```env
SUPABASE_URL=postgresql://...
```

### Bot logs in but says `Connected to 0 guilds`

The bot is running, but it has not been invited to any server yet.

## Main Commands

- `/confess` submit a confession
- `/setup` configure the bot in a server
- `/settings` view server settings
- `/pending` view pending confessions

## Notes

- The warnings about `PyNaCl` and voice support can be ignored for this bot
- Keep your Supabase secret key private
