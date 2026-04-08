#!/usr/bin/env python3
"""
Anonymous Confession Bot - Main Entry Point
A Discord bot for anonymous confession submissions with admin review.

Features:
- Multi-server support
- Admin review system with approve/reject/flag
- Bad word filtering
- Cooldown and anti-spam
- User banning
"""

import asyncio
import logging
import os
import sys
from pathlib import Path

import discord
from discord.ext import commands
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger('confession-bot')

# Bot configuration
class BotConfig:
    """Bot configuration constants."""
    DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_SERVICE_ROLE_KEY = os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    DEFAULT_COOLDOWN = int(os.getenv('DEFAULT_COOLDOWN', '300'))
    MAX_CONFESSION_LENGTH = int(os.getenv('MAX_CONFESSION_LENGTH', '2000'))
    DEFAULT_FILTER_ACTION = os.getenv('DEFAULT_FILTER_ACTION', 'flag')
    BOT_STATUS = os.getenv('BOT_STATUS', 'Anonymous Confessions')
    ENVIRONMENT = os.getenv('ENVIRONMENT', 'development')


class ConfessionBot(commands.Bot):
    """Main bot class with multi-server support."""
    
    def __init__(self):
        # Set up intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        
        super().__init__(
            command_prefix='!',  # Prefix commands (slash commands are primary)
            intents=intents,
            help_command=None,  # Disable default help, use slash commands
            activity=discord.Activity(
                type=discord.ActivityType.listening,
                name=BotConfig.BOT_STATUS
            ),
            status=discord.Status.online
        )
        
        self.config = BotConfig
        self.start_time = None
        
    async def setup_hook(self):
        """Load cogs and setup the bot."""
        self.start_time = discord.utils.utcnow()
        
        # Load all cogs
        await self.load_cogs()
        
        # Sync slash commands
        if self.config.ENVIRONMENT == 'development':
            # Sync to test guild only in development (faster)
            logger.info("Development mode: Syncing commands globally...")
            await self.tree.sync()
        else:
            # Sync globally in production (takes up to 1 hour)
            logger.info("Production mode: Syncing commands globally...")
            await self.tree.sync()
            
        logger.info(f"Loaded {len(self.cogs)} cogs successfully")
        
    async def load_cogs(self):
        """Load all cog extensions."""
        cogs_dir = Path(__file__).parent / 'cogs'
        
        if not cogs_dir.exists():
            logger.error(f"Cogs directory not found: {cogs_dir}")
            return
            
        for cog_file in cogs_dir.glob('*.py'):
            if cog_file.name.startswith('_'):
                continue
                
            cog_name = f"cogs.{cog_file.stem}"
            try:
                await self.load_extension(cog_name)
                logger.info(f"Loaded cog: {cog_name}")
            except Exception as e:
                logger.error(f"Failed to load cog {cog_name}: {e}")
                
    async def on_ready(self):
        """Called when the bot is ready."""
        logger.info(f"Bot logged in as {self.user} (ID: {self.user.id})")
        logger.info(f"Connected to {len(self.guilds)} guilds")
        logger.info(f"Serving {sum(g.member_count for g in self.guilds)} members")
        
        # Log connected guilds
        for guild in self.guilds:
            logger.info(f"  - {guild.name} (ID: {guild.id}, Members: {guild.member_count})")
            
    async def on_guild_join(self, guild: discord.Guild):
        """Called when the bot joins a new guild."""
        logger.info(f"Joined new guild: {guild.name} (ID: {guild.id})")
        
        # Try to find a system channel to send setup message
        system_channel = guild.system_channel
        if system_channel and system_channel.permissions_for(guild.me).send_messages:
            embed = discord.Embed(
                title="👋 Thanks for adding Anonymous Confession Bot!",
                description=(
                    "To get started, an admin needs to run the `/setup` command "
                    "to configure the confession and review channels.\n\n"
                    "**Quick Start:**\n"
                    "1. Run `/setup` to configure channels\n"
                    "2. Set admin role with the command\n"
                    "3. Users can start submitting with `/confess`\n\n"
                    "Use `/help` for more information."
                ),
                color=discord.Color.green()
            )
            try:
                await system_channel.send(embed=embed)
            except discord.Forbidden:
                pass
                
    async def on_guild_remove(self, guild: discord.Guild):
        """Called when the bot leaves a guild."""
        logger.info(f"Left guild: {guild.name} (ID: {guild.id})")
        
    async def on_error(self, event_method: str, *args, **kwargs):
        """Handle global errors."""
        logger.exception(f"Error in {event_method}")
        
    async def close(self):
        """Clean up when bot shuts down."""
        logger.info("Shutting down bot...")
        await super().close()


def validate_config():
    """Validate required environment variables."""
    required_vars = [
        ('DISCORD_TOKEN', BotConfig.DISCORD_TOKEN),
        ('SUPABASE_URL', BotConfig.SUPABASE_URL),
        ('SUPABASE_SERVICE_ROLE_KEY', BotConfig.SUPABASE_SERVICE_ROLE_KEY),
    ]
    
    missing = [name for name, value in required_vars if not value]
    
    if missing:
        logger.error("Missing required environment variables:")
        for var in missing:
            logger.error(f"  - {var}")
        logger.error("\nPlease copy .env.example to .env and fill in your values.")
        return False
        
    return True


def main():
    """Main entry point."""
    # Validate configuration
    if not validate_config():
        sys.exit(1)
        
    # Create and run bot
    bot = ConfessionBot()
    
    try:
        bot.run(BotConfig.DISCORD_TOKEN, reconnect=True)
    except discord.LoginFailure:
        logger.error("Invalid Discord token. Please check your DISCORD_TOKEN.")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
