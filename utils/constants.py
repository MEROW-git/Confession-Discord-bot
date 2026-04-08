"""
Constants and configuration values for the confession bot.
"""

from enum import Enum


class ConfessionStatus(str, Enum):
    """Confession status values."""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    FLAGGED = "flagged"


class FilterAction(str, Enum):
    """Bad word filter actions."""
    FLAG = "flag"
    REJECT = "reject"
    CENSOR = "censor"


class Colors:
    """Discord embed colors."""
    PRIMARY = 0x5865F2      # Discord blurple
    SUCCESS = 0x57F287      # Green
    ERROR = 0xED4245        # Red
    WARNING = 0xFEE75C      # Yellow
    INFO = 0x5865F2         # Blue
    ANONYMOUS = 0x23272A    # Dark gray
    PENDING = 0xEB459E      # Pink
    FLAGGED = 0xF39C12      # Orange


class Emojis:
    """Emoji constants."""
    APPROVE = "✅"
    REJECT = "❌"
    FLAG = "🚩"
    PENDING = "⏳"
    ANONYMOUS = "👤"
    CONFESSION = "💬"
    CATEGORY = "🏷️"
    ID = "🔢"
    TIME = "🕐"
    WARNING = "⚠️"
    INFO = "ℹ️"
    SUCCESS = "✅"
    ERROR = "❌"
    LOCK = "🔒"
    UNLOCK = "🔓"
    SETTINGS = "⚙️"
    FILTER = "🛡️"
    BAN = "🔨"
    UNBAN = "🔓"
    COOLDOWN = "⏱️"


class Limits:
    """Bot limits and constraints."""
    MAX_CONFESSION_LENGTH = 2000
    MIN_COOLDOWN_SECONDS = 10
    MAX_COOLDOWN_SECONDS = 86400  # 24 hours
    MAX_CATEGORY_LENGTH = 50
    MAX_BADWORD_LENGTH = 100
    MAX_BADWORDS_PER_GUILD = 500
    MAX_BAN_REASON_LENGTH = 500


# Default values
DEFAULT_COOLDOWN_SECONDS = 300  # 5 minutes
DEFAULT_FILTER_ACTION = FilterAction.FLAG

# Confession categories (suggestions)
SUGGESTED_CATEGORIES = [
    "Love",
    "School",
    "Work",
    "Friendship",
    "Family",
    "Regret",
    "Secret",
    "Funny",
    "Serious",
    "Other"
]
