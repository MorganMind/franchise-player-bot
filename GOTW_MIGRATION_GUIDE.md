# GOTW System Migration Guide

## Overview
This guide explains how to migrate from the current JSON-based GOTW system to a robust, persistent system that survives bot restarts and handles button interactions properly.

## Problem Analysis
The root cause of the "interaction failed" errors was:

1. **Memory Loss on Restart**: Discord buttons persist in messages, but bot memory (`self.active_gotws` and `self.votes`) is lost
2. **No Recovery Mechanism**: No way to reconnect existing buttons to poll data after restart
3. **Fragile Data Storage**: JSON files can be corrupted or lost
4. **No Persistent Views**: Discord.py views timeout and become unresponsive

## Solution Components

### 1. Fixed JSON System (`gotw_system_fixed.py`)
- **Poll Recovery**: Attempts to recover poll data from message embeds
- **Persistent Views**: Uses `timeout=None` for views that survive restarts
- **Better Error Handling**: Graceful handling of missing poll data
- **Improved Data Loading**: Proper restoration of active polls and votes

### 2. Supabase Database System (`gotw_system_supabase.py`)
- **Database Persistence**: All poll data stored in PostgreSQL
- **Real-time Queries**: Efficient vote counting and poll management
- **Row Level Security**: Proper access controls
- **Scalable Architecture**: Handles multiple concurrent polls

### 3. Database Schema (`gotw_polls_schema.sql`)
- **gotw_polls table**: Stores poll metadata and status
- **gotw_votes table**: Stores individual votes with user tracking
- **Indexes**: Optimized for fast queries
- **Functions**: Helper functions for complex operations
- **Views**: Pre-computed poll results

## Migration Steps

### Option 1: Quick Fix (Recommended for Immediate Relief)

1. **Replace the current GOTW system**:
   ```bash
   # Backup current system
   cp madden_discord_bot/cogs/gotw_system.py madden_discord_bot/cogs/gotw_system_backup.py
   
   # Replace with fixed version
   cp madden_discord_bot/cogs/gotw_system_fixed.py madden_discord_bot/cogs/gotw_system.py
   ```

2. **Update bot.py to load the fixed system**:
   ```python
   # In bot.py, ensure the cog is loaded
   await self.load_extension('cogs.gotw_system')
   ```

3. **Deploy and test**:
   - The fixed system will attempt to recover existing polls
   - New polls will work properly
   - Buttons from before restart should work again

### Option 2: Full Database Migration (Recommended for Long-term)

1. **Set up Supabase database**:
   ```sql
   -- Run the schema file
   \i database/gotw_polls_schema.sql
   ```

2. **Migrate existing data**:
   ```python
   # Create a migration script
   import json
   from supabase import create_client
   
   # Load existing JSON data
   with open('data/gotw.json', 'r') as f:
       data = json.load(f)
   
   # Migrate to Supabase
   # (Implementation details in migration script)
   ```

3. **Switch to Supabase system**:
   ```bash
   # Replace with Supabase version
   cp madden_discord_bot/cogs/gotw_system_supabase.py madden_discord_bot/cogs/gotw_system.py
   ```

4. **Update bot.py**:
   ```python
   # Load the Supabase version
   await self.load_extension('cogs.gotw_system')
   ```

## Key Improvements

### Poll Recovery System
```python
async def recover_poll_from_message(self, message: discord.Message, gotw_id: str):
    """Try to recover poll data from the message embed"""
    # Parses embed content to reconstruct poll data
    # Handles missing or corrupted data gracefully
    # Returns None if recovery is impossible
```

### Persistent Views
```python
class GOTWView(discord.ui.View):
    def __init__(self, cog, team1: dict, team2: dict, poll_id: str):
        super().__init__(timeout=None)  # No timeout = persistent
        # Views survive bot restarts
```

### Database Integration
```python
# Efficient vote counting
result = await self.supabase.rpc('get_poll_with_votes', {'poll_id_param': poll_id}).execute()

# Atomic vote operations
await self.supabase.table('gotw_votes').delete().eq('poll_id', poll_id).eq('user_id', user_id).execute()
await self.supabase.table('gotw_votes').insert(vote_data).execute()
```

## Testing Checklist

### Before Migration
- [ ] Document current active polls
- [ ] Note any ongoing votes
- [ ] Backup current data files

### After Migration (Option 1)
- [ ] Test existing poll buttons work
- [ ] Create new poll and verify functionality
- [ ] Test vote recording and results display
- [ ] Test poll locking and winner declaration
- [ ] Restart bot and verify polls still work

### After Migration (Option 2)
- [ ] Verify database connection
- [ ] Test all poll operations
- [ ] Verify point awarding works
- [ ] Test with multiple concurrent polls
- [ ] Verify data persistence across restarts

## Rollback Plan

If issues occur:

1. **Quick Rollback**:
   ```bash
   cp madden_discord_bot/cogs/gotw_system_backup.py madden_discord_bot/cogs/gotw_system.py
   ```

2. **Database Rollback**:
   ```sql
   -- Drop new tables if needed
   DROP TABLE IF EXISTS gotw_votes;
   DROP TABLE IF EXISTS gotw_polls;
   ```

## Performance Considerations

### JSON System (Option 1)
- **Pros**: Simple, no external dependencies
- **Cons**: File I/O on every vote, potential corruption
- **Best for**: Small to medium usage

### Database System (Option 2)
- **Pros**: ACID compliance, concurrent access, scalability
- **Cons**: External dependency, more complex
- **Best for**: High usage, multiple servers

## Monitoring

### Key Metrics to Watch
- Poll creation success rate
- Vote recording success rate
- Button interaction response time
- Database connection health
- Error rates in logs

### Log Messages to Monitor
```
✅ GOTWSystem cog initialized with X active polls
Loaded X polls from storage
Error handling vote: [error details]
Error recovering poll from message: [error details]
```

## Support

### Common Issues
1. **"Poll not found" errors**: Check if poll recovery is working
2. **Database connection errors**: Verify Supabase credentials
3. **Button timeouts**: Ensure views are persistent (`timeout=None`)
4. **Vote not recording**: Check database permissions

### Debug Commands
```python
# Check active polls
logger.info(f"Active polls: {list(self.active_gotws.keys())}")

# Check database connection
result = await self.supabase.table('gotw_polls').select('count').execute()
logger.info(f"Database polls: {result.data}")

# Test poll recovery
recovered = await self.recover_poll_from_message(message, poll_id)
logger.info(f"Recovery result: {recovered}")
```

## Conclusion

The migration addresses the core issue of button persistence after bot restarts. Choose Option 1 for immediate relief, or Option 2 for a robust long-term solution. Both approaches eliminate the "interaction failed" errors and provide a stable GOTW system.
