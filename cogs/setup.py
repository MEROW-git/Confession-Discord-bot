"""
Setup Cog - Server configuration and initial setup
Handles the /setup command and guild configuration.
"""

import logging

import discord
from discord import app_commands
from discord.ext import commands

from database.supabase_client import db, DatabaseError, initialize_database
from utils.embeds import (
    success_embed, error_embed, setup_complete_embed, info_embed
)
from utils.checks import (
    validate_channel_permissions,
    setup_review_channel_permissions,
    require_bot_permissions
)
from utils.constants import Emojis

logger = logging.getLogger('confession-bot.setup')


class SetupCog(commands.Cog):
    """Cog for server setup and configuration."""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Initialize database connection
        initialize_database(bot.config.SUPABASE_URL, bot.config.SUPABASE_SERVICE_ROLE_KEY)
        
    @app_commands.command(
        name="setup",
        description="Configure the confession bot for this server (Admin only)"
    )
    @app_commands.describe(
        confession_channel="The public channel where approved confessions will be posted",
        review_channel="The private channel where admins review confessions",
        admin_role="The role that can review and manage confessions"
    )
    @app_commands.checks.has_permissions(administrator=True)
    @require_bot_permissions(manage_channels=True, manage_permissions=True, send_messages=True)
    async def setup_command(
        self,
        interaction: discord.Interaction,
        confession_channel: discord.TextChannel,
        review_channel: discord.TextChannel,
        admin_role: discord.Role
    ):
        """Setup command to configure the bot for a server."""
        await interaction.response.defer(ephemeral=True)
        
        try:
            hierarchy_warning = None

            # Validate confession channel
            valid, error = await validate_channel_permissions(
                interaction.guild.me,
                confession_channel,
                require_send=True,
                require_view=True
            )
            if not valid:
                await interaction.followup.send(
                    embed=error_embed(
                        f"I cannot use {confession_channel.mention} as the confession channel.\n{error}"
                    ),
                    ephemeral=True
                )
                return
                
            # Validate review channel
            valid, error = await validate_channel_permissions(
                interaction.guild.me,
                review_channel,
                require_send=True,
                require_view=True,
                require_manage=True
            )
            if not valid:
                await interaction.followup.send(
                    embed=error_embed(
                        f"I cannot use {review_channel.mention} as the review channel.\n{error}"
                    ),
                    ephemeral=True
                )
                return
                
            # Validate admin role exists
            if admin_role not in interaction.guild.roles:
                await interaction.followup.send(
                    embed=error_embed(
                        f"The role {admin_role.mention} does not exist in this server."
                    ),
                    ephemeral=True
                )
                return
                
            # Role hierarchy can prevent automatic channel overwrite changes for the selected role.
            # Treat that as a warning so the rest of setup can still complete.
            bot_top_role = interaction.guild.me.top_role
            if admin_role >= bot_top_role:
                hierarchy_warning = (
                    f"The selected admin role ({admin_role.mention}) is not below my highest role "
                    f"({bot_top_role.mention}). I may not be able to grant that role access to "
                    f"{review_channel.mention} automatically, so please verify the channel permissions after setup."
                )
                
            # Set up review channel permissions
            setup_success, setup_error = await setup_review_channel_permissions(
                review_channel,
                admin_role,
                interaction.guild.me
            )
            
            if not setup_success:
                await interaction.followup.send(
                    embed=error_embed(
                        f"Failed to set up review channel permissions: {setup_error}\n\n"
                        f"Please manually ensure:\n"
                        f"• @everyone cannot view {review_channel.mention}\n"
                        f"• {admin_role.mention} can view and send messages\n"
                        f"• I have all necessary permissions"
                    ),
                    ephemeral=True
                )
                # Continue with setup even if permission setup fails
                
            # Save settings to database
            existing_settings = await db.get_guild_settings(interaction.guild.id)
            
            if existing_settings:
                # Update existing settings
                await db.update_guild_settings(
                    interaction.guild.id,
                    guild_name=interaction.guild.name,
                    confession_channel_id=confession_channel.id,
                    review_channel_id=review_channel.id,
                    admin_role_id=admin_role.id
                )
            else:
                # Create new settings
                await db.create_guild_settings(
                    guild_id=interaction.guild.id,
                    guild_name=interaction.guild.name,
                    confession_channel_id=confession_channel.id,
                    review_channel_id=review_channel.id,
                    admin_role_id=admin_role.id
                )
                
            # Send success message
            embed = setup_complete_embed(
                confession_channel=confession_channel,
                review_channel=review_channel,
                admin_role=admin_role
            )
            
            if not setup_success:
                embed.add_field(
                    name=f"{Emojis.WARNING} Note",
                    value="I couldn't automatically set review channel permissions. Please verify them manually.",
                    inline=False
                )

            if hierarchy_warning:
                embed.add_field(
                    name=f"{Emojis.WARNING} Role Hierarchy",
                    value=hierarchy_warning,
                    inline=False
                )
                
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Send confirmation to review channel
            try:
                review_embed = info_embed(
                    title=f"{Emojis.SETTINGS} Confession Bot Setup Complete",
                    description=(
                        f"This channel is now configured as the review channel.\n\n"
                        f"**Confession Channel:** {confession_channel.mention}\n"
                        f"**Admin Role:** {admin_role.mention}\n\n"
                        f"All confessions will appear here for review before being posted publicly."
                    )
                )
                await review_channel.send(embed=review_embed)
            except discord.Forbidden:
                logger.warning(f"Could not send setup confirmation to review channel in guild {interaction.guild.id}")
                
            logger.info(
                f"Guild {interaction.guild.id} ({interaction.guild.name}) configured successfully"
            )
            
        except DatabaseError as e:
            logger.error(f"Database error during setup: {e}")
            await interaction.followup.send(
                embed=error_embed(
                    "A database error occurred. Please try again later."
                ),
                ephemeral=True
            )
        except Exception as e:
            logger.exception(f"Unexpected error during setup: {e}")
            await interaction.followup.send(
                embed=error_embed(
                    "An unexpected error occurred. Please try again later."
                ),
                ephemeral=True
            )
            
    @setup_command.error
    async def setup_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Handle setup command errors."""
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                embed=error_embed(
                    "You need **Administrator** permission to run the setup command."
                ),
                ephemeral=True
            )
        elif isinstance(error, app_commands.BotMissingPermissions):
            perms = ", ".join(error.missing_permissions)
            await interaction.response.send_message(
                embed=error_embed(
                    f"I need the following permissions to set up: {perms}"
                ),
                ephemeral=True
            )
        else:
            logger.error(f"Setup command error: {error}")
            await interaction.response.send_message(
                embed=error_embed(
                    "An error occurred. Please try again later."
                ),
                ephemeral=True
            )


async def setup(bot: commands.Bot):
    """Add the cog to the bot."""
    await bot.add_cog(SetupCog(bot))
    logger.info("SetupCog loaded successfully")
