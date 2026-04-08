"""
Permission checks and validation utilities for the confession bot.
"""

import discord
from discord import app_commands
from typing import Optional, Callable
import logging

from database.supabase_client import db, DatabaseError

logger = logging.getLogger('confession-bot.checks')


class SetupRequiredError(app_commands.CheckFailure):
    """Raised when guild setup is not complete."""
    pass


class AdminRoleRequiredError(app_commands.CheckFailure):
    """Raised when user doesn't have the admin role."""
    pass


class BotPermissionError(app_commands.CheckFailure):
    """Raised when bot lacks required permissions."""
    pass


async def is_guild_setup(guild_id: int) -> bool:
    """Check if a guild has completed setup."""
    try:
        settings = await db.get_guild_settings(guild_id)
        if not settings:
            return False
        return all([
            settings.get('confession_channel_id'),
            settings.get('review_channel_id'),
            settings.get('admin_role_id')
        ])
    except DatabaseError as e:
        logger.error(f"Database error checking guild setup: {e}")
        return False


async def has_admin_role(interaction: discord.Interaction) -> bool:
    """Check if the user has the configured admin role."""
    if not interaction.guild:
        return False
        
    try:
        settings = await db.get_guild_settings(interaction.guild.id)
        if not settings:
            return False
            
        admin_role_id = settings.get('admin_role_id')
        if not admin_role_id:
            return False
            
        # Check if user has the admin role
        admin_role = interaction.guild.get_role(admin_role_id)
        if not admin_role:
            return False
            
        return admin_role in interaction.user.roles
    except DatabaseError as e:
        logger.error(f"Database error checking admin role: {e}")
        return False


def require_setup():
    """Decorator to require guild setup for a command."""
    async def predicate(interaction: discord.Interaction) -> bool:
        if not interaction.guild:
            raise SetupRequiredError("This command can only be used in a server.")
            
        if not await is_guild_setup(interaction.guild.id):
            raise SetupRequiredError(
                "This server hasn't been set up yet. Please ask an admin to run `/setup` first."
            )
        return True
    return app_commands.check(predicate)


def require_admin_role():
    """Decorator to require admin role for a command."""
    async def predicate(interaction: discord.Interaction) -> bool:
        if not interaction.guild:
            raise AdminRoleRequiredError("This command can only be used in a server.")
            
        # Server administrators always have access
        if interaction.user.guild_permissions.administrator:
            return True
            
        if not await has_admin_role(interaction):
            settings = await db.get_guild_settings(interaction.guild.id)
            admin_role_id = settings.get('admin_role_id') if settings else None
            admin_role = interaction.guild.get_role(admin_role_id) if admin_role_id else None
            role_mention = admin_role.mention if admin_role else "the configured admin role"
            
            raise AdminRoleRequiredError(
                f"You need {role_mention} or server administrator permissions to use this command."
            )
        return True
    return app_commands.check(predicate)


def require_bot_permissions(**permissions):
    """Decorator to check bot permissions."""
    async def predicate(interaction: discord.Interaction) -> bool:
        if not interaction.guild:
            return True
            
        bot_member = interaction.guild.me
        missing_perms = []
        
        for perm_name, required in permissions.items():
            if required:
                perm_value = getattr(discord.Permissions, perm_name, None)
                if perm_value and not getattr(bot_member.guild_permissions, perm_name, False):
                    missing_perms.append(perm_name.replace('_', ' ').title())
                    
        if missing_perms:
            raise BotPermissionError(
                f"I need the following permissions: {', '.join(missing_perms)}"
            )
        return True
    return app_commands.check(predicate)


async def validate_channel_permissions(
    bot_member: discord.Member,
    channel: discord.TextChannel,
    require_send: bool = True,
    require_view: bool = True,
    require_manage: bool = False
) -> tuple[bool, Optional[str]]:
    """Validate bot permissions in a channel.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    perms = channel.permissions_for(bot_member)
    
    if require_view and not perms.view_channel:
        return False, f"I cannot view the channel {channel.mention}"
        
    if require_send and not perms.send_messages:
        return False, f"I cannot send messages in {channel.mention}"
        
    if require_manage and not perms.manage_channels:
        return False, f"I need permission to manage channels"
        
    return True, None


async def setup_review_channel_permissions(
    review_channel: discord.TextChannel,
    admin_role: discord.Role,
    bot_member: discord.Member
) -> tuple[bool, Optional[str]]:
    """Set up proper permissions for the review channel.
    
    Makes the channel private with only admin role and bot having access.
    
    Returns:
        Tuple of (success, error_message)
    """
    try:
        # Check if bot can manage channel permissions
        if not review_channel.permissions_for(bot_member).manage_permissions:
            return False, "I need `Manage Permissions` to set up the review channel properly"
            
        # Get @everyone role
        everyone = review_channel.guild.default_role
        
        # Set @everyone to have no access
        await review_channel.set_permissions(
            everyone,
            view_channel=False,
            reason="Confession bot review channel setup"
        )
        
        # Set admin role to have access
        await review_channel.set_permissions(
            admin_role,
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            reason="Confession bot review channel setup"
        )
        
        # Ensure bot has access
        await review_channel.set_permissions(
            bot_member,
            view_channel=True,
            send_messages=True,
            embed_links=True,
            attach_files=True,
            read_message_history=True,
            manage_messages=True,  # Needed to update review messages
            reason="Confession bot review channel setup"
        )
        
        return True, None
        
    except discord.Forbidden:
        return False, "I don't have permission to modify channel permissions"
    except discord.HTTPException as e:
        return False, f"Failed to set permissions: {e.text}"


async def check_user_cooldown(
    guild_id: int,
    user_id: int,
    cooldown_seconds: int
) -> tuple[bool, int]:
    """Check if user is on cooldown.
    
    Returns:
        Tuple of (can_submit, remaining_seconds)
    """
    from datetime import datetime, timezone
    
    try:
        last_submission = await db.get_last_submission(guild_id, user_id)
        
        if not last_submission:
            return True, 0
            
        elapsed = (datetime.now(timezone.utc) - last_submission).total_seconds()
        remaining = cooldown_seconds - int(elapsed)
        
        if remaining > 0:
            return False, remaining
        return True, 0
        
    except DatabaseError as e:
        logger.error(f"Error checking cooldown: {e}")
        # Allow submission on error to avoid blocking users
        return True, 0


def format_duration(seconds: int) -> str:
    """Format seconds into human-readable duration."""
    if seconds < 60:
        return f"{seconds} second{'s' if seconds != 1 else ''}"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} minute{'s' if minutes != 1 else ''}"
    else:
        hours = seconds // 3600
        remaining_minutes = (seconds % 3600) // 60
        if remaining_minutes > 0:
            return f"{hours} hour{'s' if hours != 1 else ''} {remaining_minutes} min"
        return f"{hours} hour{'s' if hours != 1 else ''}"
