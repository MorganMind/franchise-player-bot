#!/usr/bin/env python3
"""
Migration script to move GOTW data from JSON to Supabase database
Run this script to migrate existing GOTW polls and votes to the database
"""

import json
import os
import sys
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables
load_dotenv('madden_discord_bot/.env')

def get_supabase_client():
    """Initialize Supabase client"""
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_ANON_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ Supabase credentials not found in environment variables")
        print("Make sure SUPABASE_URL and SUPABASE_ANON_KEY are set")
        sys.exit(1)
    
    try:
        client = create_client(supabase_url, supabase_key)
        print("✅ Supabase client initialized")
        return client
    except Exception as e:
        print(f"❌ Error initializing Supabase client: {e}")
        sys.exit(1)

def create_tables(supabase: Client):
    """Create the GOTW tables in Supabase"""
    print("📋 Creating database tables...")
    
    # Create gotw_polls table
    polls_table_sql = """
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
    """
    
    # Create gotw_votes table
    votes_table_sql = """
    CREATE TABLE IF NOT EXISTS gotw_votes (
        poll_id VARCHAR(255) REFERENCES gotw_polls(id) ON DELETE CASCADE,
        user_id BIGINT NOT NULL,
        team_abbr VARCHAR(3) NOT NULL,
        voted_at TIMESTAMP DEFAULT NOW(),
        PRIMARY KEY (poll_id, user_id)
    );
    """
    
    # Create indexes
    indexes_sql = [
        "CREATE INDEX IF NOT EXISTS idx_gotw_polls_message_id ON gotw_polls(message_id);",
        "CREATE INDEX IF NOT EXISTS idx_gotw_polls_created_by ON gotw_polls(created_by);",
        "CREATE INDEX IF NOT EXISTS idx_gotw_polls_created_at ON gotw_polls(created_at);",
        "CREATE INDEX IF NOT EXISTS idx_gotw_votes_poll_id ON gotw_votes(poll_id);",
        "CREATE INDEX IF NOT EXISTS idx_gotw_votes_user_id ON gotw_votes(user_id);",
        "CREATE INDEX IF NOT EXISTS idx_gotw_votes_team_abbr ON gotw_votes(team_abbr);"
    ]
    
    try:
        # Execute table creation
        supabase.rpc('exec_sql', {'sql': polls_table_sql}).execute()
        supabase.rpc('exec_sql', {'sql': votes_table_sql}).execute()
        
        # Execute indexes
        for index_sql in indexes_sql:
            supabase.rpc('exec_sql', {'sql': index_sql}).execute()
        
        print("✅ Database tables created successfully")
        return True
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        print("You may need to create the tables manually in the Supabase dashboard")
        return False

def load_json_data():
    """Load existing GOTW data from JSON file"""
    gotw_file = "madden_discord_bot/data/gotw.json"
    
    if not os.path.exists(gotw_file):
        print(f"❌ GOTW data file not found: {gotw_file}")
        return None, None
    
    try:
        with open(gotw_file, 'r') as f:
            data = json.load(f)
        
        active_gotws = data.get('active_gotws', {})
        votes = data.get('votes', {})
        
        print(f"📊 Loaded {len(active_gotws)} active polls and {len(votes)} vote records")
        return active_gotws, votes
    except Exception as e:
        print(f"❌ Error loading JSON data: {e}")
        return None, None

def migrate_polls(supabase: Client, active_gotws: dict):
    """Migrate polls from JSON to database"""
    print("🔄 Migrating polls to database...")
    
    migrated_count = 0
    failed_count = 0
    
    for poll_id, poll_data in active_gotws.items():
        try:
            # Prepare poll data for database
            db_poll = {
                'id': poll_id,
                'team1_name': poll_data.get('team1', {}).get('name', 'Unknown'),
                'team1_abbr': poll_data.get('team1', {}).get('abbreviation', 'UNK'),
                'team2_name': poll_data.get('team2', {}).get('name', 'Unknown'),
                'team2_abbr': poll_data.get('team2', {}).get('abbreviation', 'UNK'),
                'message_id': poll_data.get('message_id'),
                'channel_id': poll_data.get('channel_id'),
                'guild_id': poll_data.get('guild_id'),
                'created_by': poll_data.get('created_by', 0),
                'is_locked': poll_data.get('is_locked', False),
                'winner_declared': poll_data.get('winner_declared', False),
                'winner_team': poll_data.get('winner_team'),
                'winner_declared_by': poll_data.get('winner_declared_by'),
                'winner_declared_at': poll_data.get('winner_declared_at'),
                'created_at': poll_data.get('created_at', datetime.now().isoformat())
            }
            
            # Insert poll into database
            result = supabase.table('gotw_polls').upsert(db_poll).execute()
            
            if result.data:
                migrated_count += 1
                print(f"  ✅ Migrated poll: {poll_data.get('team1', {}).get('name', 'Unknown')} vs {poll_data.get('team2', {}).get('name', 'Unknown')}")
            else:
                failed_count += 1
                print(f"  ❌ Failed to migrate poll: {poll_id}")
                
        except Exception as e:
            failed_count += 1
            print(f"  ❌ Error migrating poll {poll_id}: {e}")
    
    print(f"📊 Poll migration complete: {migrated_count} successful, {failed_count} failed")
    return migrated_count, failed_count

