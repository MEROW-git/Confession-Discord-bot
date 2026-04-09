"""
Embed templates for the confession bot.
Provides consistent embed styling across the bot.
"""

import discord
from datetime import datetime
from typing import Optional, List

from .constants import Colors, Emojis


def create_embed(
    title: str = None,
    description: str = None,
    color: int = Colors.PRIMARY,
    footer: str = None,
    timestamp: bool = True
) -> discord.Embed:
    """Create a base embed with consistent styling."""
    embed = discord.Embed(
        title=title,
        description=description,
        color=color,
        timestamp=datetime.utcnow() if timestamp else None
    )
    if footer:
        embed.set_footer(text=footer)
    return embed


def success_embed(description: str, title: str = f"{Emojis.SUCCESS} Success") -> discord.Embed:
    """Create a success embed."""
    return create_embed(
        title=title,
        description=description,
        color=Colors.SUCCESS
    )


def error_embed(description: str, title: str = f"{Emojis.ERROR} Error") -> discord.Embed:
    """Create an error embed."""
    return create_embed(
        title=title,
        description=description,
        color=Colors.ERROR
    )


def warning_embed(description: str, title: str = f"{Emojis.WARNING} Warning") -> discord.Embed:
    """Create a warning embed."""
    return create_embed(
        title=title,
        description=description,
        color=Colors.WARNING
    )


def info_embed(description: str, title: str = f"{Emojis.INFO} Information") -> discord.Embed:
    """Create an info embed."""
    return create_embed(
        title=title,
        description=description,
        color=Colors.INFO
    )


def pending_review_embed(
    confession_id: int,
    confession_number: int,
    content: str,
    category: Optional[str] = None,
    filter_flagged: bool = False,
    matched_words: Optional[List[str]] = None
) -> discord.Embed:
    """Create the embed for pending confession in review channel."""
    embed = discord.Embed(
        title=f"{Emojis.PENDING} New Confession Pending Review",
        description=f"**Confession #{confession_number}** (ID: {confession_id})",
        color=Colors.FLAGGED if filter_flagged else Colors.PENDING,
        timestamp=datetime.utcnow()
    )
    
    # Confession content
    embed.add_field(
        name=f"{Emojis.CONFESSION} Content",
        value=content[:1024] if content else "*No content*",
        inline=False
    )
    
    # Category
    if category:
        embed.add_field(
            name=f"{Emojis.CATEGORY} Category",
            value=category,
            inline=True
        )
        
    # Filter warning
    if filter_flagged:
        warning_text = f"{Emojis.WARNING} **This confession triggered the bad word filter!**"
        if matched_words:
            warning_text += f"\nMatched words: {', '.join(matched_words)}"
        embed.add_field(
            name=f"{Emojis.FILTER} Filter Alert",
            value=warning_text,
            inline=False
        )
        
    embed.set_footer(text="Use the buttons below to approve, reject, or flag this confession.")
    return embed


def public_confession_embed(
    confession_number: int,
    content: str,
    category: Optional[str] = None,
    timestamp: Optional[datetime] = None
) -> discord.Embed:
    """Create the public confession embed posted after approval."""
    embed = discord.Embed(
        title=f"{Emojis.ANONYMOUS} Anonymous Confession #{confession_number}",
        description=content,
        color=Colors.ANONYMOUS,
        timestamp=timestamp or datetime.utcnow()
    )
    
    if category:
        embed.add_field(
            name=f"{Emojis.CATEGORY} Category",
            value=category,
            inline=True
        )
        
    embed.set_footer(text="Posted anonymously")
    return embed


def review_decision_embed(
    confession_id: int,
    confession_number: int,
    decision: str,  # 'approved', 'rejected', 'flagged'
    decided_by: str,
    reason: Optional[str] = None
) -> discord.Embed:
    """Create embed showing review decision."""
    colors = {
        'approved': Colors.SUCCESS,
        'rejected': Colors.ERROR,
        'flagged': Colors.WARNING
    }
    emojis = {
        'approved': Emojis.APPROVE,
        'rejected': Emojis.REJECT,
        'flagged': Emojis.FLAG
    }
    
    embed = discord.Embed(
        title=f"{emojis.get(decision, Emojis.INFO)} Confession #{confession_number} {decision.title()}",
        description=f"Confession ID: {confession_id}",
        color=colors.get(decision, Colors.INFO),
        timestamp=datetime.utcnow()
    )
    
    embed.add_field(
        name="Reviewed By",
        value=decided_by,
        inline=True
    )
    
    if reason:
        embed.add_field(
            name="Reason",
            value=reason,
            inline=False
        )
        
    return embed


