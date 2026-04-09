"""
Supabase Database Client
Handles all database operations for the confession bot.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from supabase import create_client, Client
from postgrest.exceptions import APIError

logger = logging.getLogger('confession-bot.database')


class DatabaseError(Exception):
    """Custom database error."""
    pass


class SupabaseClient:
    """Singleton Supabase client for database operations."""
    
    _instance = None
    _client: Optional[Client] = None
    
    def __new__(cls, url: str = None, key: str = None):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
        
    def __init__(self, url: str = None, key: str = None):
        if url and key and not self._client:
            self._client = create_client(url, key)
            logger.info("Supabase client initialized")
            
    @property
    def client(self) -> Client:
        """Get the Supabase client instance."""
        if not self._client:
            raise DatabaseError("Supabase client not initialized. Call initialize() first.")
        return self._client
        
    def initialize(self, url: str, key: str):
        """Initialize the Supabase client."""
        if not self._client:
            self._client = create_client(url, key)
            logger.info("Supabase client initialized")
            
    # ============================================
    # Guild Settings Operations
    # ============================================
    
    async def get_guild_settings(self, guild_id: int) -> Optional[Dict[str, Any]]:
        """Get settings for a specific guild."""
        try:
            result = self.client.table('guild_settings')\
                .select('*')\
                .eq('guild_id', guild_id)\
                .single()\
                .execute()
            return result.data
        except APIError as e:
            if 'JSON object requested, multiple' in str(e) or '0 rows' in str(e):
                return None
            logger.error(f"Error getting guild settings: {e}")
            raise DatabaseError(f"Failed to get guild settings: {e}")
            
    async def create_guild_settings(
        self,
        guild_id: int,
        guild_name: str,
        confession_channel_id: int = None,
        review_channel_id: int = None,
        admin_role_id: int = None
    ) -> Dict[str, Any]:
        """Create new guild settings."""
        try:
            data = {
                'guild_id': guild_id,
                'guild_name': guild_name,
                'confession_channel_id': confession_channel_id,
                'review_channel_id': review_channel_id,
                'admin_role_id': admin_role_id,
                'badword_filter_enabled': False,
                'cooldown_seconds': 300,
                'filter_action': 'flag'
            }
            result = self.client.table('guild_settings')\
                .insert(data)\
                .execute()
            return result.data[0] if result.data else None
        except APIError as e:
            logger.error(f"Error creating guild settings: {e}")
            raise DatabaseError(f"Failed to create guild settings: {e}")
            
    async def update_guild_settings(
        self,
        guild_id: int,
        **kwargs
    ) -> Dict[str, Any]:
        """Update guild settings."""
        try:
            result = self.client.table('guild_settings')\
                .update(kwargs)\
                .eq('guild_id', guild_id)\
                .execute()
            return result.data[0] if result.data else None
        except APIError as e:
            logger.error(f"Error updating guild settings: {e}")
            raise DatabaseError(f"Failed to update guild settings: {e}")
            
    async def delete_guild_settings(self, guild_id: int) -> bool:
        """Delete guild settings."""
        try:
            self.client.table('guild_settings')\
                .delete()\
                .eq('guild_id', guild_id)\
                .execute()
            return True
        except APIError as e:
            logger.error(f"Error deleting guild settings: {e}")
            raise DatabaseError(f"Failed to delete guild settings: {e}")
            
    # ============================================
    # Confession Operations
    # ============================================
    
    async def create_confession(
        self,
        guild_id: int,
        user_id: int,
        content: str,
        category: str = None,
        filter_flagged: bool = False,
        filter_matched_words: List[str] = None
    ) -> Dict[str, Any]:
        """Create a new confession submission."""
        try:
            # Get next confession number for this guild
            num_result = self.client.rpc(
                'get_next_confession_number',
                {'p_guild_id': guild_id}
            ).execute()
            confession_number = num_result.data if num_result.data else 1
            
            data = {
                'confession_number': confession_number,
                'guild_id': guild_id,
                'user_id': user_id,
                'content': content,
                'category': category,
                'status': 'pending',
                'filter_flagged': filter_flagged,
                'filter_matched_words': filter_matched_words or []
            }
            
            result = self.client.table('confessions')\
                .insert(data)\
                .execute()
            return result.data[0] if result.data else None
        except APIError as e:
            logger.error(f"Error creating confession: {e}")
            raise DatabaseError(f"Failed to create confession: {e}")
            
    async def get_confession(self, confession_id: int) -> Optional[Dict[str, Any]]:
        """Get a confession by ID."""
        try:
            result = self.client.table('confessions')\
                .select('*')\
                .eq('id', confession_id)\
                .single()\
                .execute()
            return result.data
        except APIError as e:
            if '0 rows' in str(e):
                return None
            logger.error(f"Error getting confession: {e}")
            raise DatabaseError(f"Failed to get confession: {e}")
            
    async def get_confession_by_review_message(
        self,
        review_message_id: int
    ) -> Optional[Dict[str, Any]]:
        """Get confession by review message ID."""
        try:
            result = self.client.table('confessions')\
                .select('*')\
                .eq('review_message_id', review_message_id)\
                .single()\
                .execute()
            return result.data
        except APIError as e:
            if '0 rows' in str(e):
                return None
            logger.error(f"Error getting confession by review message: {e}")
            raise DatabaseError(f"Failed to get confession: {e}")
            
    async def update_confession_status(
        self,
        confession_id: int,
        status: str,
        reviewed_by: int = None,
        public_message_id: int = None
    ) -> Dict[str, Any]:
        """Update confession status (approve/reject/flag)."""
        try:
            data = {
                'status': status,
                'reviewed_at': datetime.now(timezone.utc).isoformat()
            }
            if reviewed_by:
                data['reviewed_by'] = reviewed_by
            if public_message_id:
                data['public_message_id'] = public_message_id
                
            result = self.client.table('confessions')\
                .update(data)\
                .eq('id', confession_id)\
                .execute()
            return result.data[0] if result.data else None
        except APIError as e:
            logger.error(f"Error updating confession status: {e}")
            raise DatabaseError(f"Failed to update confession status: {e}")
            
    async def set_review_message_id(
        self,
        confession_id: int,
        review_message_id: int
    ) -> bool:
        """Set the review message ID for a confession."""
        try:
            self.client.table('confessions')\
                .update({'review_message_id': review_message_id})\
                .eq('id', confession_id)\
                .execute()
            return True
        except APIError as e:
            logger.error(f"Error setting review message ID: {e}")
            raise DatabaseError(f"Failed to set review message ID: {e}")
            
    async def get_pending_confessions(self, guild_id: int) -> List[Dict[str, Any]]:
        """Get all pending confessions for a guild."""
        try:
            result = self.client.table('confessions')\
                .select('*')\
                .eq('guild_id', guild_id)\
                .eq('status', 'pending')\
                .order('created_at')\
                .execute()
            return result.data or []
        except APIError as e:
            logger.error(f"Error getting pending confessions: {e}")
            raise DatabaseError(f"Failed to get pending confessions: {e}")
            
    async def get_confession_stats(self, guild_id: int) -> Dict[str, int]:
        """Get confession statistics for a guild."""
        try:
            # Get counts by status
            result = self.client.table('confessions')\
                .select('status')\
                .eq('guild_id', guild_id)\
                .execute()
                
            stats = {'pending': 0, 'approved': 0, 'rejected': 0, 'flagged': 0, 'total': 0}
            for row in result.data or []:
                status = row.get('status', 'pending')
                if status in stats:
                    stats[status] += 1
                stats['total'] += 1
            return stats
        except APIError as e:
            logger.error(f"Error getting confession stats: {e}")
            raise DatabaseError(f"Failed to get confession stats: {e}")
            
    # ============================================
    # Bad Word Filter Operations
    # ============================================
    
    async def get_blocked_words(self, guild_id: int) -> List[str]:
        """Get all blocked words for a guild."""
        try:
            result = self.client.table('blocked_words')\
                .select('word')\
                .eq('guild_id', guild_id)\
                .execute()
            return [row['word'].lower() for row in result.data or []]
        except APIError as e:
            logger.error(f"Error getting blocked words: {e}")
            raise DatabaseError(f"Failed to get blocked words: {e}")
            
    async def add_blocked_word(
        self,
        guild_id: int,
        word: str,
        added_by: int
    ) -> Dict[str, Any]:
        """Add a word to the blocked list."""
        try:
            data = {
                'guild_id': guild_id,
                'word': word.lower(),
                'added_by': added_by
            }
            result = self.client.table('blocked_words')\
                .insert(data)\
                .execute()
            return result.data[0] if result.data else None
        except APIError as e:
            if 'duplicate key' in str(e).lower():
                raise DatabaseError(f"Word '{word}' is already in the blocked list")
            logger.error(f"Error adding blocked word: {e}")
            raise DatabaseError(f"Failed to add blocked word: {e}")
            
    async def remove_blocked_word(self, guild_id: int, word: str) -> bool:
        """Remove a word from the blocked list."""
        try:
            self.client.table('blocked_words')\
                .delete()\
                .eq('guild_id', guild_id)\
                .eq('word', word.lower())\
                .execute()
            return True
        except APIError as e:
            logger.error(f"Error removing blocked word: {e}")
            raise DatabaseError(f"Failed to remove blocked word: {e}")
            
    # ============================================
    # Banned Users Operations
    # ============================================
    
    async def is_user_banned(self, guild_id: int, user_id: int) -> bool:
        """Check if a user is banned from submitting confessions."""
        try:
            result = self.client.table('banned_users')\
                .select('id')\
                .eq('guild_id', guild_id)\
                .eq('user_id', user_id)\
                .execute()
            return len(result.data or []) > 0
        except APIError as e:
            logger.error(f"Error checking banned user: {e}")
            raise DatabaseError(f"Failed to check banned status: {e}")
            
    async def ban_user(
        self,
        guild_id: int,
        user_id: int,
        banned_by: int,
        reason: str = None
    ) -> Dict[str, Any]:
        """Ban a user from submitting confessions."""
        try:
            data = {
                'guild_id': guild_id,
                'user_id': user_id,
                'banned_by': banned_by,
                'reason': reason
            }
            result = self.client.table('banned_users')\
                .insert(data)\
                .execute()
            return result.data[0] if result.data else None
        except APIError as e:
            if 'duplicate key' in str(e).lower():
                raise DatabaseError("User is already banned")
            logger.error(f"Error banning user: {e}")
            raise DatabaseError(f"Failed to ban user: {e}")
            
    async def unban_user(self, guild_id: int, user_id: int) -> bool:
        """Unban a user from submitting confessions."""
        try:
            self.client.table('banned_users')\
                .delete()\
                .eq('guild_id', guild_id)\
                .eq('user_id', user_id)\
                .execute()
            return True
        except APIError as e:
            logger.error(f"Error unbanning user: {e}")
            raise DatabaseError(f"Failed to unban user: {e}")
            
    async def get_banned_users(self, guild_id: int) -> List[Dict[str, Any]]:
        """Get all banned users for a guild."""
        try:
            result = self.client.table('banned_users')\
                .select('*')\
                .eq('guild_id', guild_id)\
                .order('banned_at', desc=True)\
                .execute()
            return result.data or []
        except APIError as e:
            logger.error(f"Error getting banned users: {e}")
            raise DatabaseError(f"Failed to get banned users: {e}")
            
    # ============================================
    # Cooldown Operations
    # ============================================
    
    async def get_last_submission(self, guild_id: int, user_id: int) -> Optional[datetime]:
        """Get the last submission time for a user."""
        try:
            result = self.client.table('user_cooldowns')\
                .select('last_submission_at')\
                .eq('guild_id', guild_id)\
                .eq('user_id', user_id)\
                .single()\
                .execute()
            if result.data and result.data.get('last_submission_at'):
                return datetime.fromisoformat(result.data['last_submission_at'].replace('Z', '+00:00'))
            return None
        except APIError as e:
            if '0 rows' in str(e):
                return None
            logger.error(f"Error getting cooldown: {e}")
            raise DatabaseError(f"Failed to get cooldown: {e}")
            
    async def update_cooldown(self, guild_id: int, user_id: int) -> bool:
        """Update the last submission time for a user."""
        try:
            # Upsert the cooldown record
            data = {
                'guild_id': guild_id,
                'user_id': user_id,
                'last_submission_at': datetime.now(timezone.utc).isoformat()
            }
            self.client.table('user_cooldowns')\
                .upsert(data, on_conflict='guild_id,user_id')\
                .execute()
            return True
        except APIError as e:
            logger.error(f"Error updating cooldown: {e}")
            raise DatabaseError(f"Failed to update cooldown: {e}")


# Global database instance
db = SupabaseClient()


def initialize_database(url: str, key: str):
    """Initialize the database connection."""
    db.initialize(url, key)