def migrate_votes(supabase: Client, votes: dict):
    """Migrate votes from JSON to database"""
    print("🔄 Migrating votes to database...")
    
    migrated_count = 0
    failed_count = 0
    
    for poll_id, poll_votes in votes.items():
        try:
            # Check if poll exists in database
            poll_check = supabase.table('gotw_polls').select('id').eq('id', poll_id).execute()
            if not poll_check.data:
                print(f"  ⚠️  Skipping votes for poll {poll_id} - poll not found in database")
                continue
            
            # Migrate votes for this poll
            for team_abbr, user_votes in poll_votes.items():
                for user_id in user_votes:
                    try:
                        vote_data = {
                            'poll_id': poll_id,
                            'user_id': int(user_id),
                            'team_abbr': team_abbr
                        }
                        
                        result = supabase.table('gotw_votes').upsert(vote_data).execute()
                        if result.data:
                            migrated_count += 1
                        else:
                            failed_count += 1
                            
                    except Exception as e:
                        failed_count += 1
                        print(f"  ❌ Error migrating vote for user {user_id} in poll {poll_id}: {e}")
            
            print(f"  ✅ Migrated votes for poll: {poll_id}")
            
        except Exception as e:
            failed_count += 1
            print(f"  ❌ Error migrating votes for poll {poll_id}: {e}")
    
    print(f"📊 Vote migration complete: {migrated_count} successful, {failed_count} failed")
    return migrated_count, failed_count

def verify_migration(supabase: Client):
    """Verify the migration was successful"""
    print("🔍 Verifying migration...")
    
    try:
        # Count polls in database
        polls_result = supabase.table('gotw_polls').select('id', count='exact').execute()
        polls_count = polls_result.count
        
        # Count votes in database
        votes_result = supabase.table('gotw_votes').select('poll_id', count='exact').execute()
        votes_count = votes_result.count
        
        print(f"✅ Database contains {polls_count} polls and {votes_count} votes")
        
        # Show sample data
        sample_polls = supabase.table('gotw_polls').select('*').limit(3).execute()
        if sample_polls.data:
            print("📋 Sample polls:")
            for poll in sample_polls.data:
                print(f"  - {poll['team1_name']} vs {poll['team2_name']} (ID: {poll['id']})")
        
        return True
        
    except Exception as e:
        print(f"❌ Error verifying migration: {e}")
        return False

def main():
    """Main migration function"""
    print("🚀 Starting GOTW migration to Supabase...")
    print("=" * 50)
    
    # Initialize Supabase client
    supabase = get_supabase_client()
    
    # Create tables
    if not create_tables(supabase):
        print("❌ Failed to create tables. Please create them manually in Supabase dashboard.")
        return
    
    # Load JSON data
    active_gotws, votes = load_json_data()
    if active_gotws is None:
        print("❌ No JSON data to migrate")
        return
    
    # Migrate polls
    poll_success, poll_failed = migrate_polls(supabase, active_gotws)
    
    # Migrate votes
    vote_success, vote_failed = migrate_votes(supabase, votes)
    
    # Verify migration
    if verify_migration(supabase):
        print("=" * 50)
        print("🎉 Migration completed successfully!")
        print(f"📊 Results:")
        print(f"  - Polls: {poll_success} migrated, {poll_failed} failed")
        print(f"  - Votes: {vote_success} migrated, {vote_failed} failed")
        print("")
        print("🔄 Next steps:")
        print("1. Replace gotw_system.py with gotw_system_supabase.py")
        print("2. Update bot.py to load the new system")
        print("3. Test the new system")
        print("4. Backup and remove old JSON files")
    else:
        print("❌ Migration verification failed")

if __name__ == "__main__":
    main()
