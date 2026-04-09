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
- Run the full SQL from that file in the Supabase SQL Editor before starting the bot
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

Important:

- You must run [database/schema.sql](/e:/bot/confession-bot/database/schema.sql) in Supabase SQL Editor first
- If you skip that step, commands like `/setup` and `/confess` will fail because the required tables do not exist

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

## Commands

- `/setup` : configure the confession channel, review channel, and admin role
- `/confess` : submit an anonymous confession for admin review
- `/help` : show help information about the bot
- `/pending` : view pending confessions waiting for review
- `/stats` : view confession statistics for the server
- `/settings` : view the current bot settings
- `/toggle_badword_filter` : enable or disable the bad word filter
- `/set_filter_action` : choose whether filtered confessions are flagged, rejected, or censored
- `/add_badword` : add a word to the bad word filter
- `/remove_badword` : remove a word from the bad word filter
- `/list_badwords` : list all blocked words
- `/set_cooldown` : set how long users must wait between confessions
- `/ban_confess_user` : ban a user from sending confessions
- `/unban_confess_user` : unban a server member from sending confessions
- `/unban_confess_user_by_id` : unban a user by Discord ID
- `/list_banned_users` : list all users banned from confessions
- `/check_ban_status` : check whether a user is banned from confessions

Approval actions are handled from buttons in the review channel:

- `Approve` : post the confession publicly
- `Reject` : reject the confession
- `Flag` : mark the confession for later review

## Notes

- The warnings about `PyNaCl` and voice support can be ignored for this bot
- Keep your Supabase secret key private
