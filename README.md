# 🤫 Anonymous Confession Bot

A production-ready Discord bot for anonymous confession submissions with admin review, multi-server support, and comprehensive moderation features.

## Features

- **🔒 Anonymous Submissions** - Users submit confessions that are reviewed before posting
- **✅ Admin Review System** - Approve, reject, or flag confessions with button controls
- **🏢 Multi-Server Support** - Each Discord server has independent settings
- **🛡️ Bad Word Filter** - Configurable content filtering with multiple actions
- **⏱️ Cooldown System** - Prevent spam with configurable per-user cooldowns
- **🔨 User Moderation** - Ban/unban users from submitting confessions
- **📊 Statistics** - Track confession counts and review metrics
- **🎨 Clean Embeds** - Professional-looking messages with Discord embeds

## Folder Structure

```
confession-bot/
├── bot.py                      # Main entry point
├── cogs/                       # Command modules
│   ├── confession.py          # User confession submission
│   ├── review.py              # Admin review system
│   ├── setup.py               # Server configuration
│   ├── settings.py            # Bot settings management
│   └── moderation.py          # User banning/moderation
├── database/                   # Database layer
│   ├── supabase_client.py     # Supabase client and operations
│   └── schema.sql             # Database schema
├── utils/                      # Utilities
│   ├── embeds.py              # Embed templates
│   ├── checks.py              # Permission checks
│   ├── filters.py             # Content filtering
│   └── constants.py           # Constants and enums
├── .env.example               # Environment variables template
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## Installation

### 1. Clone or Download

```bash
cd confession-bot
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Create Discord Bot

