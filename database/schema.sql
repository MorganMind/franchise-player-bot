-- Supabase Database Schema for Franchise Player Bot
-- This file contains all the table definitions for migrating from JSON to Supabase

-- Enable necessary extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Users table - stores user information and points
CREATE TABLE IF NOT EXISTS users (
    id BIGINT PRIMARY KEY, -- Discord user ID
    display_name TEXT,
    username TEXT,
    total_points INTEGER DEFAULT 0,
    stream_points INTEGER DEFAULT 0,
    other_points INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Player cards table - stores user's player cards
CREATE TABLE IF NOT EXISTS player_cards (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    position TEXT NOT NULL,
    attributes JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Game of the Week table
CREATE TABLE IF NOT EXISTS gotw (
    id SERIAL PRIMARY KEY,
    week INTEGER NOT NULL,
    season INTEGER NOT NULL,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    home_score INTEGER DEFAULT 0,
    away_score INTEGER DEFAULT 0,
    is_completed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(week, season)
);

-- NFL Schedule table
CREATE TABLE IF NOT EXISTS nfl_schedule (
    id SERIAL PRIMARY KEY,
    week INTEGER NOT NULL,
    season INTEGER NOT NULL,
    home_team TEXT NOT NULL,
    away_team TEXT NOT NULL,
    game_time TIMESTAMP WITH TIME ZONE,
    is_completed BOOLEAN DEFAULT FALSE,
    home_score INTEGER DEFAULT 0,
    away_score INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Stream links table
CREATE TABLE IF NOT EXISTS stream_links (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    url TEXT NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Server settings table (for any server-specific configurations)
CREATE TABLE IF NOT EXISTS server_settings (
    id SERIAL PRIMARY KEY,
    guild_id BIGINT NOT NULL,
    setting_key TEXT NOT NULL,
    setting_value JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(guild_id, setting_key)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_total_points ON users(total_points DESC);
CREATE INDEX IF NOT EXISTS idx_player_cards_user_id ON player_cards(user_id);
CREATE INDEX IF NOT EXISTS idx_gotw_week_season ON gotw(week, season);
CREATE INDEX IF NOT EXISTS idx_nfl_schedule_week_season ON nfl_schedule(week, season);
CREATE INDEX IF NOT EXISTS idx_stream_links_active ON stream_links(is_active);
CREATE INDEX IF NOT EXISTS idx_server_settings_guild_id ON server_settings(guild_id);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers for updated_at
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_player_cards_updated_at BEFORE UPDATE ON player_cards
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_gotw_updated_at BEFORE UPDATE ON gotw
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_nfl_schedule_updated_at BEFORE UPDATE ON nfl_schedule
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_stream_links_updated_at BEFORE UPDATE ON stream_links
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_server_settings_updated_at BEFORE UPDATE ON server_settings
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Enable Row Level Security (RLS) for better security
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE player_cards ENABLE ROW LEVEL SECURITY;
ALTER TABLE gotw ENABLE ROW LEVEL SECURITY;
ALTER TABLE nfl_schedule ENABLE ROW LEVEL SECURITY;
ALTER TABLE stream_links ENABLE ROW LEVEL SECURITY;
ALTER TABLE server_settings ENABLE ROW LEVEL SECURITY;

-- Create policies (allow all for now, can be restricted later)
CREATE POLICY "Allow all operations on users" ON users FOR ALL USING (true);
CREATE POLICY "Allow all operations on player_cards" ON player_cards FOR ALL USING (true);
CREATE POLICY "Allow all operations on gotw" ON gotw FOR ALL USING (true);
CREATE POLICY "Allow all operations on nfl_schedule" ON nfl_schedule FOR ALL USING (true);
CREATE POLICY "Allow all operations on stream_links" ON stream_links FOR ALL USING (true);
CREATE POLICY "Allow all operations on server_settings" ON server_settings FOR ALL USING (true);
