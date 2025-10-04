-- GOTW Polls Database Schema for Supabase
-- This replaces the JSON file storage with proper database persistence

-- Create gotw_polls table
CREATE TABLE gotw_polls (
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
CREATE TABLE gotw_votes (
    poll_id VARCHAR(255) REFERENCES gotw_polls(id) ON DELETE CASCADE,
    user_id BIGINT NOT NULL,
    team_abbr VARCHAR(3) NOT NULL,
    voted_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (poll_id, user_id)
);

-- Create indexes for better performance
CREATE INDEX idx_gotw_polls_message_id ON gotw_polls(message_id);
CREATE INDEX idx_gotw_polls_created_by ON gotw_polls(created_by);
CREATE INDEX idx_gotw_polls_created_at ON gotw_polls(created_at);
CREATE INDEX idx_gotw_votes_poll_id ON gotw_votes(poll_id);
CREATE INDEX idx_gotw_votes_user_id ON gotw_votes(user_id);
CREATE INDEX idx_gotw_votes_team_abbr ON gotw_votes(team_abbr);

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

-- Add RLS (Row Level Security) policies
ALTER TABLE gotw_polls ENABLE ROW LEVEL SECURITY;
ALTER TABLE gotw_votes ENABLE ROW LEVEL SECURITY;

-- Allow authenticated users to read polls
CREATE POLICY "Allow authenticated users to read polls" ON gotw_polls
    FOR SELECT USING (auth.role() = 'authenticated');

-- Allow authenticated users to read votes
CREATE POLICY "Allow authenticated users to read votes" ON gotw_votes
    FOR SELECT USING (auth.role() = 'authenticated');

-- Allow authenticated users to insert polls
CREATE POLICY "Allow authenticated users to insert polls" ON gotw_polls
    FOR INSERT WITH CHECK (auth.role() = 'authenticated');

-- Allow authenticated users to insert votes
CREATE POLICY "Allow authenticated users to insert votes" ON gotw_votes
    FOR INSERT WITH CHECK (auth.role() = 'authenticated');

-- Allow authenticated users to update polls (for locking, winner declaration)
CREATE POLICY "Allow authenticated users to update polls" ON gotw_polls
    FOR UPDATE USING (auth.role() = 'authenticated');

-- Allow users to update their own votes (change vote)
CREATE POLICY "Allow users to update their own votes" ON gotw_votes
    FOR UPDATE USING (auth.role() = 'authenticated' AND user_id = auth.uid());

-- Allow users to delete their own votes (change vote)
CREATE POLICY "Allow users to delete their own votes" ON gotw_votes
    FOR DELETE USING (auth.role() = 'authenticated' AND user_id = auth.uid());

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

-- Create a function to migrate existing JSON data
CREATE OR REPLACE FUNCTION migrate_json_polls()
RETURNS VOID AS $$
BEGIN
    -- This function would be called from the Python code
    -- to migrate existing JSON data to the database
    RAISE NOTICE 'Migration function created. Call from Python code to migrate JSON data.';
END;
$$ LANGUAGE plpgsql;

-- Grant necessary permissions
GRANT USAGE ON SCHEMA public TO authenticated;
GRANT ALL ON gotw_polls TO authenticated;
GRANT ALL ON gotw_votes TO authenticated;
GRANT SELECT ON gotw_poll_results TO authenticated;
GRANT EXECUTE ON FUNCTION get_poll_with_votes(VARCHAR) TO authenticated;
GRANT EXECUTE ON FUNCTION migrate_json_polls() TO authenticated;