def setup_complete_embed(
    confession_channel: discord.TextChannel,
    review_channel: discord.TextChannel,
    admin_role: discord.Role
) -> discord.Embed:
    """Embed shown after successful setup."""
    embed = discord.Embed(
        title=f"{Emojis.SUCCESS} Setup Complete!",
        description="Your confession bot has been configured successfully.",
        color=Colors.SUCCESS
    )
    
    embed.add_field(
        name=f"{Emojis.CONFESSION} Confession Channel",
        value=confession_channel.mention,
        inline=True
    )
    
    embed.add_field(
        name=f"{Emojis.LOCK} Review Channel",
        value=review_channel.mention,
        inline=True
    )
    
    embed.add_field(
        name=f"{Emojis.SETTINGS} Admin Role",
        value=admin_role.mention,
        inline=True
    )
    
    embed.add_field(
        name="Next Steps",
        value=(
            "• Users can submit confessions with `/confess`\n"
            "• Admins will review submissions in the review channel\n"
            "• Use `/settings` to configure additional options"
        ),
        inline=False
    )
    
    return embed


def settings_embed(
    guild_name: str,
    confession_channel: Optional[discord.TextChannel] = None,
    review_channel: Optional[discord.TextChannel] = None,
    admin_role: Optional[discord.Role] = None,
    badword_filter: bool = False,
    cooldown: int = 300,
    filter_action: str = 'flag'
) -> discord.Embed:
    """Embed showing current guild settings."""
    embed = discord.Embed(
        title=f"{Emojis.SETTINGS} Bot Settings - {guild_name}",
        description="Current configuration for this server",
        color=Colors.INFO
    )
    
    embed.add_field(
        name=f"{Emojis.CONFESSION} Confession Channel",
        value=confession_channel.mention if confession_channel else "Not set",
        inline=True
    )
    
    embed.add_field(
        name=f"{Emojis.LOCK} Review Channel",
        value=review_channel.mention if review_channel else "Not set",
        inline=True
    )
    
    embed.add_field(
        name=f"{Emojis.SETTINGS} Admin Role",
        value=admin_role.mention if admin_role else "Not set",
        inline=True
    )
    
    embed.add_field(
        name=f"{Emojis.FILTER} Bad Word Filter",
        value=f"{'Enabled' if badword_filter else 'Disabled'} ({filter_action})",
        inline=True
    )
    
    embed.add_field(
        name=f"{Emojis.COOLDOWN} Cooldown",
        value=f"{cooldown} seconds",
        inline=True
    )
    
    return embed


def banned_list_embed(guild_name: str, banned_users: List[dict]) -> discord.Embed:
    """Embed showing list of banned users."""
    embed = discord.Embed(
        title=f"{Emojis.BAN} Banned Users - {guild_name}",
        description=f"Total banned users: {len(banned_users)}",
        color=Colors.ERROR
    )
    
    if not banned_users:
        embed.description = "No users are currently banned."
    else:
        for ban in banned_users[:25]:  # Discord limit
            user_id = ban.get('user_id', 'Unknown')
            reason = ban.get('reason', 'No reason provided')
            banned_at = ban.get('banned_at', 'Unknown')
            
            embed.add_field(
                name=f"User ID: {user_id}",
                value=f"Reason: {reason[:100]}\nBanned: {banned_at[:10] if banned_at else 'Unknown'}",
                inline=False
            )
            
    return embed


def badword_list_embed(guild_name: str, words: List[str]) -> discord.Embed:
    """Embed showing list of blocked words."""
    embed = discord.Embed(
        title=f"{Emojis.FILTER} Blocked Words - {guild_name}",
        description=f"Total blocked words: {len(words)}",
        color=Colors.WARNING
    )
    
    if not words:
        embed.description = "No words are currently blocked."
    else:
        # Split words into chunks to fit in embed
        word_list = ", ".join(words)
        if len(word_list) > 4000:
            word_list = word_list[:4000] + "..."
            
        embed.add_field(
            name="Blocked Words",
            value=word_list or "None",
            inline=False
        )
        
    return embed


def help_embed() -> discord.Embed:
    """Main help embed."""
    embed = discord.Embed(
        title=f"{Emojis.INFO} Anonymous Confession Bot - Help",
        description="Submit anonymous confessions that are reviewed by admins before posting.",
        color=Colors.PRIMARY
    )
    
    embed.add_field(
        name="👤 User Commands",
        value=(
            "`/confess` - Submit an anonymous confession\n"
            "`/help` - Show this help message"
        ),
        inline=False
    )
    
    embed.add_field(
        name="⚙️ Admin Setup",
        value=(
            "`/setup` - Configure confession and review channels\n"
            "`/settings` - View current settings\n"
            "`/toggle_badword_filter` - Enable/disable filter\n"
            "`/set_cooldown` - Set submission cooldown"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🛡️ Moderation",
        value=(
            "`/add_badword` - Add word to filter\n"
            "`/remove_badword` - Remove word from filter\n"
            "`/ban_confess_user` - Ban user from submitting\n"
            "`/unban_confess_user` - Unban user"
        ),
        inline=False
    )
    
    embed.add_field(
        name="How It Works",
        value=(
            "1. Use `/confess` to submit a confession\n"
            "2. Admins review it in the private review channel\n"
            "3. If approved, it appears anonymously in the public channel"
        ),
        inline=False
    )
    
    embed.set_footer(text="Your identity is kept private and only visible to bot admins for moderation.")
    return embed
