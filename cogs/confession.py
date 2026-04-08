"""
Confession Cog - User confession submission
Handles the /confess command and modal for submissions.
"""

import logging
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

from database.supabase_client import db, DatabaseError
from utils.embeds import (
    success_embed, error_embed, pending_review_embed, info_embed
)
from utils.checks import (
    is_guild_setup, check_user_cooldown, format_duration
)
from utils.filters import check_content_safety, ContentFilter
from utils.constants import Colors, Emojis, Limits

logger = logging.getLogger('confession-bot.confession')


class ConfessionModal(discord.ui.Modal):
    """Modal for submitting a confession."""
    
    def __init__(self, bot: commands.Bot):
        super().__init__(title="Submit Anonymous Confession")
        self.bot = bot
        
        self.content = discord.ui.TextInput(
            label="Your Confession",
            placeholder="Type your anonymous confession here...",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=Limits.MAX_CONFESSION_LENGTH,
            min_length=5
        )
        
        self.category = discord.ui.TextInput(
            label="Category (Optional)",
            placeholder="e.g., Love, School, Secret, Funny...",
            style=discord.TextStyle.short,
            required=False,
            max_length=Limits.MAX_CATEGORY_LENGTH
        )
        
        self.add_item(self.content)
        self.add_item(self.category)
        
    async def on_submit(self, interaction: discord.Interaction):
        """Handle confession submission."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Get guild settings
            settings = await db.get_guild_settings(interaction.guild.id)
            if not settings:
                await interaction.followup.send(
                    embed=error_embed(
                        "This server hasn't been set up yet. Please ask an admin to run `/setup`."
                    ),
                    ephemeral=True
                )
                return
                
            # Check if user is banned
            is_banned = await db.is_user_banned(interaction.guild.id, interaction.user.id)
            if is_banned:
                await interaction.followup.send(
                    embed=error_embed(
                        "You have been banned from submitting confessions on this server."
                    ),
                    ephemeral=True
                )
                return
                
            # Check cooldown
            can_submit, remaining = await check_user_cooldown(
                interaction.guild.id,
                interaction.user.id,
                settings.get('cooldown_seconds', 300)
            )
            if not can_submit:
                await interaction.followup.send(
                    embed=error_embed(
                        f"Please wait **{format_duration(remaining)}** before submitting another confession."
                    ),
                    ephemeral=True
                )
                return
                
            # Get content and category
            content = self.content.value.strip()
            category = self.category.value.strip() if self.category.value else None
            
            # Content safety check
            filter_enabled = settings.get('badword_filter_enabled', False)
            safety_result = await check_content_safety(
                interaction.guild.id,
                content,
                filter_enabled
            )
            
            # Handle spam detection
            if safety_result['spam']:
                await interaction.followup.send(
                    embed=error_embed(
                        f"Your confession was flagged as spam: {safety_result['spam_reason']}"
                    ),
                    ephemeral=True
                )
                return
                
            # Determine filter action
            filter_action = settings.get('filter_action', 'flag')
            filter_flagged = safety_result['badword_match']
            matched_words = safety_result['matched_words']
            
            # If filter is set to reject and bad words found
            if filter_enabled and filter_action == 'reject' and filter_flagged:
                await interaction.followup.send(
                    embed=error_embed(
                        f"Your confession contains inappropriate language and was rejected.\n"
                        f"Matched words: {', '.join(matched_words)}"
                    ),
                    ephemeral=True
                )
                return
                
            # If filter is set to censor, use censored content
            if filter_enabled and filter_action == 'censor' and filter_flagged:
                content = safety_result['censored_content']
                
            # Create confession in database
            confession = await db.create_confession(
                guild_id=interaction.guild.id,
                user_id=interaction.user.id,
                content=content,
                category=category,
                filter_flagged=filter_flagged,
                filter_matched_words=matched_words
            )
            
            if not confession:
                await interaction.followup.send(
                    embed=error_embed(
                        "Failed to save your confession. Please try again later."
                    ),
                    ephemeral=True
                )
                return
                
            # Update cooldown
            await db.update_cooldown(interaction.guild.id, interaction.user.id)
            
            # Send to review channel
            review_channel_id = settings.get('review_channel_id')
            review_channel = interaction.guild.get_channel(review_channel_id)
            
            if not review_channel:
                await interaction.followup.send(
                    embed=error_embed(
                        "Review channel not found. Please contact an admin."
                    ),
                    ephemeral=True
                )
                return
                
            # Create review embed
            review_embed = pending_review_embed(
                confession_id=confession['id'],
                confession_number=confession['confession_number'],
                content=content,
                category=category,
                filter_flagged=filter_flagged,
                matched_words=matched_words
            )
            
            # Create review buttons
            view = ReviewButtons(confession['id'])
            
            # Send to review channel
            review_message = await review_channel.send(
                embed=review_embed,
                view=view
            )
            
            # Save review message ID
            await db.set_review_message_id(confession['id'], review_message.id)
            
            # Send confirmation to user
            confirmation_embed = success_embed(
                title=f"{Emojis.SUCCESS} Confession Submitted!",
                description=(
                    f"Your confession **#{confession['confession_number']}** has been submitted for review.\n\n"
                    f"It will be posted anonymously once approved by an admin."
                )
            )
            
            if filter_flagged:
                confirmation_embed.add_field(
                    name=f"{Emojis.WARNING} Note",
                    value="Your confession was flagged for review due to content filtering.",
                    inline=False
                )
                
            await interaction.followup.send(embed=confirmation_embed, ephemeral=True)
            
            logger.info(
                f"Confession {confession['id']} submitted by user {interaction.user.id} "
                f"in guild {interaction.guild.id}"
            )
            
        except DatabaseError as e:
            logger.error(f"Database error during confession submission: {e}")
            await interaction.followup.send(
                embed=error_embed(
                    "A database error occurred. Please try again later."
                ),
                ephemeral=True
            )
        except Exception as e:
            logger.exception(f"Unexpected error during confession submission: {e}")
            await interaction.followup.send(
                embed=error_embed(
                    "An unexpected error occurred. Please try again later."
                ),
                ephemeral=True
            )
            
    async def on_error(self, interaction: discord.Interaction, error: Exception):
        """Handle modal errors."""
        logger.exception(f"Error in confession modal: {error}")
        await interaction.followup.send(
            embed=error_embed(
                "An error occurred while processing your confession. Please try again."
            ),
            ephemeral=True
        )


class ReviewButtons(discord.ui.View):
    """Buttons for reviewing confessions."""
    
    def __init__(self, confession_id: int):
        super().__init__(timeout=None)  # Persistent buttons
        self.confession_id = confession_id
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Check if user has admin role."""
        # Import here to avoid circular imports
        from utils.checks import has_admin_role
        
        has_role = await has_admin_role(interaction)
        if not has_role:
            await interaction.response.send_message(
                embed=error_embed(
                    "You don't have permission to review confessions."
                ),
                ephemeral=True
            )
            return False
        return True
        
    @discord.ui.button(
        label="Approve",
        style=discord.ButtonStyle.success,
        emoji=Emojis.APPROVE,
        custom_id="confession_approve"
    )
    async def approve_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Approve the confession."""
        # This is handled by the ReviewCog to keep logic centralized
        # We just emit an event or call the review function
        cog = interaction.client.get_cog('ReviewCog')
        if cog:
            await cog.handle_approve(interaction, self.confession_id)
        else:
            await interaction.response.send_message(
                embed=error_embed("Review system is not available."),
                ephemeral=True
            )
            
    @discord.ui.button(
        label="Reject",
        style=discord.ButtonStyle.danger,
        emoji=Emojis.REJECT,
        custom_id="confession_reject"
    )
    async def reject_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Reject the confession."""
        cog = interaction.client.get_cog('ReviewCog')
        if cog:
            await cog.handle_reject(interaction, self.confession_id)
        else:
            await interaction.response.send_message(
                embed=error_embed("Review system is not available."),
                ephemeral=True
            )
            
    @discord.ui.button(
        label="Flag",
        style=discord.ButtonStyle.secondary,
        emoji=Emojis.FLAG,
        custom_id="confession_flag"
    )
    async def flag_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Flag the confession for later review."""
        cog = interaction.client.get_cog('ReviewCog')
        if cog:
            await cog.handle_flag(interaction, self.confession_id)
        else:
            await interaction.response.send_message(
                embed=error_embed("Review system is not available."),
                ephemeral=True
            )


class ConfessionCog(commands.Cog):
    """Cog for confession submissions."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
    @app_commands.command(
        name="confess",
        description="Submit an anonymous confession"
    )
    async def confess_command(self, interaction: discord.Interaction):
        """Open the confession modal."""
        # Check if guild is set up
        if not interaction.guild:
            await interaction.response.send_message(
                embed=error_embed("This command can only be used in a server."),
                ephemeral=True
            )
            return
            
        setup_complete = await is_guild_setup(interaction.guild.id)
        if not setup_complete:
            await interaction.response.send_message(
                embed=error_embed(
                    "This server hasn't been set up yet. Please ask an admin to run `/setup`."
                ),
                ephemeral=True
            )
            return
            
        # Show the modal
        modal = ConfessionModal(self.bot)
        await interaction.response.send_modal(modal)
        
    @app_commands.command(
        name="help",
        description="Show help information about the confession bot"
    )
    async def help_command(self, interaction: discord.Interaction):
        """Show help information."""
        from utils.embeds import help_embed
        await interaction.response.send_message(
            embed=help_embed(),
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    """Add the cog to the bot."""
    await bot.add_cog(ConfessionCog(bot))
    logger.info("ConfessionCog loaded successfully")
