"""
Content filtering utilities for the confession bot.
Handles bad word detection and content moderation.
"""

import re
import logging
import unicodedata
from typing import List, Tuple, Set

from database.supabase_client import db, DatabaseError

logger = logging.getLogger('confession-bot.filters')


class ContentFilter:
    """Bad word content filter for confessions."""
    
    # Common character substitutions that people use to bypass filters
    SUBSTITUTIONS = {
        'a': ['@', '4', '∂', 'α'],
        'b': ['8', 'ß', 'β'],
        'c': ['(', '<', '©', '¢'],
        'd': ['|)', '∂', 'ð'],
        'e': ['3', '€', 'ε'],
        'f': ['ƒ'],
        'g': ['6', '9', 'ɢ'],
        'h': ['#', 'ℋ'],
        'i': ['1', '!', '|', 'ℹ'],
        'j': ['ʝ'],
        'k': ['|<', 'κ'],
        'l': ['1', '|', '£', 'ℓ'],
        'm': ['|v|', 'ℳ'],
        'n': ['|\|', 'η'],
        'o': ['0', '()', 'ø', 'ο'],
        'p': ['|>', '¶', 'ρ'],
        'q': ['9', 'ɋ'],
        'r': ['|2', '®', 'ρ'],
        's': ['5', '$', '§', 'σ'],
        't': ['7', '+', '†', 'τ'],
        'u': ['|_|', 'υ'],
        'v': ['\/', 'ν'],
        'w': ['\/\/', 'ω'],
        'x': ['%', '×', 'χ'],
        'y': ['¥', 'ʏ', 'γ'],
        'z': ['2', 'ζ'],
    }
    
    def __init__(self, guild_id: int):
        self.guild_id = guild_id
        self._word_cache: Set[str] = set()
        self._cache_loaded = False
        
    async def _load_words(self) -> Set[str]:
        """Load blocked words from database."""
        if self._cache_loaded:
            return self._word_cache
            
        try:
            words = await db.get_blocked_words(self.guild_id)
            self._word_cache = set(word.lower() for word in words)
            self._cache_loaded = True
            return self._word_cache
        except DatabaseError as e:
            logger.error(f"Error loading blocked words: {e}")
            return set()
            
    def _normalize_text(self, text: str) -> str:
        """Normalize text by converting substitutions to regular characters."""
        normalized = text.lower()
        
        # Replace common substitutions
        for char, substitutes in self.SUBSTITUTIONS.items():
            for sub in substitutes:
                normalized = normalized.replace(sub, char)
                
        # Remove extra whitespace and special characters
        normalized = re.sub(r'[^\w\s]', '', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        return normalized
        
    def _generate_variations(self, word: str) -> List[str]:
        """Generate possible variations of a word with substitutions."""
        variations = [word.lower()]
        
        # Add version with common substitutions
        substituted = word.lower()
        for char, substitutes in self.SUBSTITUTIONS.items():
            for sub in substitutes:
                substituted = substituted.replace(char, sub)
        variations.append(substituted)
        
        return variations
        
    async def check_content(self, content: str) -> Tuple[bool, List[str]]:
        """Check content for blocked words.
        
        Returns:
            Tuple of (has_match, list_of_matched_words)
        """
        blocked_words = await self._load_words()
        
        if not blocked_words:
            return False, []
            
        normalized_content = self._normalize_text(content)
        matched_words = []
        
        for word in blocked_words:
            # Check exact word match
            pattern = r'\b' + re.escape(word) + r'\b'
            if re.search(pattern, normalized_content, re.IGNORECASE):
                matched_words.append(word)
                continue
                
            # Check with substitutions
            variations = self._generate_variations(word)
            for variation in variations:
                if variation in normalized_content:
                    matched_words.append(word)
                    break
                    
        return len(matched_words) > 0, matched_words
        
    async def censor_content(self, content: str) -> str:
        """Censor blocked words in content.
        
        Returns:
            Censored content with blocked words replaced.
        """
        blocked_words = await self._load_words()
        
        if not blocked_words:
            return content
            
        censored = content
        normalized = self._normalize_text(content)
        
        for word in blocked_words:
            pattern = r'\b' + re.escape(word) + r'\b'
            
            # Find matches in normalized text and censor in original
            for match in re.finditer(pattern, normalized, re.IGNORECASE):
                start, end = match.span()
                # Replace with asterisks
                censored = censored[:start] + '*' * (end - start) + censored[end:]
                
        return censored
        
    def clear_cache(self):
        """Clear the word cache (call when words are modified)."""
        self._word_cache.clear()
        self._cache_loaded = False


class SpamDetector:
    """Simple spam detection for confessions."""
    
    # Patterns that might indicate spam
    SPAM_PATTERNS = [
        r'(.)\1{10,}',  # Repeated characters (10+ times)
        r'[A-Z]{20,}',  # Excessive caps
        r'https?://\S{100,}',  # Very long URLs
        r'([\w\s])\1{50,}',  # Repeated words/phrases
    ]

    CUSTOM_EMOJI_PATTERN = re.compile(r'<a?:\w+:\d+>')

    @staticmethod
    def count_emojis(content: str) -> int:
        """Count custom Discord emoji and common Unicode emoji/symbol glyphs."""
        custom_emoji_count = len(SpamDetector.CUSTOM_EMOJI_PATTERN.findall(content))
        content_without_custom = SpamDetector.CUSTOM_EMOJI_PATTERN.sub('', content)

        unicode_emoji_count = 0
        for char in content_without_custom:
            if char.isspace() or char.isalnum() or char == '_':
                continue

            category = unicodedata.category(char)
            if category in {'So', 'Sk'}:
                unicode_emoji_count += 1

        return custom_emoji_count + unicode_emoji_count
    
    @staticmethod
    def is_spam(content: str) -> Tuple[bool, str]:
        """Check if content appears to be spam.
        
        Returns:
            Tuple of (is_spam, reason)
        """
        # Check length
        if len(content) > 4000:
            return True, "Message is too long"
            
        # Check spam patterns
        for pattern in SpamDetector.SPAM_PATTERNS:
            if re.search(pattern, content):
                return True, "Content matches spam patterns"
                
        # Check for excessive newlines
        if content.count('\n') > 50:
            return True, "Excessive line breaks"
            
        # Check for excessive emoji
        emoji_count = SpamDetector.count_emojis(content)
        if emoji_count > 50:
            return True, "Excessive emoji usage"
            
        return False, ""


async def check_content_safety(
    guild_id: int,
    content: str,
    filter_enabled: bool = True
) -> dict:
    """Comprehensive content safety check.
    
    Returns dict with:
        - safe: bool - Whether content passes all checks
        - spam: bool - Whether content is detected as spam
        - spam_reason: str - Reason for spam detection
        - badword_match: bool - Whether bad words were found
        - matched_words: list - List of matched bad words
        - censored_content: str - Content with bad words censored (if applicable)
    """
    result = {
        'safe': True,
        'spam': False,
        'spam_reason': '',
        'badword_match': False,
        'matched_words': [],
        'censored_content': content
    }
    
    # Check for spam
    is_spam, spam_reason = SpamDetector.is_spam(content)
    if is_spam:
        result['spam'] = True
        result['spam_reason'] = spam_reason
        result['safe'] = False
        return result
        
    # Check for bad words if filter is enabled
    if filter_enabled:
        filter_obj = ContentFilter(guild_id)
        has_match, matched_words = await filter_obj.check_content(content)
        
        if has_match:
            result['badword_match'] = True
            result['matched_words'] = matched_words
            result['censored_content'] = await filter_obj.censor_content(content)
            # Don't mark as unsafe here - let the filter action decide
            
    return result
