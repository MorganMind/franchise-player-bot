# 🏈 Game of the Week (GOTW) System

The Game of the Week system allows users to create head-to-head matchups between NFL teams and vote on who they think will win. The system displays team helmets in a beautiful card format and tracks real-time voting results.

## Features

- **Team Selection**: Choose from all 32 NFL teams using names or abbreviations
- **Head-to-Head Cards**: Beautiful display with team helmets and information
- **Interactive Voting**: Click buttons to vote directly on the card
- **Real-time Updates**: Vote counts update automatically
- **Detailed Results**: See who voted for each team and percentages
- **Team Information**: Conference and division details for each team

## Commands

### `/gotw create <team1> <team2>`
Creates a new Game of the Week matchup between two teams.

**Examples:**
- `/gotw create DAL PHI` - Cowboys vs Eagles
- `/gotw create dallas eagles` - Cowboys vs Eagles (using team names)
- `/gotw create COWBOYS EAGLES` - Cowboys vs Eagles (using partial names)

### `/gotw vote`
Shows the current Game of the Week voting card with interactive buttons.

### `/gotw results`
Displays detailed voting results including:
- List of users who voted for each team
- Vote percentages
- Total vote count

### `/gotw list`
Shows all available NFL teams organized by conference (AFC/NFC).

### `/gotw clear`
Clears the current Game of the Week and all votes.

## How to Vote

1. Use `/gotw vote` to see the current matchup
2. Click the button for your chosen team
3. Your vote will be recorded and the card will update automatically
4. You can change your vote by clicking the other team's button

## Team Abbreviations

All NFL teams are supported with their official abbreviations:

**AFC Teams:**
- BAL (Ravens), BUF (Bills), CIN (Bengals), CLE (Browns)
- DEN (Broncos), HOU (Texans), IND (Colts), JAX (Jaguars)
- KC (Chiefs), LV (Raiders), LAC (Chargers), MIA (Dolphins)
- NE (Patriots), NYJ (Jets), PIT (Steelers), TEN (Titans)

**NFC Teams:**
- ARI (Cardinals), ATL (Falcons), CAR (Panthers), CHI (Bears)
- DAL (Cowboys), DET (Lions), GB (Packers), LAR (Rams)
- MIN (Vikings), NO (Saints), NYG (Giants), PHI (Eagles)
- SF (49ers), SEA (Seahawks), TB (Buccaneers), WAS (Commanders)

## Data Storage

The system stores data in JSON files:
- `data/gotw.json` - Current GOTW and votes
- `data/nfl_teams.json` - Team information and helmet URLs

## Future Enhancements

- Team records display
- Historical GOTW results
- Weekly automatic GOTW creation
- Integration with live game data
- Custom GOTW themes and colors

## Technical Details

- Uses Discord.py slash commands
- Interactive buttons for voting
- Real-time message updates
- Persistent data storage
- Error handling and validation
- Team name fuzzy matching

## Setup

1. The GOTW system is automatically loaded when the bot starts
2. Team data is created on first run
3. No additional configuration required
4. Works with existing bot permissions

## Permissions Required

- Send Messages
- Use Slash Commands
- Add Reactions (for voting buttons)
- Embed Links (for team helmet images)










