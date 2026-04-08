"""
Settings Cog - Bot configuration management
Handles filter settings, cooldown, and other configurations.
"""

import logging

import discord
from discord import app_commands
from discord.ext import commands

from database.supabase_client import db, DatabaseError
from utils.embeds import success_embed, error_embed, settings_embed, badword_list_embed
from utils.checks import require_admin_role, require_setup
from utils.filters import ContentFilter
from utils.constants import Emojis, Limits, FilterAction

logger = logging.getLogger('confession-bot.settings')


class SettingsCog(commands.Cog):
    """Cog for managing bot settings."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
    @app_commands.command(
        name="settings",
        description="View current bot settings (Admin only)"
    )
    @require_admin_role()
    async def settings_command(self, interaction: discord.Interaction):
        """Display current guild settings."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            settings = await db.get_guild_settings(interaction.guild.id)
            
            if not settings:
                await interaction.followup.send(
                    embed=error_embed(
                        "This server hasn't been set up yet. Please run `/setup` first."
                    ),
                    ephemeral=True
                )
                return
                
            # Get channel and role objects
            confession_channel = interaction.guild.get_channel(
                settings.get('confession_channel_id')
            )
            review_channel = interaction.guild.get_channel(
                settings.get('review_channel_id')
            )
            admin_role = interaction.guild.get_role(
                settings.get('admin_role_id')
            )
            
            embed = settings_embed(
                guild_name=interaction.guild.name,
                confession_channel=confession_channel,
                review_channel=review_channel,
                admin_role=admin_role,
                badword_filter=settings.get('badword_filter_enabled', False),
                cooldown=settings.get('cooldown_seconds', 300),
                filter_action=settings.get('filter_action', 'flag')
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except DatabaseError as e:
            logger.error(f"Database error getting settings: {e}")
            await interaction.followup.send(
                embed=error_embed("A database error occurred. Please try again later."),
                ephemeral=True
            )
            
    @app_commands.command(
        name="toggle_badword_filter",
        description="Enable or disable the bad word filter (Admin only)"
    )
    @app_commands.describe(
        enabled="Whether to enable or disable the filter"
    )
    @require_admin_role()
    async def toggle_filter_command(
        self,
        interaction: discord.Interaction,
        enabled: bool
    ):
        """Toggle the bad word filter."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            await db.update_guild_settings(
                interaction.guild.id,
                badword_filter_enabled=enabled
            )
            
            status = "enabled" if enabled else "disabled"
            await interaction.followup.send(
                embed=success_embed(
                    f"{Emojis.FILTER} Bad word filter has been **{status}**."
                ),
                ephemeral=True
            )
            
            logger.info(
                f"Bad word filter {status} in guild {interaction.guild.id} by {interaction.user.id}"
            )
            
        except DatabaseError as e:
            logger.error(f"Database error toggling filter: {e}")
            await interaction.followup.send(
                embed=error_embed("A database error occurred. Please try again later."),
                ephemeral=True
            )
            
    @app_commands.command(
        name="set_filter_action",
        description="Set what happens when bad words are detected (Admin only)"
    )
    @app_commands.describe(
        action="The action to take when bad words are found"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Flag for review", value="flag"),
        app_commands.Choice(name="Reject immediately", value="reject"),
        app_commands.Choice(name="Censor and post", value="censor")
    ])
    @require_admin_role()
    async def set_filter_action_command(
        self,
        interaction: discord.Interaction,
        action: app_commands.Choice[str]
    ):
        """Set the filter action."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            await db.update_guild_settings(
                interaction.guild.id,
                filter_action=action.value
            )
            
            descriptions = {
                'flag': "Confessions with bad words will be flagged for admin review",
                'reject': "Confessions with bad words will be immediately rejected",
                'censor': "Bad words will be censored and the confession will be posted"
            }
            
            await interaction.followup.send(
                embed=success_embed(
                    f"{Emojis.FILTER} Filter action set to **{action.name}**.\n"
                    f"{descriptions[action.value]}"
                ),
                ephemeral=True
            )
            
        except DatabaseError as e:
            logger.error(f"Database error setting filter action: {e}")
            await interaction.followup.send(
                embed=error_embed("A database error occurred. Please try again later."),
                ephemeral=True
            )
            
    @app_commands.command(
        name="add_badword",
        description="Add a word to the bad word filter (Admin only)"
    )
    @app_commands.describe(
        word="The word to add to the filter"
    )
    @require_admin_role()
    async def add_badword_command(
        self,
        interaction: discord.Interaction,
        word: str
    ):
        """Add a word to the bad word filter."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Validate word
            word = word.lower().strip()
            if not word or len(word) < 2:
                await interaction.followup.send(
                    embed=error_embed("Please provide a valid word (at least 2 characters)."),
                    ephemeral=True
                )
                return
                
            if len(word) > Limits.MAX_BADWORD_LENGTH:
                await interaction.followup.send(
                    embed=error_embed(f"Word is too long (max {Limits.MAX_BADWORD_LENGTH} characters)."),
                    ephemeral=True
                )
                return
                
            # Check limit
            existing_words = await db.get_blocked_words(interaction.guild.id)
            if len(existing_words) >= Limits.MAX_BADWORDS_PER_GUILD:
                await interaction.followup.send(
                    embed=error_embed(
                        f"Maximum number of blocked words reached ({Limits.MAX_BADWORDS_PER_GUILD})."
                    ),
                    ephemeral=True
                )
                return
                
            # Add word
            await db.add_blocked_word(interaction.guild.id, word, interaction.user.id)
            
            # Clear cache
            filter_obj = ContentFilter(interaction.guild.id)
            filter_obj.clear_cache()
            
            await interaction.followup.send(
                embed=success_embed(
                    f"{Emojis.FILTER} Added **'{word}'** to the bad word filter."
                ),
                ephemeral=True
            )
            
            logger.info(
                f"Word '{word}' added to filter in guild {interaction.guild.id} by {interaction.user.id}"
            )
            
        except Exception as e:
            if "already in the blocked list" in str(e):
                await interaction.followup.send(
                    embed=error_embed(f"'{word}' is already in the filter."),
                    ephemeral=True
                )
            else:
                logger.error(f"Error adding bad word: {e}")
                await interaction.followup.send(
                    embed=error_embed("An error occurred. Please try again later."),
                    ephemeral=True
                )
                
    @app_commands.command(
        name="remove_badword",
        description="Remove a word from the bad word filter (Admin only)"
    )
    @app_commands.describe(
        word="The word to remove from the filter"
    )
    @require_admin_role()
    async def remove_badword_command(
        self,
        interaction: discord.Interaction,
        word: str
    ):
        """Remove a word from the bad word filter."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            word = word.lower().strip()
            await db.remove_blocked_word(interaction.guild.id, word)
            
            # Clear cache
            filter_obj = ContentFilter(interaction.guild.id)
            filter_obj.clear_cache()
            
            await interaction.followup.send(
                embed=success_embed(
                    f"{Emojis.FILTER} Removed **'{word}'** from the bad word filter."
                ),
                ephemeral=True
            )
            
            logger.info(
                f"Word '{word}' removed from filter in guild {interaction.guild.id} by {interaction.user.id}"
            )
            
        except DatabaseError as e:
            logger.error(f"Database error removing bad word: {e}")
            await interaction.followup.send(
                embed=error_embed("A database error occurred. Please try again later."),
                ephemeral=True
            )
            
    @app_commands.command(
        name="list_badwords",
        description="List all blocked words (Admin only)"
    )
    @require_admin_role()
    async def list_badwords_command(self, interaction: discord.Interaction):
        """List all blocked words."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            words = await db.get_blocked_words(interaction.guild.id)
            embed = badword_list_embed(interaction.guild.name, words)
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except DatabaseError as e:
            logger.error(f"Database error listing bad words: {e}")
            await interaction.followup.send(
                embed=error_embed("A database error occurred. Please try again later."),
                ephemeral=True
            )
            
    @app_commands.command(
        name="set_cooldown",
        description="Set the cooldown between confessions (Admin only)"
    )
    @app_commands.describe(
        seconds="Cooldown duration in seconds (10-86400)"
    )
    @require_admin_role()
    async def set_cooldown_command(
        self,
        interaction: discord.Interaction,
        seconds: app_commands.Range[int, 10, 86400]
    ):
        """Set the confession cooldown."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            await db.update_guild_settings(
                interaction.guild.id,
                cooldown_seconds=seconds
            )
            
            # Format duration nicely
            if seconds < 60:
                duration_str = f"{seconds} seconds"
            elif seconds < 3600:
                minutes = seconds // 60
                duration_str = f"{minutes} minute{'s' if minutes != 1 else ''}"
            else:
                hours = seconds // 3600
                remaining_minutes = (seconds % 3600) // 60
                if remaining_minutes > 0:
                    duration_str = f"{hours} hour{'s' if hours != 1 else ''} {remaining_minutes} min"
                else:
                    duration_str = f"{hours} hour{'s' if hours != 1 else ''}"
                    
            await interaction.followup.send(
                embed=success_embed(
                    f"{Emojis.COOLDOWN} Cooldown set to **{duration_str}**.\n"
                    f"Users must wait this long between confessions."
                ),
                ephemeral=True
            )
            
            logger.info(
                f"Cooldown set to {seconds}s in guild {interaction.guild.id} by {interaction.user.id}"
            )
            
        except DatabaseError as e:
            logger.error(f"Database error setting cooldown: {e}")
            await interaction.followup.send(
                embed=error_embed("A database error occurred. Please try again later."),
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    """Add the cog to the bot."""
    await bot.add_cog(SettingsCog(bot))
    logger.info("SettingsCog loaded successfully")
