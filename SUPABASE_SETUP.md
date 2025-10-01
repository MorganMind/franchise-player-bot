# Supabase Migration Setup Guide

## Prerequisites

1. **Supabase Account**: Sign up at [supabase.com](https://supabase.com)
2. **Python Dependencies**: Install the new requirements

## Step 1: Install Dependencies

```bash
cd madden_discord_bot
pip install -r requirements.txt
```

## Step 2: Set Up Supabase Project

1. Create a new project in Supabase
2. Go to Settings > API
3. Copy your Project URL and anon/public key

## Step 3: Environment Variables

Add these to your `.env` file:

```env
# Existing variables
DISCORD_TOKEN=your_discord_bot_token_here
OPENAI_API_KEY=your_openai_api_key_here

# New Supabase variables
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_ANON_KEY=your_supabase_anon_key_here
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key_here
```

## Step 4: Apply Database Schema

1. Go to your Supabase project dashboard
2. Navigate to SQL Editor
3. Copy and paste the contents of `database/schema.sql`
4. Run the SQL to create all tables

## Step 5: Run Migration

```bash
python3 database/migrate_to_supabase.py
```

This will:
- Create all necessary tables
- Migrate your existing JSON data to Supabase
- Preserve all user points and settings

## Step 6: Update Bot Configuration

Replace the old points system with the new Supabase version:

1. **Backup your current bot** (optional but recommended)
2. **Update bot.py** to load the new Supabase cog instead of the old one
3. **Test the migration** with a small group first

## Step 7: Verify Migration

1. Check that all users appear in the leaderboard
2. Test adding/removing points
3. Verify all commands work correctly

## Rollback Plan

If you need to rollback:
1. The original JSON files are preserved
2. Simply switch back to the original `points_system.py` cog
3. Your data will be exactly as it was before

## Benefits After Migration

- **Better Performance**: Database queries are faster than JSON file operations
- **Concurrent Access**: Multiple operations won't conflict
- **Data Integrity**: ACID transactions ensure data consistency
- **Scalability**: Can handle many more users
- **Backup**: Automatic backups in Supabase
- **Real-time**: Potential for real-time features later

## Troubleshooting

### Connection Issues
- Verify your Supabase URL and keys are correct
- Check that your project is active in Supabase
- Ensure your IP is not blocked (if using IP restrictions)

### Migration Errors
- Check the logs for specific error messages
- Verify your JSON files are valid
- Ensure all required tables exist in Supabase

### Bot Issues
- Check that the new cog is loaded correctly
- Verify environment variables are set
- Test with a simple command first

## Support

If you encounter issues:
1. Check the bot logs for error messages
2. Verify your Supabase project settings
3. Test the connection with a simple query
