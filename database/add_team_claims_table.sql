-- Create team_claims table for storing user team affiliations
CREATE TABLE IF NOT EXISTS team_claims (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL,
    team_abbreviation TEXT NOT NULL,
    display_name TEXT,
    username TEXT,
    claimed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create unique constraint to ensure one team per user
CREATE UNIQUE INDEX IF NOT EXISTS idx_team_claims_user_id ON team_claims(user_id);

-- Create unique constraint to ensure one user per team
CREATE UNIQUE INDEX IF NOT EXISTS idx_team_claims_team_abbreviation ON team_claims(team_abbreviation);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_team_claims_team_abbreviation_lookup ON team_claims(team_abbreviation);

-- Add trigger to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_team_claims_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_team_claims_updated_at
    BEFORE UPDATE ON team_claims
    FOR EACH ROW
    EXECUTE FUNCTION update_team_claims_updated_at();
