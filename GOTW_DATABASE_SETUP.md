# GOTW Database Setup Instructions

## Step 1: Create Database Tables

Go to your Supabase dashboard and run this SQL in the SQL editor:

**Copy and paste the entire contents of `database/setup_gotw_tables_simple.sql`**

Or run this simplified version:

```sql
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

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_gotw_polls_message_id ON gotw_polls(message_id);
CREATE INDEX IF NOT EXISTS idx_gotw_polls_created_by ON gotw_polls(created_by);
CREATE INDEX IF NOT EXISTS idx_gotw_votes_poll_id ON gotw_votes(poll_id);
CREATE INDEX IF NOT EXISTS idx_gotw_votes_user_id ON gotw_votes(user_id);
```

## Step 2: Migrate Existing Data

After creating the tables, run this Python script to migrate your existing data:

```python
import json
import os
from datetime import datetime
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv('madden_discord_bot/.env')

# Initialize Supabase client
supabase = create_client(
    os.getenv('SUPABASE_URL'),
    os.getenv('SUPABASE_ANON_KEY')
)

# Load existing data
with open('madden_discord_bot/data/gotw.json', 'r') as f:
    data = json.load(f)

# Migrate the current GOTW poll
current_gotw = data.get('current_gotw')
if current_gotw:
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
    
    # Insert poll
    result = supabase.table('gotw_polls').insert(poll_data).execute()
    print(f"✅ Migrated poll: {poll_data['team1_name']} vs {poll_data['team2_name']}")
    
    # Migrate votes
    votes = data.get('votes', {})
    for user_id, team_abbr in votes.items():
        vote_data = {
            'poll_id': poll_id,
            'user_id': int(user_id),
            'team_abbr': team_abbr
        }
        supabase.table('gotw_votes').insert(vote_data).execute()
        print(f"✅ Migrated vote: User {user_id} voted for {team_abbr}")

print("🎉 Migration complete!")
```

## Step 3: Replace GOTW System

1. **Backup current system**:
   ```bash
   cp madden_discord_bot/cogs/gotw_system.py madden_discord_bot/cogs/gotw_system_backup.py
   ```

2. **Replace with Supabase version**:
   ```bash
   cp madden_discord_bot/cogs/gotw_system_supabase.py madden_discord_bot/cogs/gotw_system.py
   ```

3. **Update bot.py** (if needed):
   ```python
   # Make sure the cog is loaded
   await self.load_extension('cogs.gotw_system')
   ```

## Step 4: Test the System

1. **Start the bot** and check logs for:
   ```
   ✅ Supabase client initialized for GOTW system
   ✅ GOTWSystemSupabase cog initialized
   ```

2. **Test creating a new poll**:
   - Use `/gotw` command
   - Verify poll is created in database

3. **Test voting**:
   - Click vote buttons
   - Verify votes are recorded in database

4. **Test results**:
   - Click "Show Results" button
   - Verify vote counts are correct

## Step 5: Clean Up

After confirming everything works:

1. **Backup old JSON files**:
   ```bash
   mkdir -p backup_json_files
   cp madden_discord_bot/data/gotw.json backup_json_files/
   ```

2. **Remove old JSON files** (optional):
   ```bash
   rm madden_discord_bot/data/gotw.json
   ```

## Troubleshooting

### Database Connection Issues
- Verify Supabase credentials in `.env` file
- Check Supabase dashboard for connection status
- Ensure RLS policies allow your operations

### Migration Issues
- Check that tables were created successfully
- Verify data types match between JSON and database
- Check for duplicate primary keys

### Bot Issues
- Check logs for Supabase connection errors
- Verify cog is loading properly
- Test with a simple poll first

## Benefits of Database Migration

1. **Persistence**: Polls survive bot restarts
2. **Scalability**: Handle multiple concurrent polls
3. **Reliability**: ACID compliance and data integrity
4. **Performance**: Indexed queries and efficient storage
5. **Backup**: Automatic database backups
6. **Analytics**: Easy to query vote patterns and statistics

## Next Steps

After successful migration:
1. Monitor bot logs for any errors
2. Test all GOTW functionality thoroughly
3. Consider adding more features like poll analytics
4. Set up database monitoring and alerts
