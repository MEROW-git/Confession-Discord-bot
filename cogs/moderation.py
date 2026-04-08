"""
Moderation Cog - User banning and moderation tools
Handles banning users from submitting confessions.
"""

import logging

import discord
from discord import app_commands
from discord.ext import commands

from database.supabase_client import db, DatabaseError
from utils.embeds import success_embed, error_embed, banned_list_embed
from utils.checks import require_admin_role
from utils.constants import Emojis, Limits

logger = logging.getLogger('confession-bot.moderation')


class ModerationCog(commands.Cog):
    """Cog for moderation commands."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        
    @app_commands.command(
        name="ban_confess_user",
        description="Ban a user from submitting confessions (Admin only)"
    )
    @app_commands.describe(
        user="The user to ban from submitting confessions",
        reason="Optional reason for the ban"
    )
    @require_admin_role()
    async def ban_user_command(
        self,
        interaction: discord.Interaction,
        user: discord.Member,
        reason: str = None
    ):
        """Ban a user from submitting confessions."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Check if trying to ban self
            if user.id == interaction.user.id:
                await interaction.followup.send(
                    embed=error_embed("You cannot ban yourself!"),
                    ephemeral=True
                )
                return
                
            # Check if trying to ban an admin
            settings = await db.get_guild_settings(interaction.guild.id)
            if settings:
                admin_role_id = settings.get('admin_role_id')
                admin_role = interaction.guild.get_role(admin_role_id)
                if admin_role and admin_role in user.roles:
                    await interaction.followup.send(
                        embed=error_embed("You cannot ban a user with the admin role."),
                        ephemeral=True
                    )
                    return
                    
            # Check if already banned
            is_banned = await db.is_user_banned(interaction.guild.id, user.id)
            if is_banned:
                await interaction.followup.send(
                    embed=error_embed(f"{user.mention} is already banned from submitting confessions."),
                    ephemeral=True
                )
                return
                
            # Validate reason length
            if reason and len(reason) > Limits.MAX_BAN_REASON_LENGTH:
                await interaction.followup.send(
                    embed=error_embed(
                        f"Reason is too long (max {Limits.MAX_BAN_REASON_LENGTH} characters)."
                    ),
                    ephemeral=True
                )
                return
                
            # Ban the user
            await db.ban_user(
                interaction.guild.id,
                user.id,
                interaction.user.id,
                reason
            )
            
            # Send confirmation
            embed = success_embed(
                title=f"{Emojis.BAN} User Banned",
                description=f"{user.mention} has been banned from submitting confessions."
            )
            embed.add_field(
                name="User",
                value=f"{user} (ID: {user.id})",
                inline=True
            )
            embed.add_field(
                name="Banned By",
                value=interaction.user.mention,
                inline=True
            )
            if reason:
                embed.add_field(
                    name="Reason",
                    value=reason,
                    inline=False
                )
                
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Try to DM the user
            try:
                dm_embed = discord.Embed(
                    title=f"{Emojis.BAN} Banned from Confessions",
                    description=f"You have been banned from submitting confessions in **{interaction.guild.name}**.",
                    color=discord.Color.red()
                )
                if reason:
                    dm_embed.add_field(name="Reason", value=reason, inline=False)
                dm_embed.set_footer(text="Contact a server admin if you believe this is a mistake.")
                await user.send(embed=dm_embed)
            except discord.Forbidden:
                logger.info(f"Could not DM user {user.id} about ban")
                
            logger.info(
                f"User {user.id} banned from confessions in guild {interaction.guild.id} by {interaction.user.id}"
            )
            
        except DatabaseError as e:
            logger.error(f"Database error banning user: {e}")
            await interaction.followup.send(
                embed=error_embed("A database error occurred. Please try again later."),
                ephemeral=True
            )
            
    @app_commands.command(
        name="unban_confess_user",
        description="Unban a user from submitting confessions (Admin only)"
    )
    @app_commands.describe(
        user="The user to unban"
    )
    @require_admin_role()
    async def unban_user_command(
        self,
        interaction: discord.Interaction,
        user: discord.Member
    ):
        """Unban a user from submitting confessions."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Check if user is banned
            is_banned = await db.is_user_banned(interaction.guild.id, user.id)
            if not is_banned:
                await interaction.followup.send(
                    embed=error_embed(f"{user.mention} is not banned from submitting confessions."),
                    ephemeral=True
                )
                return
                
            # Unban the user
            await db.unban_user(interaction.guild.id, user.id)
            
            # Send confirmation
            embed = success_embed(
                title=f"{Emojis.UNBAN} User Unbanned",
                description=f"{user.mention} can now submit confessions again."
            )
            embed.add_field(
                name="User",
                value=f"{user} (ID: {user.id})",
                inline=True
            )
            embed.add_field(
                name="Unbanned By",
                value=interaction.user.mention,
                inline=True
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Try to DM the user
            try:
                dm_embed = discord.Embed(
                    title=f"{Emojis.UNBAN} Unbanned from Confessions",
                    description=f"You can now submit confessions again in **{interaction.guild.name}**.",
                    color=discord.Color.green()
                )
                await user.send(embed=dm_embed)
            except discord.Forbidden:
                logger.info(f"Could not DM user {user.id} about unban")
                
            logger.info(
                f"User {user.id} unbanned from confessions in guild {interaction.guild.id} by {interaction.user.id}"
            )
            
        except DatabaseError as e:
            logger.error(f"Database error unbanning user: {e}")
            await interaction.followup.send(
                embed=error_embed("A database error occurred. Please try again later."),
                ephemeral=True
            )
            
    @app_commands.command(
        name="unban_confess_user_by_id",
        description="Unban a user by their ID (for users not in the server) (Admin only)"
    )
    @app_commands.describe(
        user_id="The Discord user ID to unban"
    )
    @require_admin_role()
    async def unban_by_id_command(
        self,
        interaction: discord.Interaction,
        user_id: str
    ):
        """Unban a user by their ID."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Validate user ID
            try:
                user_id_int = int(user_id)
            except ValueError:
                await interaction.followup.send(
                    embed=error_embed("Please provide a valid user ID (numbers only)."),
                    ephemeral=True
                )
                return
                
            # Unban the user
            await db.unban_user(interaction.guild.id, user_id_int)
            
            embed = success_embed(
                title=f"{Emojis.UNBAN} User Unbanned",
                description=f"User with ID **{user_id}** has been unbanned."
            )
            embed.add_field(
                name="Unbanned By",
                value=interaction.user.mention,
                inline=True
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            logger.info(
                f"User {user_id_int} unbanned from confessions in guild {interaction.guild.id} by {interaction.user.id}"
            )
            
        except DatabaseError as e:
            logger.error(f"Database error unbanning user: {e}")
            await interaction.followup.send(
                embed=error_embed("A database error occurred. Please try again later."),
                ephemeral=True
            )
            
    @app_commands.command(
        name="list_banned_users",
        description="List all users banned from submitting confessions (Admin only)"
    )
    @require_admin_role()
    async def list_banned_command(self, interaction: discord.Interaction):
        """List all banned users."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            banned_users = await db.get_banned_users(interaction.guild.id)
            
            if not banned_users:
                await interaction.followup.send(
                    embed=success_embed(
                        f"{Emojis.INFO} No users are currently banned from submitting confessions."
                    ),
                    ephemeral=True
                )
                return
                
            embed = banned_list_embed(interaction.guild.name, banned_users)
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except DatabaseError as e:
            logger.error(f"Database error listing banned users: {e}")
            await interaction.followup.send(
                embed=error_embed("A database error occurred. Please try again later."),
                ephemeral=True
            )
            
    @app_commands.command(
        name="check_ban_status",
        description="Check if a user is banned from submitting confessions (Admin only)"
    )
    @app_commands.describe(
        user="The user to check"
    )
    @require_admin_role()
    async def check_ban_command(
        self,
        interaction: discord.Interaction,
        user: discord.Member
    ):
        """Check if a user is banned."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            is_banned = await db.is_user_banned(interaction.guild.id, user.id)
            
            if is_banned:
                # Get ban details
                banned_users = await db.get_banned_users(interaction.guild.id)
                ban_info = next(
                    (b for b in banned_users if b['user_id'] == user.id),
                    None
                )
                
                embed = discord.Embed(
                    title=f"{Emojis.BAN} User is Banned",
                    description=f"{user.mention} is banned from submitting confessions.",
                    color=discord.Color.red()
                )
                if ban_info and ban_info.get('reason'):
                    embed.add_field(name="Reason", value=ban_info['reason'], inline=False)
                if ban_info and ban_info.get('banned_at'):
                    embed.add_field(
                        name="Banned At",
                        value=ban_info['banned_at'][:10],
                        inline=True
                    )
            else:
                embed = discord.Embed(
                    title=f"{Emojis.UNBAN} User is Not Banned",
                    description=f"{user.mention} can submit confessions.",
                    color=discord.Color.green()
                )
                
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except DatabaseError as e:
            logger.error(f"Database error checking ban status: {e}")
            await interaction.followup.send(
                embed=error_embed("A database error occurred. Please try again later."),
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    """Add the cog to the bot."""
    await bot.add_cog(ModerationCog(bot))
    logger.info("ModerationCog loaded successfully")
