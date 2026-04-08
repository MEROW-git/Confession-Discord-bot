-- ============================================
-- Anonymous Confession Bot - Database Schema
-- For Supabase PostgreSQL
-- ============================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================
-- Table: guild_settings
-- Stores configuration for each Discord server
-- ============================================
CREATE TABLE IF NOT EXISTS guild_settings (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL UNIQUE,
    guild_name VARCHAR(255),
    confession_channel_id BIGINT,
    review_channel_id BIGINT,
    admin_role_id BIGINT,
    badword_filter_enabled BOOLEAN DEFAULT FALSE,
    cooldown_seconds INTEGER DEFAULT 300,  -- Default 5 minutes
    filter_action VARCHAR(20) DEFAULT 'flag',  -- 'flag', 'reject', 'censor'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for faster guild lookups
CREATE INDEX IF NOT EXISTS idx_guild_settings_guild_id ON guild_settings(guild_id);

-- ============================================
-- Table: confessions
-- Stores all confession submissions
-- ============================================
CREATE TABLE IF NOT EXISTS confessions (
    id SERIAL PRIMARY KEY,
    confession_number INTEGER NOT NULL,  -- Per-guild confession number
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,  -- Kept private for moderation
    content TEXT NOT NULL,
    category VARCHAR(50),
    status VARCHAR(20) DEFAULT 'pending',  -- 'pending', 'approved', 'rejected', 'flagged'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    reviewed_by BIGINT,  -- Admin who reviewed
    reviewed_at TIMESTAMP WITH TIME ZONE,
    public_message_id BIGINT,  -- Message ID in public channel
    review_message_id BIGINT,  -- Message ID in review channel
    filter_flagged BOOLEAN DEFAULT FALSE,
    filter_matched_words TEXT[],  -- Array of matched bad words
    
    CONSTRAINT valid_status CHECK (status IN ('pending', 'approved', 'rejected', 'flagged'))
);

-- Indexes for confession queries
CREATE INDEX IF NOT EXISTS idx_confessions_guild_id ON confessions(guild_id);
CREATE INDEX IF NOT EXISTS idx_confessions_user_id ON confessions(user_id);
CREATE INDEX IF NOT EXISTS idx_confessions_status ON confessions(status);
CREATE INDEX IF NOT EXISTS idx_confessions_guild_number ON confessions(guild_id, confession_number);

-- ============================================
-- Table: blocked_words
-- Bad words filter list per guild
-- ============================================
CREATE TABLE IF NOT EXISTS blocked_words (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    word VARCHAR(100) NOT NULL,
    added_by BIGINT NOT NULL,
    added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(guild_id, word)
);

-- Index for blocked words
CREATE INDEX IF NOT EXISTS idx_blocked_words_guild_id ON blocked_words(guild_id);

-- ============================================
-- Table: banned_users
-- Users banned from submitting confessions per guild
-- ============================================
CREATE TABLE IF NOT EXISTS banned_users (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    banned_by BIGINT NOT NULL,
    reason TEXT,
    banned_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(guild_id, user_id)
);

-- Index for banned users
CREATE INDEX IF NOT EXISTS idx_banned_users_guild_id ON banned_users(guild_id);
CREATE INDEX IF NOT EXISTS idx_banned_users_user_id ON banned_users(user_id);

-- ============================================
-- Table: user_cooldowns
-- Tracks user submission cooldowns per guild
-- ============================================
CREATE TABLE IF NOT EXISTS user_cooldowns (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    last_submission_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(guild_id, user_id)
);

-- Index for cooldown lookups
CREATE INDEX IF NOT EXISTS idx_user_cooldowns_guild_user ON user_cooldowns(guild_id, user_id);

-- ============================================
-- Function to get next confession number
-- ============================================
CREATE OR REPLACE FUNCTION get_next_confession_number(p_guild_id BIGINT)
RETURNS INTEGER AS $$
DECLARE
    next_num INTEGER;
BEGIN
    SELECT COALESCE(MAX(confession_number), 0) + 1
    INTO next_num
    FROM confessions
    WHERE guild_id = p_guild_id;
    
    RETURN next_num;
END;
$$ LANGUAGE plpgsql;

-- ============================================
-- Function to update updated_at timestamp
-- ============================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for guild_settings updated_at
DROP TRIGGER IF EXISTS update_guild_settings_updated_at ON guild_settings;
CREATE TRIGGER update_guild_settings_updated_at
    BEFORE UPDATE ON guild_settings
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- Row Level Security (RLS) Policies
-- Enable RLS on all tables for security
-- ============================================

-- Enable RLS
ALTER TABLE guild_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE confessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE blocked_words ENABLE ROW LEVEL SECURITY;
ALTER TABLE banned_users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_cooldowns ENABLE ROW LEVEL SECURITY;

-- Note: Create appropriate policies based on your access patterns
-- For bot usage with service role key, you may disable RLS or use service role
-- These are basic policies for reference:

-- Allow all operations for service role (bot backend)
CREATE POLICY IF NOT EXISTS service_role_all_guild_settings ON guild_settings
    FOR ALL USING (true) WITH CHECK (true);
    
CREATE POLICY IF NOT EXISTS service_role_all_confessions ON confessions
    FOR ALL USING (true) WITH CHECK (true);
    
CREATE POLICY IF NOT EXISTS service_role_all_blocked_words ON blocked_words
    FOR ALL USING (true) WITH CHECK (true);
    
CREATE POLICY IF NOT EXISTS service_role_all_banned_users ON banned_users
    FOR ALL USING (true) WITH CHECK (true);
    
CREATE POLICY IF NOT EXISTS service_role_all_user_cooldowns ON user_cooldowns
    FOR ALL USING (true) WITH CHECK (true);

-- ============================================
-- Comments for documentation
-- ============================================
COMMENT ON TABLE guild_settings IS 'Configuration settings for each Discord guild';
COMMENT ON TABLE confessions IS 'Anonymous confession submissions';
COMMENT ON TABLE blocked_words IS 'Bad words list for content filtering per guild';
COMMENT ON TABLE banned_users IS 'Users banned from using the confession system per guild';
COMMENT ON TABLE user_cooldowns IS 'Tracks last submission time for cooldown enforcement';
