import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class GOTWSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.gotw_file = "data/gotw.json"
        self.teams_file = "data/nfl_teams.json"
        self.active_gotws = {}
        self.votes = {}
        
        # Load persisted data on initialization
        self.load_gotw_data()
        self.load_teams()
        
        logger.info(f"✅ GOTWSystem cog initialized with {len(self.active_gotws)} active polls")

    def load_gotw_data(self):
        """Load GOTW data from JSON file"""
        try:
            if os.path.exists(self.gotw_file):
                with open(self.gotw_file, 'r') as f:
                    data = json.load(f)
                    # Restore both active polls and votes
                    self.active_gotws = data.get('active_gotws', {})
                    self.votes = data.get('votes', {})
                    logger.info(f"Loaded {len(self.active_gotws)} polls from storage")
            else:
                # Create file with empty structure
                self.active_gotws = {}
                self.votes = {}
                self.save_gotw_data()
        except Exception as e:
            logger.error(f"Error loading GOTW data: {e}")
            self.active_gotws = {}
            self.votes = {}

    def save_gotw_data(self):
        """Save GOTW data to JSON file"""
        try:
            os.makedirs(os.path.dirname(self.gotw_file), exist_ok=True)
            with open(self.gotw_file, 'w') as f:
                json.dump({
                    'active_gotws': self.active_gotws,
                    'votes': self.votes
                }, f, indent=2)
            logger.debug("GOTW data saved")
        except Exception as e:
            logger.error(f"Error saving GOTW data: {e}")

    def load_teams(self):
        """Load NFL teams data"""
        try:
            if os.path.exists(self.teams_file):
                with open(self.teams_file, 'r') as f:
                    teams_data = json.load(f)
                    # Handle both direct list and nested "teams" object formats
                    if isinstance(teams_data, list):
                        teams_list = teams_data
                    elif isinstance(teams_data, dict) and 'teams' in teams_data:
                        teams_list = teams_data['teams']
                    else:
                        teams_list = []
                    
                    self.teams = {team['abbreviation']: team for team in teams_list}
                    logger.info(f"Loaded {len(self.teams)} teams from {self.teams_file}")
            else:
                # Create default teams data if file doesn't exist
                teams_data = {
                    "teams": [
                        {"name": "Arizona Cardinals", "abbreviation": "ARI", "conference": "NFC", "division": "West", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/7/72/Arizona_Cardinals_logo.svg", "emoji": "🃏"},
                        {"name": "Atlanta Falcons", "abbreviation": "ATL", "conference": "NFC", "division": "South", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/c/c5/Atlanta_Falcons_logo.svg", "emoji": "🦅"},
                        {"name": "Baltimore Ravens", "abbreviation": "BAL", "conference": "AFC", "division": "North", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/1/16/Baltimore_Ravens_logo.svg", "emoji": "🐦‍⬛"},
                        {"name": "Buffalo Bills", "abbreviation": "BUF", "conference": "AFC", "division": "East", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/7/72/Buffalo_Bills_logo.svg", "emoji": "🦬"},
                        {"name": "Carolina Panthers", "abbreviation": "CAR", "conference": "NFC", "division": "South", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/5/5c/Carolina_Panthers_logo.svg", "emoji": "🐆"},
                        {"name": "Chicago Bears", "abbreviation": "CHI", "conference": "NFC", "division": "North", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/4/44/Chicago_Bears_logo.svg", "emoji": "🐻"},
                        {"name": "Cincinnati Bengals", "abbreviation": "CIN", "conference": "AFC", "division": "North", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/8/81/Cincinnati_Bengals_logo.svg", "emoji": "🐅"},
                        {"name": "Cleveland Browns", "abbreviation": "CLE", "conference": "AFC", "division": "North", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/d/d9/Cleveland_Browns_logo.svg", "emoji": "🤎"},
                        {"name": "Dallas Cowboys", "abbreviation": "DAL", "conference": "NFC", "division": "East", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/5/50/Dallas_Cowboys_logo.svg", "emoji": "⭐"},
                        {"name": "Denver Broncos", "abbreviation": "DEN", "conference": "AFC", "division": "West", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/4/44/Denver_Broncos_logo.svg", "emoji": "🐴"},
                        {"name": "Detroit Lions", "abbreviation": "DET", "conference": "NFC", "division": "North", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/7/71/Detroit_Lions_logo.svg", "emoji": "🦁"},
                        {"name": "Green Bay Packers", "abbreviation": "GB", "conference": "NFC", "division": "North", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/5/50/Green_Bay_Packers_logo.svg", "emoji": "🧀"},
                        {"name": "Houston Texans", "abbreviation": "HOU", "conference": "AFC", "division": "South", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/2/28/Houston_Texans_logo.svg", "emoji": "🤠"},
                        {"name": "Indianapolis Colts", "abbreviation": "IND", "conference": "AFC", "division": "South", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/0/00/Indianapolis_Colts_logo.svg", "emoji": "🐎"},
                        {"name": "Jacksonville Jaguars", "abbreviation": "JAX", "conference": "AFC", "division": "South", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/7/74/Jacksonville_Jaguars_logo.svg", "emoji": "🐆"},
                        {"name": "Kansas City Chiefs", "abbreviation": "KC", "conference": "AFC", "division": "West", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/e/e1/Kansas_City_Chiefs_logo.svg", "emoji": "🏹"},
                        {"name": "Las Vegas Raiders", "abbreviation": "LV", "conference": "AFC", "division": "West", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/4/48/Las_Vegas_Raiders_logo.svg", "emoji": "⚔️"},
                        {"name": "Los Angeles Chargers", "abbreviation": "LAC", "conference": "AFC", "division": "West", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/7/79/Los_Angeles_Chargers_logo.svg", "emoji": "⚡"},
                        {"name": "Los Angeles Rams", "abbreviation": "LAR", "conference": "NFC", "division": "West", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/8/8a/Los_Angeles_Rams_logo.svg", "emoji": "🐏"},
                        {"name": "Miami Dolphins", "abbreviation": "MIA", "conference": "AFC", "division": "East", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/3/37/Miami_Dolphins_logo.svg", "emoji": "🐬"},
                        {"name": "Minnesota Vikings", "abbreviation": "MIN", "conference": "NFC", "division": "North", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/4/48/Minnesota_Vikings_logo.svg", "emoji": "⚔️"},
                        {"name": "New England Patriots", "abbreviation": "NE", "conference": "AFC", "division": "East", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/b/b9/New_England_Patriots_logo.svg", "emoji": "🇺🇸"},
                        {"name": "New Orleans Saints", "abbreviation": "NO", "conference": "NFC", "division": "South", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/5/5d/New_Orleans_Saints_logo.svg", "emoji": "⛪"},
                        {"name": "New York Giants", "abbreviation": "NYG", "conference": "NFC", "division": "East", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/6/62/New_York_Giants_logo.svg", "emoji": "👹"},
                        {"name": "New York Jets", "abbreviation": "NYJ", "conference": "AFC", "division": "East", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/6/6b/New_York_Jets_logo.svg", "emoji": "✈️"},
                        {"name": "Philadelphia Eagles", "abbreviation": "PHI", "conference": "NFC", "division": "East", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/8/8e/Philadelphia_Eagles_logo.svg", "emoji": "🦅"},
                        {"name": "Pittsburgh Steelers", "abbreviation": "PIT", "conference": "AFC", "division": "North", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/d/de/Pittsburgh_Steelers_logo.svg", "emoji": "⚫"},
                        {"name": "San Francisco 49ers", "abbreviation": "SF", "conference": "NFC", "division": "West", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/3/3a/San_Francisco_49ers_logo.svg", "emoji": "💍"},
                        {"name": "Seattle Seahawks", "abbreviation": "SEA", "conference": "NFC", "division": "West", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/2/2d/Seattle_Seahawks_logo.svg", "emoji": "🦅"},
                        {"name": "Tampa Bay Buccaneers", "abbreviation": "TB", "conference": "NFC", "division": "South", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/a/a2/Tampa_Bay_Buccaneers_logo.svg", "emoji": "🏴‍☠️"},
                        {"name": "Tennessee Titans", "abbreviation": "TEN", "conference": "AFC", "division": "South", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/c/c1/Tennessee_Titans_logo.svg", "emoji": "⚔️"},
                        {"name": "Washington Commanders", "abbreviation": "WAS", "conference": "NFC", "division": "East", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/f/f6/Washington_Commanders_logo.svg", "emoji": "🏈"}
                    ]
                }
                
                # Save teams data
                try:
                    os.makedirs(os.path.dirname(self.teams_file), exist_ok=True)
                    with open(self.teams_file, 'w') as f:
                        json.dump(teams_data, f, indent=2)
                    
                    self.teams = {team['abbreviation']: team for team in teams_data['teams']}
                    logger.info(f"Created default teams data with {len(self.teams)} teams")
                except Exception as e:
                    logger.error(f"Error creating default teams data: {e}")
                    self.teams = {}
        except Exception as e:
            logger.error(f"Error loading teams data: {e}")
            self.teams = {}

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        """Handle all button interactions, including those from before restart"""
        if not interaction.type == discord.InteractionType.component:
            return
        
        custom_id = interaction.data.get('custom_id', '')
        
        # Parse custom_id to determine action type and poll ID
        if custom_id.startswith('vote_'):
            # Format: vote_{gotw_id}_{team}
            parts = custom_id.split('_', 2)
            if len(parts) == 3:
                _, gotw_id, team = parts
                await self.handle_vote_with_recovery(interaction, team, gotw_id)
                
        elif custom_id.startswith('show_results_'):
            # Format: show_results_{gotw_id}
            gotw_id = custom_id.replace('show_results_', '')
            await self.handle_results_with_recovery(interaction, gotw_id)
            
        elif custom_id.startswith('lock_poll_'):
            # Format: lock_poll_{gotw_id}
            gotw_id = custom_id.replace('lock_poll_', '')
            await self.handle_lock_with_recovery(interaction, gotw_id)
            
        elif custom_id.startswith('declare_winner_'):
            # Format: declare_winner_{gotw_id}_{team}
            parts = custom_id.replace('declare_winner_', '').split('_', 1)
            if len(parts) == 2:
                gotw_id, team = parts
                await self.handle_declare_winner_with_recovery(interaction, gotw_id, team)

    async def handle_vote_with_recovery(self, interaction: discord.Interaction, team: str, gotw_id: str):
        """Handle vote with recovery for polls that may not be in memory"""
        # Try to get poll data from memory first
        gotw_data = self.active_gotws.get(gotw_id)
        
        # If not in memory, try to recover from the message itself
        if not gotw_data:
            gotw_data = await self.recover_poll_from_message(interaction.message, gotw_id)
            if gotw_data:
                # Add recovered poll back to active polls
                self.active_gotws[gotw_id] = gotw_data
                self.save_gotw_data()
        
        if not gotw_data:
            await interaction.response.send_message(
                "❌ This poll data couldn't be recovered. You may need to create a new poll.", 
                ephemeral=True
            )
            return
        
        # Check if poll is locked
        if gotw_data.get('is_locked', False):
            await interaction.response.send_message("❌ This poll is locked.", ephemeral=True)
            return
        
        # Record the vote
        user_id = str(interaction.user.id)
        
        # Initialize votes for this poll if needed
        if gotw_id not in self.votes:
            self.votes[gotw_id] = {}
        
        poll_votes = self.votes[gotw_id]
        
        # Remove user from other team's votes
        for t in poll_votes:
            if user_id in poll_votes[t]:
                poll_votes[t].remove(user_id)
        
        # Add user to selected team's votes
        if team not in poll_votes:
            poll_votes[team] = []
        if user_id not in poll_votes[team]:
            poll_votes[team].append(user_id)
        
        # Save votes
        self.votes[gotw_id] = poll_votes
        self.save_gotw_data()
        
        # Send confirmation
        team_name = gotw_data.get('team1', {}).get('name') if team == gotw_data.get('team1', {}).get('abbreviation') else gotw_data.get('team2', {}).get('name')
        await interaction.response.send_message(f"✅ Vote recorded for {team_name}!", ephemeral=True)
        
        # Update the message with new vote counts
        try:
            await self.update_vote_message(interaction.message, gotw_id)
        except Exception as e:
            logger.error(f"Error updating vote message: {e}")

    async def recover_poll_from_message(self, message: discord.Message, gotw_id: str):
        """Try to recover poll data from the message embed"""
        try:
            if not message.embeds:
                return None
            
            embed = message.embeds[0]
            
            # Parse teams from embed fields or title
            gotw_data = {
                'message_id': message.id,
                'created_at': message.created_at.isoformat(),
                'is_locked': False,
                'winner_declared': False
            }
            
            # Try to extract team info from embed
            # This assumes your embed has a consistent format
            if embed.fields:
                for field in embed.fields:
                    if "Washington" in field.name or "WAS" in field.name:
                        gotw_data['team1'] = {'name': 'Washington Commanders', 'abbreviation': 'WAS'}
                    elif "Tennessee" in field.name or "TEN" in field.name:
                        gotw_data['team2'] = {'name': 'Tennessee Titans', 'abbreviation': 'TEN'}
            
            # If we couldn't parse teams from fields, try the title
            if 'team1' not in gotw_data and embed.title:
                # Parse from title like "GOTW: WAS vs TEN"
                if " vs " in embed.title:
                    teams = embed.title.split(" vs ")
                    # You'd need to map these to full team names
                    # This is a simplified example
                    gotw_data['team1'] = {'abbreviation': 'WAS', 'name': 'Washington Commanders'}
                    gotw_data['team2'] = {'abbreviation': 'TEN', 'name': 'Tennessee Titans'}
            
            return gotw_data if 'team1' in gotw_data else None
            
        except Exception as e:
            logger.error(f"Error recovering poll from message: {e}")
            return None

    async def handle_results_with_recovery(self, interaction: discord.Interaction, gotw_id: str):
        """Handle showing results with recovery"""
        # Initialize votes if not present
        if gotw_id not in self.votes:
            self.votes[gotw_id] = {}
        
        poll_votes = self.votes.get(gotw_id, {})
        
        # Try to get poll data
        gotw_data = self.active_gotws.get(gotw_id)
        if not gotw_data:
            gotw_data = await self.recover_poll_from_message(interaction.message, gotw_id)
            if gotw_data:
                self.active_gotws[gotw_id] = gotw_data
                self.save_gotw_data()
        
        if not gotw_data:
            await interaction.response.send_message("❌ Unable to retrieve poll data.", ephemeral=True)
            return
        
        # Build results message
        team1 = gotw_data.get('team1', {})
        team2 = gotw_data.get('team2', {})
        
        team1_votes = len(poll_votes.get(team1.get('abbreviation', ''), []))
        team2_votes = len(poll_votes.get(team2.get('abbreviation', ''), []))
        total_votes = team1_votes + team2_votes
        
        results_embed = discord.Embed(
            title="📊 Current Results",
            color=discord.Color.blue()
        )
        
        results_embed.add_field(
            name=f"{team1.get('name', 'Team 1')}",
            value=f"{team1_votes} votes ({(team1_votes/total_votes*100 if total_votes > 0 else 0):.1f}%)",
            inline=True
        )
        
        results_embed.add_field(
            name=f"{team2.get('name', 'Team 2')}",
            value=f"{team2_votes} votes ({(team2_votes/total_votes*100 if total_votes > 0 else 0):.1f}%)",
            inline=True
        )
        
        await interaction.response.send_message(embed=results_embed, ephemeral=True)

    async def handle_lock_with_recovery(self, interaction: discord.Interaction, gotw_id: str):
        """Handle locking poll with recovery"""
        # Check permissions
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ You don't have permission to lock polls.", ephemeral=True)
            return
        
        # Get or recover poll data
        gotw_data = self.active_gotws.get(gotw_id)
        if not gotw_data:
            gotw_data = await self.recover_poll_from_message(interaction.message, gotw_id)
            if gotw_data:
                self.active_gotws[gotw_id] = gotw_data
        
        if not gotw_data:
            await interaction.response.send_message("❌ Unable to retrieve poll data.", ephemeral=True)
            return
        
        # Toggle lock status
        current_status = gotw_data.get('is_locked', False)
        gotw_data['is_locked'] = not current_status
        self.save_gotw_data()
        
        status_text = "locked" if gotw_data['is_locked'] else "unlocked"
        await interaction.response.send_message(f"✅ Poll has been {status_text}.", ephemeral=True)
        
        # Update the message to reflect lock status
        try:
            await self.update_vote_message(interaction.message, gotw_id)
        except Exception as e:
            logger.error(f"Error updating message: {e}")

    async def handle_declare_winner_with_recovery(self, interaction: discord.Interaction, gotw_id: str, team: str):
        """Handle declaring winner with recovery"""
        # Check permissions
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ You don't have permission to declare winners.", ephemeral=True)
            return
        
        # Get or recover poll data
        gotw_data = self.active_gotws.get(gotw_id)
        if not gotw_data:
            gotw_data = await self.recover_poll_from_message(interaction.message, gotw_id)
            if gotw_data:
                self.active_gotws[gotw_id] = gotw_data
        
        if not gotw_data:
            await interaction.response.send_message("❌ Unable to retrieve poll data.", ephemeral=True)
            return
        
        # Mark winner as declared
        gotw_data['winner_declared'] = True
        gotw_data['winner_team'] = team
        gotw_data['winner_declared_by'] = interaction.user.id
        gotw_data['winner_declared_at'] = datetime.now().isoformat()
        
        self.save_gotw_data()
        
        # Award points to voters and team claimers
        await self.award_points_for_winner(gotw_id, team)
        
        team_name = gotw_data.get('team1', {}).get('name') if team == gotw_data.get('team1', {}).get('abbreviation') else gotw_data.get('team2', {}).get('name')
        await interaction.response.send_message(f"🏆 {team_name} has been declared the winner!", ephemeral=True)

    async def award_points_for_winner(self, gotw_id: str, winning_team: str):
        """Award points to voters and team claimers"""
        try:
            points_cog = self.bot.get_cog('PointsSystemSupabase')
            if not points_cog:
                logger.error("PointsSystemSupabase cog not found")
                return
            
            # Award points to voters
            poll_votes = self.votes.get(gotw_id, {})
            winning_voters = poll_votes.get(winning_team, [])
            
            for user_id in winning_voters:
                try:
                    await points_cog.add_user_points(int(user_id), 1, "GOTW vote")
                except Exception as e:
                    logger.error(f"Error awarding points to user {user_id}: {e}")
            
            # Award points to team claimers
            team_claim_cog = self.bot.get_cog('TeamClaimSystem')
            if team_claim_cog:
                winning_team_claimer = team_claim_cog.get_team_claim(winning_team)
                if winning_team_claimer:
                    try:
                        await points_cog.add_user_points(int(winning_team_claimer['user_id']), 2, "GOTW team claim")
                    except Exception as e:
                        logger.error(f"Error awarding team claim points: {e}")
                        
        except Exception as e:
            logger.error(f"Error awarding points for winner: {e}")

    async def update_vote_message(self, message: discord.Message, gotw_id: str):
        """Update the vote message with current counts and lock status"""
        gotw_data = self.active_gotws.get(gotw_id, {})
        poll_votes = self.votes.get(gotw_id, {})
        
        # Get current embed
        if message.embeds:
            embed = message.embeds[0]
            
            # Update lock status in footer if locked
            if gotw_data.get('is_locked', False):
                embed.set_footer(text="🔒 This poll is locked")
            else:
                embed.set_footer(text="")
            
            # Update vote counts in fields
            # (You'd implement this based on your embed structure)
            
            await message.edit(embed=embed)

async def setup(bot):
    await bot.add_cog(GOTWSystem(bot))
