#!/usr/bin/env python3
"""
Simple GOTW migration script
Run this after creating the database tables manually in Supabase dashboard
"""

import json
import os
from datetime import datetime
from supabase import create_client
from dotenv import load_dotenv

def main():
    print("🚀 Starting simple GOTW migration...")
    
    # Load environment variables
    load_dotenv('madden_discord_bot/.env')
    
    # Initialize Supabase client
    supabase_url = os.getenv('SUPABASE_URL')
    supabase_key = os.getenv('SUPABASE_ANON_KEY')
    
    if not supabase_url or not supabase_key:
        print("❌ Supabase credentials not found")
        return
    
    try:
        supabase = create_client(supabase_url, supabase_key)
        print("✅ Supabase client initialized")
    except Exception as e:
        print(f"❌ Error initializing Supabase client: {e}")
        return
    
    # Load existing data
    try:
        with open('madden_discord_bot/data/gotw.json', 'r') as f:
            data = json.load(f)
        print("✅ Loaded existing GOTW data")
    except Exception as e:
        print(f"❌ Error loading GOTW data: {e}")
        return
    
    # Migrate the current GOTW poll
    current_gotw = data.get('current_gotw')
    if not current_gotw:
        print("ℹ️  No current GOTW to migrate")
        return
    
    # Generate poll ID
    poll_id = f"{current_gotw['created_by']}_{int(datetime.now().timestamp())}"
    
    # Create poll data
    poll_data = {
        'id': poll_id,
        'team1_name': current_gotw['team1']['name'],
        'team1_abbr': current_gotw['team1']['abbreviation'],
        'team2_name': current_gotw['team2']['name'],
        'team2_abbr': current_gotw['team2']['abbreviation'],
        'created_by': current_gotw['created_by'],
        'created_at': current_gotw['created_at']
    }
    
    try:
        # Insert poll
        result = supabase.table('gotw_polls').insert(poll_data).execute()
        print(f"✅ Migrated poll: {poll_data['team1_name']} vs {poll_data['team2_name']}")
        print(f"   Poll ID: {poll_id}")
    except Exception as e:
        print(f"❌ Error inserting poll: {e}")
        return
    
    # Migrate votes
    votes = data.get('votes', {})
    vote_count = 0
    
    for user_id, team_abbr in votes.items():
        try:
            vote_data = {
                'poll_id': poll_id,
                'user_id': int(user_id),
                'team_abbr': team_abbr
            }
            supabase.table('gotw_votes').insert(vote_data).execute()
            vote_count += 1
            print(f"✅ Migrated vote: User {user_id} voted for {team_abbr}")
        except Exception as e:
            print(f"❌ Error migrating vote for user {user_id}: {e}")
    
    print(f"🎉 Migration complete!")
    print(f"   - 1 poll migrated")
    print(f"   - {vote_count} votes migrated")
    print(f"   - Poll ID: {poll_id}")
    print("")
    print("🔄 Next steps:")
    print("1. Replace gotw_system.py with gotw_system_supabase.py")
    print("2. Restart the bot")
    print("3. Test the new system")

if __name__ == "__main__":
    main()
