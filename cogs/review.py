"""
Review Cog - Admin review system
Handles approve/reject/flag actions for confessions.
"""

import logging
from datetime import datetime

import discord
from discord import app_commands
from discord.ext import commands

from database.supabase_client import db, DatabaseError
from utils.embeds import (
    success_embed, error_embed, public_confession_embed, review_decision_embed
)
from utils.checks import has_admin_role
from utils.constants import Colors, Emojis

logger = logging.getLogger('confession-bot.review')


class ReviewCog(commands.Cog):
    """Cog for confession review and moderation."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
    async def handle_approve(self, interaction: discord.Interaction, confession_id: int):
        """Handle approving a confession."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Get confession
            confession = await db.get_confession(confession_id)
            if not confession:
                await interaction.followup.send(
                    embed=error_embed("Confession not found."),
                    ephemeral=True
                )
                return
                
            # Check if already processed
            if confession['status'] != 'pending':
                await interaction.followup.send(
                    embed=error_embed(
                        f"This confession has already been **{confession['status']}**."
                    ),
                    ephemeral=True
                )
                return
                
            # Get guild settings
            settings = await db.get_guild_settings(confession['guild_id'])
            if not settings:
                await interaction.followup.send(
                    embed=error_embed("Guild settings not found."),
                    ephemeral=True
                )
                return
                
            # Get confession channel
            confession_channel_id = settings.get('confession_channel_id')
            confession_channel = self.bot.get_channel(confession_channel_id)
            
            if not confession_channel:
                await interaction.followup.send(
                    embed=error_embed(
                        f"Confession channel not found. It may have been deleted."
                    ),
                    ephemeral=True
                )
                return
                
            # Create public confession embed
            public_embed = public_confession_embed(
                confession_number=confession['confession_number'],
                content=confession['content'],
                category=confession.get('category'),
                timestamp=datetime.utcnow()
            )
            
            # Post to public channel
            public_message = await confession_channel.send(embed=public_embed)
            
            # Update confession status
            await db.update_confession_status(
                confession_id=confession_id,
                status='approved',
                reviewed_by=interaction.user.id,
                public_message_id=public_message.id
            )
            
            # Update review message
            review_message_id = confession.get('review_message_id')
            if review_message_id:
                try:
                    review_channel_id = settings.get('review_channel_id')
                    review_channel = self.bot.get_channel(review_channel_id)
                    if review_channel:
                        review_message = await review_channel.fetch_message(review_message_id)
                        
                        # Create decision embed
                        decision_embed = review_decision_embed(
                            confession_id=confession_id,
                            confession_number=confession['confession_number'],
                            decision='approved',
                            decided_by=interaction.user.mention
                        )
                        
                        # Disable buttons and update message
                        await review_message.edit(
                            embeds=[review_message.embeds[0], decision_embed],
                            view=None  # Remove buttons
                        )
                except discord.NotFound:
                    logger.warning(f"Review message {review_message_id} not found")
                except discord.Forbidden:
                    logger.warning(f"Cannot edit review message {review_message_id}")
                    
            # Confirm to admin
            await interaction.followup.send(
                embed=success_embed(
                    f"Confession **#{confession['confession_number']}** has been approved and posted to {confession_channel.mention}."
                ),
                ephemeral=True
            )
            
            logger.info(
                f"Confession {confession_id} approved by {interaction.user.id} "
                f"in guild {confession['guild_id']}"
            )
            
        except DatabaseError as e:
            logger.error(f"Database error during approval: {e}")
            await interaction.followup.send(
                embed=error_embed("A database error occurred. Please try again later."),
                ephemeral=True
            )
        except Exception as e:
            logger.exception(f"Unexpected error during approval: {e}")
            await interaction.followup.send(
                embed=error_embed("An unexpected error occurred. Please try again later."),
                ephemeral=True
            )
            
    async def handle_reject(self, interaction: discord.Interaction, confession_id: int):
        """Handle rejecting a confession."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Get confession
            confession = await db.get_confession(confession_id)
            if not confession:
                await interaction.followup.send(
                    embed=error_embed("Confession not found."),
                    ephemeral=True
                )
                return
                
            # Check if already processed
            if confession['status'] != 'pending':
                await interaction.followup.send(
                    embed=error_embed(
                        f"This confession has already been **{confession['status']}**."
                    ),
                    ephemeral=True
                )
                return
                
            # Update confession status
            await db.update_confession_status(
                confession_id=confession_id,
                status='rejected',
                reviewed_by=interaction.user.id
            )
            
            # Update review message
            settings = await db.get_guild_settings(confession['guild_id'])
            review_message_id = confession.get('review_message_id')
            
            if review_message_id and settings:
                try:
                    review_channel_id = settings.get('review_channel_id')
                    review_channel = self.bot.get_channel(review_channel_id)
                    if review_channel:
                        review_message = await review_channel.fetch_message(review_message_id)
                        
                        # Create decision embed
                        decision_embed = review_decision_embed(
                            confession_id=confession_id,
                            confession_number=confession['confession_number'],
                            decision='rejected',
                            decided_by=interaction.user.mention
                        )
                        
                        # Disable buttons and update message
                        await review_message.edit(
                            embeds=[review_message.embeds[0], decision_embed],
                            view=None
                        )
                except discord.NotFound:
                    logger.warning(f"Review message {review_message_id} not found")
                except discord.Forbidden:
                    logger.warning(f"Cannot edit review message {review_message_id}")
                    
            # Confirm to admin
            await interaction.followup.send(
                embed=success_embed(
                    f"Confession **#{confession['confession_number']}** has been rejected."
                ),
                ephemeral=True
            )
            
            logger.info(
                f"Confession {confession_id} rejected by {interaction.user.id} "
                f"in guild {confession['guild_id']}"
            )
            
        except DatabaseError as e:
            logger.error(f"Database error during rejection: {e}")
            await interaction.followup.send(
                embed=error_embed("A database error occurred. Please try again later."),
                ephemeral=True
            )
        except Exception as e:
            logger.exception(f"Unexpected error during rejection: {e}")
            await interaction.followup.send(
                embed=error_embed("An unexpected error occurred. Please try again later."),
                ephemeral=True
            )
            
    async def handle_flag(self, interaction: discord.Interaction, confession_id: int):
        """Handle flagging a confession."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Get confession
            confession = await db.get_confession(confession_id)
            if not confession:
                await interaction.followup.send(
                    embed=error_embed("Confession not found."),
                    ephemeral=True
                )
                return
                
            # Check if already processed
            if confession['status'] != 'pending':
                await interaction.followup.send(
                    embed=error_embed(
                        f"This confession has already been **{confession['status']}**."
                    ),
                    ephemeral=True
                )
                return
                
            # Update confession status
            await db.update_confession_status(
                confession_id=confession_id,
                status='flagged',
                reviewed_by=interaction.user.id
            )
            
            # Update review message
            settings = await db.get_guild_settings(confession['guild_id'])
            review_message_id = confession.get('review_message_id')
            
            if review_message_id and settings:
                try:
                    review_channel_id = settings.get('review_channel_id')
                    review_channel = self.bot.get_channel(review_channel_id)
                    if review_channel:
                        review_message = await review_channel.fetch_message(review_message_id)
                        
                        # Create decision embed
                        decision_embed = review_decision_embed(
                            confession_id=confession_id,
                            confession_number=confession['confession_number'],
                            decision='flagged',
                            decided_by=interaction.user.mention,
                            reason="Flagged for further review by admin team"
                        )
                        
                        # Disable buttons and update message
                        await review_message.edit(
                            embeds=[review_message.embeds[0], decision_embed],
                            view=None
                        )
                except discord.NotFound:
                    logger.warning(f"Review message {review_message_id} not found")
                except discord.Forbidden:
                    logger.warning(f"Cannot edit review message {review_message_id}")
                    
            # Confirm to admin
            await interaction.followup.send(
                embed=success_embed(
                    f"Confession **#{confession['confession_number']}** has been flagged for later review."
                ),
                ephemeral=True
            )
            
            logger.info(
                f"Confession {confession_id} flagged by {interaction.user.id} "
                f"in guild {confession['guild_id']}"
            )
            
        except DatabaseError as e:
            logger.error(f"Database error during flagging: {e}")
            await interaction.followup.send(
                embed=error_embed("A database error occurred. Please try again later."),
                ephemeral=True
            )
        except Exception as e:
            logger.exception(f"Unexpected error during flagging: {e}")
            await interaction.followup.send(
                embed=error_embed("An unexpected error occurred. Please try again later."),
                ephemeral=True
            )
            
    @app_commands.command(
        name="pending",
        description="View all pending confessions (Admin only)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def pending_command(self, interaction: discord.Interaction):
        """Show list of pending confessions."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            pending = await db.get_pending_confessions(interaction.guild.id)
            
            if not pending:
                await interaction.followup.send(
                    embed=info_embed(
                        title=f"{Emojis.PENDING} Pending Confessions",
                        description="There are no pending confessions at this time."
                    ),
                    ephemeral=True
                )
                return
                
            embed = discord.Embed(
                title=f"{Emojis.PENDING} Pending Confessions",
                description=f"Total pending: {len(pending)}",
                color=Colors.PENDING
            )
            
            for confession in pending[:10]:  # Show first 10
                content_preview = confession['content'][:100]
                if len(confession['content']) > 100:
                    content_preview += "..."
                    
                embed.add_field(
                    name=f"Confession #{confession['confession_number']} (ID: {confession['id']})",
                    value=f"```{content_preview}```",
                    inline=False
                )
                
            if len(pending) > 10:
                embed.set_footer(text=f"Showing 10 of {len(pending)} pending confessions")
                
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except DatabaseError as e:
            logger.error(f"Database error getting pending confessions: {e}")
            await interaction.followup.send(
                embed=error_embed("A database error occurred. Please try again later."),
                ephemeral=True
            )
            
    @app_commands.command(
        name="stats",
        description="View confession statistics for this server"
    )
    async def stats_command(self, interaction: discord.Interaction):
        """Show confession statistics."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            stats = await db.get_confession_stats(interaction.guild.id)
            
            embed = discord.Embed(
                title=f"{Emojis.INFO} Confession Statistics",
                description=f"Statistics for **{interaction.guild.name}**",
                color=Colors.INFO
            )
            
            embed.add_field(
                name="Total Confessions",
                value=str(stats['total']),
                inline=True
            )
            embed.add_field(
                name=f"{Emojis.PENDING} Pending",
                value=str(stats['pending']),
                inline=True
            )
            embed.add_field(
                name=f"{Emojis.APPROVE} Approved",
                value=str(stats['approved']),
                inline=True
            )
            embed.add_field(
                name=f"{Emojis.REJECT} Rejected",
                value=str(stats['rejected']),
                inline=True
            )
            embed.add_field(
                name=f"{Emojis.FLAG} Flagged",
                value=str(stats['flagged']),
                inline=True
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except DatabaseError as e:
            logger.error(f"Database error getting stats: {e}")
            await interaction.followup.send(
                embed=error_embed("A database error occurred. Please try again later."),
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    """Add the cog to the bot."""
    await bot.add_cog(ReviewCog(bot))
    logger.info("ReviewCog loaded successfully")
