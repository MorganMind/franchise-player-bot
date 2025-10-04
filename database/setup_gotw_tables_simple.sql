-- Simple GOTW Database Setup Script
-- Run this in your Supabase SQL editor to create the required tables

-- Create gotw_polls table
CREATE TABLE IF NOT EXISTS gotw_polls (
    id VARCHAR(255) PRIMARY KEY,
    team1_name VARCHAR(255) NOT NULL,
    team1_abbr VARCHAR(3) NOT NULL,
    team2_name VARCHAR(255) NOT NULL,
    team2_abbr VARCHAR(3) NOT NULL,
    message_id BIGINT,
    channel_id BIGINT,
    guild_id BIGINT,
    created_by BIGINT NOT NULL,
    is_locked BOOLEAN DEFAULT FALSE,
    winner_declared BOOLEAN DEFAULT FALSE,
    winner_team VARCHAR(3),
    winner_declared_by BIGINT,
    winner_declared_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Create gotw_votes table
CREATE TABLE IF NOT EXISTS gotw_votes (
    poll_id VARCHAR(255) REFERENCES gotw_polls(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL,
    team_abbr VARCHAR(3) NOT NULL,
    voted_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (poll_id, user_id)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_gotw_polls_message_id ON gotw_polls(message_id);
CREATE INDEX IF NOT EXISTS idx_gotw_polls_created_by ON gotw_polls(created_by);
CREATE INDEX IF NOT EXISTS idx_gotw_polls_created_at ON gotw_polls(created_at);
CREATE INDEX IF NOT EXISTS idx_gotw_votes_poll_id ON gotw_votes(poll_id);
CREATE INDEX IF NOT EXISTS idx_gotw_votes_user_id ON gotw_votes(user_id);
CREATE INDEX IF NOT EXISTS idx_gotw_votes_team_abbr ON gotw_votes(team_abbr);

-- Create updated_at trigger for gotw_polls
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_gotw_polls_updated_at 
    BEFORE UPDATE ON gotw_polls 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

-- Create a view for poll results
CREATE VIEW gotw_poll_results AS
SELECT 
    p.id,
    p.team1_name,
    p.team1_abbr,
    p.team2_name,
    p.team2_abbr,
    p.is_locked,
    p.winner_declared,
    p.winner_team,
    p.created_at,
    COUNT(CASE WHEN v.team_abbr = p.team1_abbr THEN 1 END) as team1_votes,
    COUNT(CASE WHEN v.team_abbr = p.team2_abbr THEN 1 END) as team2_votes,
    COUNT(v.user_id) as total_votes
FROM gotw_polls p
LEFT JOIN gotw_votes v ON p.id = v.poll_id
GROUP BY p.id, p.team1_name, p.team1_abbr, p.team2_name, p.team2_abbr, 
         p.is_locked, p.winner_declared, p.winner_team, p.created_at;

-- Create a function to get poll with vote details
CREATE OR REPLACE FUNCTION get_poll_with_votes(poll_id_param VARCHAR(255))
RETURNS TABLE (
    poll_id VARCHAR(255),
    team1_name VARCHAR(255),
    team1_abbr VARCHAR(3),
    team2_name VARCHAR(255),
    team2_abbr VARCHAR(3),
    is_locked BOOLEAN,
    winner_declared BOOLEAN,
    winner_team VARCHAR(3),
    team1_votes BIGINT,
    team2_votes BIGINT,
    total_votes BIGINT,
    team1_voters BIGINT[],
    team2_voters BIGINT[]
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.id,
        p.team1_name,
        p.team1_abbr,
        p.team2_name,
        p.team2_abbr,
        p.is_locked,
        p.winner_declared,
        p.winner_team,
        COUNT(CASE WHEN v.team_abbr = p.team1_abbr THEN 1 END) as team1_votes,
        COUNT(CASE WHEN v.team_abbr = p.team2_abbr THEN 1 END) as team2_votes,
        COUNT(v.user_id) as total_votes,
        ARRAY_AGG(CASE WHEN v.team_abbr = p.team1_abbr THEN v.user_id END) FILTER (WHERE v.team_abbr = p.team1_abbr) as team1_voters,
        ARRAY_AGG(CASE WHEN v.team_abbr = p.team2_abbr THEN v.user_id END) FILTER (WHERE v.team_abbr = p.team2_abbr) as team2_voters
    FROM gotw_polls p
    LEFT JOIN gotw_votes v ON p.id = v.poll_id
    WHERE p.id = poll_id_param
    GROUP BY p.id, p.team1_name, p.team1_abbr, p.team2_name, p.team2_abbr, 
             p.is_locked, p.winner_declared, p.winner_team;
END;
$$ LANGUAGE plpgsql;

-- Grant necessary permissions (without RLS for simplicity)
GRANT USAGE ON SCHEMA public TO authenticated;
GRANT ALL ON gotw_polls TO authenticated;
GRANT ALL ON gotw_votes TO authenticated;
GRANT SELECT ON gotw_poll_results TO authenticated;
GRANT EXECUTE ON FUNCTION get_poll_with_votes(VARCHAR) TO authenticated;
