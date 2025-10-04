# GOTW (Game of the Week) System Documentation

## Overview
The GOTW system is a Discord bot feature that allows users to create polls for NFL games, vote on their preferred team, and declare winners. It includes real-time vote tracking, team claim integration, and point awarding systems.

## Architecture

### Core Components
1. **GOTW System Cog** (`madden_discord_bot/cogs/gotw_system.py`)
2. **Team Claim System** (`madden_discord_bot/cogs/team_claim_system.py`)
3. **Points System** (`madden_discord_bot/cogs/points_system_supabase.py`)
4. **Supabase Database** (PostgreSQL)
5. **Discord API Integration**

## Database Schema

### Supabase Tables

#### `users` Table
```sql
CREATE TABLE users (
    user_id BIGINT PRIMARY KEY,
    username VARCHAR(255),
    display_name VARCHAR(255),
    total_points INTEGER DEFAULT 0,
    stream_points INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### `team_claims` Table
```sql
CREATE TABLE team_claims (
    user_id BIGINT REFERENCES users(user_id),
    team_abbreviation VARCHAR(3) NOT NULL,
    display_name VARCHAR(255),
    username VARCHAR(255),
    claimed_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (user_id),
    UNIQUE (team_abbreviation)
);
```

#### `points_history` Table (Optional - for audit trail)
```sql
CREATE TABLE points_history (
    id SERIAL PRIMARY KEY,
    user_id BIGINT REFERENCES users(user_id),
    points_change INTEGER NOT NULL,
    reason VARCHAR(255),
    source VARCHAR(100), -- 'gotw_vote', 'gotw_team_claim', 'stream', etc.
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Discord Integration

### Slash Commands
- `/gotw` - Create a new GOTW poll with team selection
- `/claimteam` - Claim an NFL team for point bonuses
- `/teamslist` - List all teams and their claimed status
- `/removeteam` - Remove a team claim (commissioner only)

### Interactive Components
- **Team Selection Dropdowns** - AFC/NFC split for team selection
- **Vote Buttons** - Team-specific voting buttons
- **Results Button** - Show detailed vote breakdown
- **Winner Declaration Buttons** - Declare poll winner
- **Lock Button** - Lock poll from further voting

### Discord API Features Used
- **Slash Commands** with autocomplete
- **Select Menus** for team selection
- **Buttons** for voting and actions
- **Embeds** for rich message formatting
- **Ephemeral Messages** for private interactions
- **Message Editing** for real-time updates

## Core Code Structure

### GOTW System Class
```python
class GOTWSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.gotw_file = "data/gotw.json"
        self.teams_file = "data/nfl_teams.json"
        self.active_gotws = {}  # Dictionary of message_id -> gotw_data
        self.votes = {}  # Dictionary of message_id -> votes
        
        # Hardcoded poll data for Washington/Tennessee poll
        self.hardcoded_poll_id = "recreated_1759543801"
        self.hardcoded_votes = {
            "WAS": set(),  # Set of user IDs who voted for Washington
            "TEN": set()   # Set of user IDs who voted for Tennessee
        }
        
        self.load_gotw_data()
        self.load_teams()
```

### Key Methods

#### Poll Creation
```python
@app_commands.command(name="gotw", description="Create a Game of the Week poll")
@app_commands.describe(
    team1="First team (optional - use autocomplete)",
    team2="Second team (optional - use autocomplete)"
)
async def gotw(self, interaction: discord.Interaction, team1: str = None, team2: str = None):
    """Create a GOTW poll with team selection"""
    if team1 and team2:
        # Direct creation with provided teams
        await self.create_gotw(interaction, team1, team2)
    else:
        # Interactive team selection
        await self.setup_gotw_creation(interaction)
```

#### Vote Handling
```python
async def handle_vote(self, interaction: discord.Interaction, team_abbreviation: str, gotw_id: str):
    """Handle a vote for a specific team in a GOTW poll"""
    # Get poll data
    gotw_data = self.active_gotws.get(gotw_id)
    if not gotw_data:
        await interaction.response.send_message("❌ Poll not found.", ephemeral=True)
        return
    
    # Check if poll is locked
    if gotw_data.get('is_locked', False):
        await interaction.response.send_message("❌ This poll is locked.", ephemeral=True)
        return
    
    # Record vote
    user_id = str(interaction.user.id)
    poll_votes = self.votes.get(gotw_id, {})
    
    # Remove user from other team's votes
    for team in poll_votes:
        if user_id in poll_votes[team]:
            poll_votes[team].remove(user_id)
    
    # Add user to selected team's votes
    if team_abbreviation not in poll_votes:
        poll_votes[team_abbreviation] = []
    poll_votes[team_abbreviation].append(user_id)
    
    # Save votes
    self.votes[gotw_id] = poll_votes
    self.save_gotw_data()
    
    # Update message with new vote counts
    await self.update_vote_message(message, gotw_id)
```

#### Winner Declaration
```python
async def handle_declare_winner(self, interaction: discord.Interaction, gotw_id: str, winning_team: str):
    """Declare a winner for a GOTW poll and award points"""
    # Award points to voters
    points_cog = self.bot.get_cog('PointsSystemSupabase')
    if points_cog:
        poll_votes = self.votes.get(gotw_id, {})
        winning_voters = poll_votes.get(winning_team, [])
        
        for user_id in winning_voters:
            await points_cog.add_user_points(int(user_id), 1)
    
    # Award points to team claimers
    team_claim_cog = self.bot.get_cog('TeamClaimSystem')
    if team_claim_cog:
        winning_team_claimer = team_claim_cog.get_team_claim(winning_team)
        if winning_team_claimer:
            await points_cog.add_user_points(int(winning_team_claimer['user_id']), 2)
```

### Hardcoded Poll System
For the Washington/Tennessee poll that was causing issues, a hardcoded system was implemented:

```python
@commands.Cog.listener()
async def on_interaction(self, interaction: discord.Interaction):
    """Handle specific hardcoded poll interactions"""
    if not interaction.type == discord.InteractionType.component:
        return
    
    custom_id = interaction.data.get('custom_id', '')
    
    # Hardcoded fix for Washington/Tennessee poll
    if (custom_id in ['vote_recreated_1759543801_WAS', 'vote_recreated_1759543801_TEN', 
                      'show_results_recreated_1759543801', 
                      'declare_winner_recreated_1759543801_WAS', 
                      'declare_winner_recreated_1759543801_TEN'] and 
        interaction.message.id == 1423854647738761246):
        
        if custom_id == 'vote_recreated_1759543801_WAS':
            # Record actual vote
            user_id = interaction.user.id
            self.hardcoded_votes["TEN"].discard(user_id)  # Remove from other team
            if user_id in self.hardcoded_votes["WAS"]:
                await interaction.response.send_message("✅ You already voted for Washington Commanders!", ephemeral=True)
            else:
                self.hardcoded_votes["WAS"].add(user_id)
                await interaction.response.send_message("✅ Vote recorded for Washington Commanders!", ephemeral=True)
```

## Supabase Integration

### Points System Integration
```python
# In points_system_supabase.py
async def add_user_points(self, user_id: int, points: int, reason: str = "GOTW vote"):
    """Add points to a user's total"""
    try:
        # Insert or update user
        result = await self.supabase.table('users').upsert({
            'user_id': user_id,
            'total_points': points
        }).execute()
        
        # Log to points history
        await self.supabase.table('points_history').insert({
            'user_id': user_id,
            'points_change': points,
            'reason': reason,
            'source': 'gotw'
        }).execute()
        
    except Exception as e:
        logger.error(f"Error adding points to user {user_id}: {e}")
```

### Team Claim Integration
```python
# In team_claim_system.py
async def claim_team(self, interaction: discord.Interaction, team_abbreviation: str):
    """Claim a team for a user"""
    try:
        # Check if team is already claimed
        existing_claim = await self.supabase.table('team_claims').select('*').eq('team_abbreviation', team_abbreviation).execute()
        
        if existing_claim.data:
            await interaction.followup.send(f"❌ {team_abbreviation} is already claimed by {existing_claim.data[0]['display_name']}", ephemeral=True)
            return
        
        # Create new claim
        await self.supabase.table('team_claims').insert({
            'user_id': interaction.user.id,
            'team_abbreviation': team_abbreviation,
            'display_name': interaction.user.display_name,
            'username': interaction.user.name
        }).execute()
        
        await interaction.followup.send(f"✅ You have claimed {team_abbreviation}!", ephemeral=True)
        
    except Exception as e:
        logger.error(f"Error claiming team: {e}")
        await interaction.followup.send("❌ Error claiming team. Please try again.", ephemeral=True)
```

## Data Storage

### JSON Files
- `data/gotw.json` - Stores active GOTW polls and votes
- `data/nfl_teams.json` - NFL team data with emojis and metadata

### JSON Structure
```json
{
  "active_gotws": {
    "user_id_timestamp": {
      "team1": {"name": "Washington Commanders", "abbreviation": "WAS"},
      "team2": {"name": "Tennessee Titans", "abbreviation": "TEN"},
      "message_id": 1234567890123456789,
      "created_by": 123456789,
      "created_at": "2025-10-04T12:00:00Z",
      "is_locked": false,
      "winner_declared": false
    }
  },
  "votes": {
    "user_id_timestamp": {
      "WAS": ["user1", "user2", "user3"],
      "TEN": ["user4", "user5"]
    }
  }
}
```

## Error Handling

### Common Issues and Solutions

#### 1. Interaction Timeout (404 Not Found)
**Problem**: Discord interactions expire after 3 seconds
**Solution**: Use `interaction.followup.send()` for delayed responses

#### 2. Cog Loading Failures
**Problem**: Syntax errors prevent cogs from loading
**Solution**: Always validate syntax before committing:
```bash
python3 -c "import ast; ast.parse(open('filename.py').read())"
```

#### 3. Message ID Storage Issues
**Problem**: `WebhookMessage` objects don't expose `id` attribute
**Solution**: Fetch message from channel history after sending

#### 4. Rate Limiting
**Problem**: Too many message edits (5 per 5 seconds per server)
**Solution**: Implement retry logic with exponential backoff

## Configuration

### Environment Variables
```bash
DISCORD_TOKEN=your_discord_bot_token
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_anon_key
```

### Bot Permissions
- Send Messages
- Use Slash Commands
- Embed Links
- Attach Files
- Read Message History
- Manage Messages (for editing)

## Deployment

### Render.com Configuration
- **Build Command**: `pip install -r madden_discord_bot/requirements.txt`
- **Start Command**: `cd madden_discord_bot && python3 bot.py`
- **Python Version**: 3.13.4
- **Auto Deploy**: From `clean-main` branch

### Local Development
```bash
cd madden_discord_bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 bot.py
```

## Testing

### Manual Testing Checklist
- [ ] Create new GOTW poll
- [ ] Vote on poll
- [ ] Change vote
- [ ] Show results
- [ ] Declare winner
- [ ] Award points
- [ ] Team claim integration
- [ ] Lock poll
- [ ] Undo winner declaration

### Debug Commands
```python
# Check active polls
logger.info(f"Active GOTWs: {list(self.active_gotws.keys())}")

# Check vote counts
logger.info(f"Votes: {self.votes}")

# Check team claims
team_claims = await self.supabase.table('team_claims').select('*').execute()
logger.info(f"Team claims: {team_claims.data}")
```

## Future Improvements

1. **Database Migration**: Move from JSON to full Supabase storage
2. **Real-time Updates**: Use Supabase real-time subscriptions
3. **Poll Scheduling**: Allow scheduled poll creation
4. **Advanced Analytics**: Vote trends and statistics
5. **Multi-language Support**: Internationalization
6. **Mobile Optimization**: Better mobile Discord experience

## Troubleshooting

### Bot Not Responding
1. Check if cogs are loading: Look for "✅ GOTWSystem cog initialized"
2. Check syntax: Run syntax validation
3. Check permissions: Verify bot has required Discord permissions
4. Check logs: Look for error messages in console

### Votes Not Recording
1. Check database connection
2. Verify user permissions
3. Check for rate limiting
4. Validate JSON file permissions

### Points Not Awarding
1. Check Supabase connection
2. Verify points system cog is loaded
3. Check user exists in database
4. Validate point calculation logic

## Support

For issues or questions:
1. Check the logs for error messages
2. Verify all environment variables are set
3. Test with a simple poll first
4. Check Discord bot permissions
5. Validate database schema matches expectations