1. Go to [Discord Developer Portal](https://discord.com/developers/applications)
2. Click "New Application" and give it a name
3. Go to "Bot" section and click "Add Bot"
4. Enable these **Privileged Gateway Intents**:
   - ✅ Server Members Intent
   - ✅ Message Content Intent
5. Copy the **Token** (you'll need it for `.env`)
6. Go to "OAuth2" → "URL Generator"
7. Select scopes:
   - ✅ `bot`
   - ✅ `applications.commands`
8. Select bot permissions:
   - ✅ Send Messages
   - ✅ Embed Links
   - ✅ Attach Files
   - ✅ Read Message History
   - ✅ Manage Messages
   - ✅ Manage Channels (for review channel setup)
   - ✅ Manage Roles (for review channel permissions)
   - ✅ View Channels
9. Copy the generated URL and use it to invite the bot

### 4. Set Up Supabase

1. Go to [Supabase](https://supabase.com/) and create an account
2. Create a new project
3. Go to the **SQL Editor**
4. Open `database/schema.sql` from this project
5. Copy the entire contents and paste into the SQL Editor
6. Click "Run" to create all tables
7. Go to **Project Settings** → **API**
8. Copy:
   - **Project URL** (for `SUPABASE_URL`)
   - **service_role key** (for `SUPABASE_SERVICE_ROLE_KEY`)

> ⚠️ **Important**: Never share or expose the `service_role_key`. It has full database access.

### 5. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your values:

```env
DISCORD_TOKEN=your_discord_bot_token_here
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here
```

## Running the Bot

### Local Development

```bash
python bot.py
```

### Production (Recommended)

Use a process manager like `pm2` or `systemd`:

```bash
# Using pm2
pm2 start bot.py --name confession-bot --interpreter python3

# Using systemd (create a service file)
sudo systemctl enable confession-bot
sudo systemctl start confession-bot
```

## Commands

### User Commands

| Command | Description |
|---------|-------------|
| `/confess` | Submit an anonymous confession |
| `/help` | Show help information |
| `/stats` | View confession statistics |

### Admin Commands

| Command | Description | Permission |
|---------|-------------|------------|
| `/setup` | Configure confession and review channels | Administrator |
| `/settings` | View current settings | Admin Role |
| `/toggle_badword_filter` | Enable/disable filter | Admin Role |
| `/set_filter_action` | Set filter action (flag/reject/censor) | Admin Role |
| `/add_badword` | Add word to filter | Admin Role |
| `/remove_badword` | Remove word from filter | Admin Role |
| `/list_badwords` | List all blocked words | Admin Role |
| `/set_cooldown` | Set submission cooldown | Admin Role |
| `/ban_confess_user` | Ban user from submitting | Admin Role |
| `/unban_confess_user` | Unban a user | Admin Role |
| `/unban_confess_user_by_id` | Unban by user ID | Admin Role |
| `/list_banned_users` | List banned users | Admin Role |
| `/check_ban_status` | Check if user is banned | Admin Role |
| `/pending` | View pending confessions | Administrator |

## Setup Flow

1. **Invite bot** to your server with required permissions
2. **Run `/setup`** with:
   - Public confession channel (where approved confessions appear)
   - Private review channel (for admin review)
   - Admin role (who can review confessions)
3. **Bot configures permissions** on review channel automatically
4. **Users submit** with `/confess`
5. **Admins review** in the review channel with buttons
6. **Approved confessions** appear anonymously in public channel

## Multi-Server Support

The bot is designed to work across multiple Discord servers simultaneously:

- Each server has **independent settings** stored by `guild_id`
- **Separate confession counters** per server
- **Independent** word filters, cooldowns, and banned users
- **Isolated review channels** and admin roles

## Database Schema

### Tables

| Table | Purpose |
|-------|---------|
| `guild_settings` | Server configuration |
| `confessions` | All confession submissions |
| `blocked_words` | Bad word filter list |
| `banned_users` | Banned user list |
| `user_cooldowns` | Cooldown tracking |

### Key Fields

**confessions table:**
- `id` - Unique confession ID
- `confession_number` - Per-server confession number (for display)
- `guild_id` - Discord server ID
- `user_id` - Anonymous user ID (kept private)
- `content` - Confession text
- `status` - pending/approved/rejected/flagged
- `filter_flagged` - Whether filter caught bad words

## Security & Privacy

- **User IDs are stored** in database for moderation purposes
- **Public posts are anonymous** - no user info is revealed
- **Review channel is private** - only admins can see pending confessions
- **Service role key** should never be exposed publicly
- **Row Level Security** is enabled on all tables

## Bad Word Filter Actions

| Action | Behavior |
|--------|----------|
| **Flag** | Confession goes to review with warning |
| **Reject** | Confession is immediately rejected |
| **Censor** | Bad words are replaced with `***` |

## Troubleshooting

### Bot doesn't respond to commands
- Check that bot has `applications.commands` scope
- Re-invite with correct permissions
- Check console for errors

### Database connection errors
- Verify `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`
- Check Supabase project is active
- Ensure database schema is applied

### Review channel not working
- Bot needs `Manage Channels` and `Manage Permissions`
- Admin role must be below bot's highest role
- Verify channel IDs in database

### Slash commands not appearing
- Commands can take up to 1 hour to sync globally
- In development, they sync immediately
- Re-invite bot if issues persist

## Required Bot Permissions

| Permission | Why It's Needed |
|------------|-----------------|
| Send Messages | Post confessions |
| Embed Links | Create rich embeds |
| Read Message History | Update review messages |
| Manage Messages | Edit review messages |
| Manage Channels | Setup review channel |
| Manage Permissions | Configure review channel privacy |
| View Channels | Access configured channels |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DISCORD_TOKEN` | Yes | Discord bot token |
| `SUPABASE_URL` | Yes | Supabase project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | Supabase service role key |
| `DEFAULT_COOLDOWN` | No | Default cooldown (300s) |
| `MAX_CONFESSION_LENGTH` | No | Max characters (2000) |
| `BOT_STATUS` | No | Bot activity status |
| `ENVIRONMENT` | No | development/production |

## License

MIT License - Feel free to use and modify for your community.

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review the logs in `bot.log`
3. Check database connections
4. Verify all permissions are correct

---

**Happy confessing!** 🤫
