import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import logging
import asyncio
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class VoteButton(discord.ui.Button):
    def __init__(self, team, cog, gotw_id, disabled=False, guild=None):
        # Get custom emoji with fallback
        emoji = cog.get_team_emoji(guild, team['abbreviation']) if guild else team.get('emoji', '🏈')
        
        super().__init__(
            style=discord.ButtonStyle.primary,
            label=f"Vote {team['name']}",
            custom_id=f"vote_{gotw_id}_{team['abbreviation']}",
            emoji=emoji,
            disabled=disabled
        )
        self.team = team
        self.cog = cog
        self.gotw_id = gotw_id
    
    async def callback(self, interaction: discord.Interaction):
        logger.info(f"🔍 VoteButton callback: team={self.team['abbreviation']}, gotw_id={self.gotw_id}")
        await self.cog.handle_vote(interaction, self.team['abbreviation'], self.gotw_id)

class LockButton(discord.ui.Button):
    def __init__(self, cog, gotw_id):
        super().__init__(
            style=discord.ButtonStyle.danger,
            label="Lock Poll",
            custom_id=f"lock_poll_{gotw_id}",
            emoji="🔒"
        )
        self.cog = cog
        self.gotw_id = gotw_id
    
    async def callback(self, interaction: discord.Interaction):
        await self.cog.handle_lock_poll(interaction, self.gotw_id)

class ResultsButton(discord.ui.Button):
    def __init__(self, cog, gotw_id):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label="Show Results",
            custom_id=f"show_results_{gotw_id}",
            emoji="📊"
        )
        self.cog = cog
        self.gotw_id = gotw_id
    
    async def callback(self, interaction: discord.Interaction):
        # Check if user is administrator
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Only administrators can view results.", ephemeral=True)
            return
        await self.cog.handle_show_results(interaction, self.gotw_id)

class DeclareWinnerButton(discord.ui.Button):
    def __init__(self, cog, team_abbreviation, team_name, team_emoji, guild=None):
        # Get custom emoji with fallback
        emoji = cog.get_team_emoji(guild, team_abbreviation) if guild else team_emoji
        
        super().__init__(
            style=discord.ButtonStyle.success,
            label=f"Winner: {team_name}",
            custom_id=f"winner_{team_abbreviation}",
            emoji=emoji
        )
        self.cog = cog
        self.team_abbreviation = team_abbreviation
        self.team_name = team_name
    
    async def callback(self, interaction: discord.Interaction):
        await self.cog.handle_declare_winner(interaction, self.team_abbreviation, self.team_name)

class TeamSelect(discord.ui.Select):
    def __init__(self, cog, team_number, guild, teams_subset, conference_name):
        self.cog = cog
        self.team_number = team_number
        self.guild = guild
        self.conference_name = conference_name
        
        # Create options from teams subset
        options = []
        for team in teams_subset:
            emoji = cog.get_team_emoji(guild, team['abbreviation'])
            options.append(discord.SelectOption(
                label=team['name'],
                description=f"{team['conference']} {team['division']}",
                value=team['abbreviation'],
                emoji=emoji
            ))
        
        super().__init__(
            placeholder=f"Select Team {team_number} ({conference_name})",
            min_values=1,
            max_values=1,
            options=options
        )
    
    def update_placeholder(self, selected_team_abbrev=None):
        """Update the placeholder to show selected team"""
        if selected_team_abbrev:
            team = self.cog.teams.get(selected_team_abbrev.upper())
            if team:
                # Use just the team name without emoji to avoid Discord's raw format issue
                self.placeholder = f"✓ {team['name']}"
            else:
                self.placeholder = f"Team {self.team_number} Selected"
        else:
            self.placeholder = f"Select Team {self.team_number} ({self.conference_name})"
    
    async def callback(self, interaction: discord.Interaction):
        # Update the view's selected teams
        view = self.view
        selected_team = self.values[0]
        
        if self.team_number == 1:
            view.team1_selected = selected_team
            # Update all Team 1 selectors
            for item in view.children:
                if isinstance(item, TeamSelect) and item.team_number == 1:
                    if item == self:
                        item.update_placeholder(selected_team)
                    else:
                        item.update_placeholder(None)  # Reset other Team 1 selectors
        else:
            view.team2_selected = selected_team
            # Update all Team 2 selectors
            for item in view.children:
                if isinstance(item, TeamSelect) and item.team_number == 2:
                    if item == self:
                        item.update_placeholder(selected_team)
                    else:
                        item.update_placeholder(None)  # Reset other Team 2 selectors
        
        # Update the create button state
        view.update_create_button()
        
        # Update the message
        await interaction.response.edit_message(view=view)

class CreateGOTWButton(discord.ui.Button):
    def __init__(self, cog):
        super().__init__(
            style=discord.ButtonStyle.success,
            label="Create GOTW",
            custom_id="create_gotw",
            emoji="⭐",
            disabled=True
        )
        self.cog = cog
    
    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if not view.team1_selected or not view.team2_selected:
            await interaction.response.send_message("❌ Please select both teams first!", ephemeral=True)
            return
        
        if view.team1_selected == view.team2_selected:
            await interaction.response.send_message("❌ Cannot create GOTW with the same team!", ephemeral=True)
            return
        
        # Create the GOTW
        await self.cog.create_gotw(interaction, view.team1_selected, view.team2_selected)
        
        # Dismiss the setup message after successful creation
        try:
            await interaction.delete_original_response()
        except:
            pass  # Ignore if message is already deleted

class DismissButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label="Dismiss",
            custom_id="dismiss_setup",
            emoji="❌"
        )
    
    async def callback(self, interaction: discord.Interaction):
        try:
            await interaction.delete_original_response()
        except:
            await interaction.response.send_message("Setup dismissed.", ephemeral=True)

class GOTWSetupView(discord.ui.View):
    def __init__(self, cog, guild):
        super().__init__(timeout=300)  # 5 minute timeout
        self.cog = cog
        self.guild = guild
        self.team1_selected = None
        self.team2_selected = None
        
        # Split teams by conference to respect Discord's 25-option limit
        teams_list = list(cog.teams.values())
        
        # AFC teams (16 teams)
        afc_teams = [team for team in teams_list if team['conference'] == 'AFC']
        afc_teams.sort(key=lambda x: x['name'])  # Sort alphabetically within conference
        
        # NFC teams (16 teams)
        nfc_teams = [team for team in teams_list if team['conference'] == 'NFC']
        nfc_teams.sort(key=lambda x: x['name'])  # Sort alphabetically within conference
        
        # Create team selectors for Team 1 (AFC and NFC)
        self.team1_afc_select = TeamSelect(cog, 1, guild, afc_teams, "AFC")
        self.team1_nfc_select = TeamSelect(cog, 1, guild, nfc_teams, "NFC")
        
        # Create team selectors for Team 2 (AFC and NFC)
        self.team2_afc_select = TeamSelect(cog, 2, guild, afc_teams, "AFC")
        self.team2_nfc_select = TeamSelect(cog, 2, guild, nfc_teams, "NFC")
        
        # Add team selectors
        self.add_item(self.team1_afc_select)
        self.add_item(self.team1_nfc_select)
        self.add_item(self.team2_afc_select)
        self.add_item(self.team2_nfc_select)
        
        # Add create button
        self.create_button = CreateGOTWButton(cog)
        self.add_item(self.create_button)
        
        # Add dismiss button
        self.add_item(DismissButton())
    
    def update_create_button(self):
        """Update the create button state based on selections"""
        if self.team1_selected and self.team2_selected and self.team1_selected != self.team2_selected:
            self.create_button.disabled = False
            self.create_button.style = discord.ButtonStyle.success
        else:
            self.create_button.disabled = True
            self.create_button.style = discord.ButtonStyle.secondary
    
    async def on_timeout(self):
        """Handle timeout by disabling all buttons"""
        for item in self.children:
            item.disabled = True
        
        # Try to edit the message to show it's expired
        try:
            embed = discord.Embed(
                title="⏰ GOTW Setup Expired",
                description="This setup session has timed out. Use `/gotw` to start a new one.",
                color=0xff6b6b
            )
            await self.message.edit(embed=embed, view=self)
        except:
            pass  # Ignore if message is already deleted

class GOTWView(discord.ui.View):
    def __init__(self, cog, team1, team2, gotw_id, is_locked=False, guild=None):
        super().__init__(timeout=None)  # No timeout
        self.cog = cog
        self.team1 = team1
        self.team2 = team2
        self.gotw_id = gotw_id
        self.is_locked = is_locked
        self.guild = guild
        
        # Create buttons for voting
        self.add_item(VoteButton(team1, cog, gotw_id, disabled=is_locked, guild=guild))
        self.add_item(VoteButton(team2, cog, gotw_id, disabled=is_locked, guild=guild))
        
        # Add results button (always available)
        self.add_item(ResultsButton(cog, gotw_id))
        
        # Add lock button (only if not locked and user has permission)
        if not is_locked:
            self.add_item(LockButton(cog, gotw_id))

class GOTWSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.gotw_file = "data/gotw.json"
        self.teams_file = "data/nfl_teams.json"
        self.active_gotws = {}  # Dictionary of message_id -> gotw_data
        self.votes = {}  # Dictionary of message_id -> votes
        self.load_gotw_data()
        self.load_teams()
        logger.info("✅ GOTWSystem cog initialized")
    
    
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
                {"name": "Chicago Bears", "abbreviation": "CHI", "conference": "NFC", "division": "North", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/5/5c/Chicago_Bears_logo.svg", "emoji": "🐻"},
                {"name": "Cincinnati Bengals", "abbreviation": "CIN", "conference": "AFC", "division": "North", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/8/81/Cincinnati_Bengals_logo.svg", "emoji": "🐯"},
                {"name": "Cleveland Browns", "abbreviation": "CLE", "conference": "AFC", "division": "North", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/d/d9/Cleveland_Browns_logo.svg", "emoji": "🐕"},
                {"name": "Dallas Cowboys", "abbreviation": "DAL", "conference": "NFC", "division": "East", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/4/47/Dallas_Cowboys_logo.svg", "emoji": "⭐"},
                {"name": "Denver Broncos", "abbreviation": "DEN", "conference": "AFC", "division": "West", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/4/44/Denver_Broncos_logo.svg", "emoji": "🐎"},
                {"name": "Detroit Lions", "abbreviation": "DET", "conference": "NFC", "division": "North", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/7/71/Detroit_Lions_logo.svg", "emoji": "🦁"},
                {"name": "Green Bay Packers", "abbreviation": "GB", "conference": "NFC", "division": "North", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/5/50/Green_Bay_Packers_logo.svg", "emoji": "🧀"},
                {"name": "Houston Texans", "abbreviation": "HOU", "conference": "AFC", "division": "South", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/f/f2/Houston_Texans_logo.svg", "emoji": "🤠"},
                {"name": "Indianapolis Colts", "abbreviation": "IND", "conference": "AFC", "division": "South", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/0/00/Indianapolis_Colts_logo.svg", "emoji": "🐎"},
                {"name": "Jacksonville Jaguars", "abbreviation": "JAX", "conference": "AFC", "division": "South", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/7/74/Jacksonville_Jaguars_logo.svg", "emoji": "🐆"},
                {"name": "Kansas City Chiefs", "abbreviation": "KC", "conference": "AFC", "division": "West", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/e/e1/Kansas_City_Chiefs_logo.svg", "emoji": "🏹"},
                {"name": "Las Vegas Raiders", "abbreviation": "LV", "conference": "AFC", "division": "West", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/4/48/Las_Vegas_Raiders_logo.svg", "emoji": "🏴‍☠️"},
                {"name": "Los Angeles Chargers", "abbreviation": "LAC", "conference": "AFC", "division": "West", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/7/72/NFL_Chargers_logo.svg", "emoji": "⚡"},
                {"name": "Los Angeles Rams", "abbreviation": "LAR", "conference": "NFC", "division": "West", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/8/81/Los_Angeles_Rams_logo.svg", "emoji": "🐏"},
                {"name": "Miami Dolphins", "abbreviation": "MIA", "conference": "AFC", "division": "East", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/3/37/Miami_Dolphins_logo.svg", "emoji": "🐬"},
                {"name": "Minnesota Vikings", "abbreviation": "MIN", "conference": "NFC", "division": "North", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/4/48/Minnesota_Vikings_logo.svg", "emoji": "🛡️"},
                {"name": "New England Patriots", "abbreviation": "NE", "conference": "AFC", "division": "East", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/b/b9/New_England_Patriots_logo.svg", "emoji": "🇺🇸"},
                {"name": "New Orleans Saints", "abbreviation": "NO", "conference": "NFC", "division": "South", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/5/50/New_Orleans_Saints_logo.svg", "emoji": "⛪"},
                {"name": "New York Giants", "abbreviation": "NYG", "conference": "NFC", "division": "East", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/6/60/New_York_Giants_logo.svg", "emoji": "👹"},
                {"name": "New York Jets", "abbreviation": "NYJ", "conference": "AFC", "division": "East", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/3/3a/New_York_Jets_logo.svg", "emoji": "✈️"},
                {"name": "Philadelphia Eagles", "abbreviation": "PHI", "conference": "NFC", "division": "East", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/8/8e/Philadelphia_Eagles_logo.svg", "emoji": "🦅"},
                {"name": "Pittsburgh Steelers", "abbreviation": "PIT", "conference": "AFC", "division": "North", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/d/de/Pittsburgh_Steelers_logo.svg", "emoji": "⚫"},
                {"name": "San Francisco 49ers", "abbreviation": "SF", "conference": "NFC", "division": "West", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/3/3a/San_Francisco_49ers_logo.svg", "emoji": "💎"},
                {"name": "Seattle Seahawks", "abbreviation": "SEA", "conference": "NFC", "division": "West", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/2/24/Seattle_Seahawks_logo.svg", "emoji": "🦅"},
                {"name": "Tampa Bay Buccaneers", "abbreviation": "TB", "conference": "NFC", "division": "South", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/a/a2/Tampa_Bay_Buccaneers_logo.svg", "emoji": "☠️"},
                {"name": "Tennessee Titans", "abbreviation": "TEN", "conference": "AFC", "division": "South", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/c/c1/Tennessee_Titans_logo.svg", "emoji": "⚔️"},
                {"name": "Washington Commanders", "abbreviation": "WAS", "conference": "NFC", "division": "East", "helmet_url": "https://upload.wikimedia.org/wikipedia/en/8/81/Washington_Commanders_logo.svg", "emoji": "⚔️"}
            ]
        }
        
        # Save teams data
        os.makedirs(os.path.dirname(self.teams_file), exist_ok=True)
        with open(self.teams_file, 'w') as f:
            json.dump(teams_data, f, indent=2)
        
        self.teams = {team['abbreviation']: team for team in teams_data['teams']}
                logger.info(f"Created default teams data with {len(self.teams)} teams")
        except Exception as e:
            logger.error(f"Error loading teams data: {e}")
            self.teams = {}
    
    def load_gotw_data(self):
        """Load GOTW data from JSON file"""
        try:
            os.makedirs(os.path.dirname(self.gotw_file), exist_ok=True)
            
            if os.path.exists(self.gotw_file):
                with open(self.gotw_file, 'r') as f:
                    data = json.load(f)
                    # Handle both old and new data formats
                    if 'active_gotws' in data:
                        self.active_gotws = data.get('active_gotws', {})
                    self.votes = data.get('votes', {})
                    else:
                        # Migrate from old format
                        self.active_gotws = {}
                        self.votes = {}
                        if data.get('current_gotw'):
                            # Convert old single GOTW to new format (if we had a message_id)
                            logger.info("Migrating from old GOTW format")
            else:
                self.save_gotw_data()
        except Exception as e:
            logger.error(f"Error loading GOTW data: {e}")
            self.active_gotws = {}
            self.votes = {}
    
    def save_gotw_data(self):
        """Save GOTW data to JSON file"""
        try:
            data = {
                'active_gotws': self.active_gotws,
                'votes': self.votes
            }
            with open(self.gotw_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving GOTW data: {e}")
    
    def get_team_by_name(self, team_name):
        """Get team data by name or abbreviation"""
        team_name = team_name.upper()
        
        # Try exact abbreviation match first
        if team_name in self.teams:
            return self.teams[team_name]
        
        # Try partial name match
        for team in self.teams.values():
            if team_name in team['name'].upper() or team['name'].upper().startswith(team_name):
                return team
        
        return None
    
    def get_team_emoji(self, guild, team_abbreviation):
        """Get custom emoji for team with fallback to Unicode emoji"""
        try:
            # Try to find custom emoji by team abbreviation
            custom_emoji = discord.utils.get(guild.emojis, name=team_abbreviation.lower())
            if custom_emoji:
                return str(custom_emoji)
            
            # Fallback to Unicode emoji from team data
            team = self.teams.get(team_abbreviation.upper())
            if team:
                return team.get('emoji', '🏈')
            
            return '🏈'  # Default fallback
        except Exception as e:
            logger.error(f"Error getting team emoji for {team_abbreviation}: {e}")
            return '🏈'

    
    @app_commands.command(name="gotw", description="Create a Game of the Week matchup")
    @app_commands.describe(
        team1="First team for the matchup",
        team2="Second team for the matchup"
    )
    async def gotw(self, interaction: discord.Interaction, team1: str = None, team2: str = None):
        """Main GOTW command - can use parameters or interactive setup"""
        if team1 and team2:
            # Direct creation with parameters
            await self.create_gotw(interaction, team1, team2)
        else:
            # Interactive setup
            await self.setup_gotw_creation(interaction)
    
    @gotw.autocomplete('team1')
    @gotw.autocomplete('team2')
    async def team_autocomplete(self, interaction: discord.Interaction, current: str):
        """Autocomplete for team selection"""
        teams = []
        for team in self.teams.values():
            if current.lower() in team['name'].lower() or current.lower() in team['abbreviation'].lower():
                # Use default emoji instead of custom emoji for autocomplete
                default_emoji = team.get('emoji', '🏈')
                teams.append(app_commands.Choice(
                    name=f"{default_emoji} {team['name']} ({team['abbreviation']})",
                    value=team['abbreviation']
                ))
        
        # Sort by name and return first 25
        teams.sort(key=lambda x: x.name)
        return teams[:25]
    
    async def setup_gotw_creation(self, interaction: discord.Interaction):
        """Setup interactive GOTW creation with team selection"""
        embed = discord.Embed(
            title="⭐ Create Game of the Week",
            description="Use the `/gotw` command with team parameters for easy team selection!",
            color=0x00ff00
        )
        
        embed.add_field(
            name="How to Use:",
            value="Type `/gotw team1:` and start typing a team name - autocomplete will show all 32 teams!\n\n**Example:**\n`/gotw team1: Patriots team2: Bills`\n\n**Benefits:**\n• All 32 teams accessible\n• Smart autocomplete filtering\n• No complex dropdowns\n• Fast team selection",
            inline=False
        )
        
        embed.add_field(
            name="Alternative:",
            value="You can also use `/gotw` without parameters for the interactive setup if you prefer dropdowns.",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    async def create_gotw(self, interaction: discord.Interaction, team1_abbrev: str, team2_abbrev: str):
        """Create a new Game of the Week"""
        if not team1_abbrev or not team2_abbrev:
            await interaction.response.send_message("❌ Please select both teams", ephemeral=True)
            return
        
        # Get teams by abbreviation (from autocomplete)
        team1 = self.teams.get(team1_abbrev.upper())
        team2 = self.teams.get(team2_abbrev.upper())
        
        if not team1:
            await interaction.response.send_message(f"❌ Team '{team1_abbrev}' not found", ephemeral=True)
            return
        
        if not team2:
            await interaction.response.send_message(f"❌ Team '{team2_abbrev}' not found", ephemeral=True)
            return
        
        if team1['abbreviation'] == team2['abbreviation']:
            await interaction.response.send_message("❌ Cannot create GOTW with the same team", ephemeral=True)
            return
        
        # Create new GOTW with unique ID
        gotw_id = f"{interaction.user.id}_{int(datetime.now().timestamp())}"
        
        gotw_data = {
            'id': gotw_id,
            'team1': team1,
            'team2': team2,
            'created_by': interaction.user.id,
            'created_at': datetime.now().isoformat(),
            'is_locked': False,
            'locked_by': None,
            'locked_at': None,
            'winner_declared': False,
            'winner_team': None,
            'winner_declared_by': None,
            'winner_declared_at': None
        }
        
        # Store the GOTW data
        self.active_gotws[gotw_id] = gotw_data
        self.votes[gotw_id] = {}
        
        self.save_gotw_data()
        
        # Show the GOTW card
        await self.show_gotw_card(interaction, team1, team2, gotw_id)
    
    async def show_gotw_card(self, interaction: discord.Interaction, team1=None, team2=None, gotw_id=None):
        """Display a GOTW card"""
        logger.info(f"🔍 show_gotw_card called: gotw_id={gotw_id}, team1={team1['abbreviation'] if team1 else None}, team2={team2['abbreviation'] if team2 else None}")
        
        if not team1 or not team2:
            await interaction.response.send_message("❌ No teams provided for GOTW", ephemeral=True)
            return
        
        # Create embed
        embed = discord.Embed(
            title="⭐ GAME OF THE WEEK ⭐",
            description="**Head to Head Matchup**",
            color=0x00ff00
        )
        
        # Get custom emojis with fallbacks
        team1_emoji = self.get_team_emoji(interaction.guild, team1['abbreviation'])
        team2_emoji = self.get_team_emoji(interaction.guild, team2['abbreviation'])
        
        # Add team information
        embed.add_field(
            name=f"{team1_emoji} {team1['name']} ({team1['abbreviation']})",
            value=f"Conference: {team1['conference']}\nDivision: {team1['division']}",
            inline=True
        )
        
        embed.add_field(
            name="VS",
            value="",
            inline=True
        )
        
        embed.add_field(
            name=f"{team2_emoji} {team2['name']} ({team2['abbreviation']})",
            value=f"Conference: {team2['conference']}\nDivision: {team2['division']}",
            inline=True
        )
        
        # Add team helmet images
        embed.set_thumbnail(url=team1['helmet_url'])
        embed.set_image(url=team2['helmet_url'])
        
        # Add voting information
        poll_votes = self.votes.get(gotw_id, {})
        team1_votes = len([v for v in poll_votes.values() if v == team1['abbreviation']])
        team2_votes = len([v for v in poll_votes.values() if v == team2['abbreviation']])
        
        embed.add_field(
            name="📊 Current Votes",
            value=f"{team1_emoji} {team1['name']}: **{team1_votes}**\n{team2_emoji} {team2['name']}: **{team2_votes}**",
            inline=False
        )
        
        embed.set_footer(text="Click the buttons below to vote!")
        
        # Create view with voting buttons
        is_locked = self.active_gotws[gotw_id].get('is_locked', False)
        view = GOTWView(self, team1, team2, gotw_id, is_locked=is_locked, guild=interaction.guild)
        
        # Get league role for mention
        league_role = discord.utils.get(interaction.guild.roles, name="League")
        league_mention = league_role.mention if league_role else "@League"
        
        await interaction.response.send_message(content=league_mention, embed=embed, view=view)
        
        # Get the message ID from the interaction response
        # For response messages, we need to fetch the message after sending
        try:
            logger.info(f"🔍 Attempting to store message_id for GOTW {gotw_id}")
            # Wait a moment for the message to be sent
            await asyncio.sleep(0.1)
            # Get the message from the channel
            message_found = False
            async for message in interaction.channel.history(limit=5):
                logger.info(f"🔍 Checking message: {message.id}, author={message.author}, embeds={len(message.embeds) if message.embeds else 0}")
                if message.author == self.bot.user and message.embeds and "GAME OF THE WEEK" in message.embeds[0].title:
                    self.active_gotws[gotw_id]['message_id'] = message.id
                    self.save_gotw_data()
                    logger.info(f"✅ Stored message_id {message.id} for GOTW {gotw_id}")
                    message_found = True
                    break
            
            if not message_found:
                logger.warning(f"⚠️ Could not find GOTW message to store message_id for {gotw_id}")
                
        except Exception as e:
            logger.error(f"❌ Failed to store message_id for GOTW {gotw_id}: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
    
    async def show_vote_card(self, interaction: discord.Interaction):
        """Show the current GOTW voting card"""
        await self.show_gotw_card(interaction)
    
    async def handle_show_results(self, interaction: discord.Interaction, gotw_id: str):
        """Handle showing results from the button"""
        if gotw_id not in self.active_gotws:
            await interaction.response.send_message("❌ This poll no longer exists", ephemeral=True)
            return
        
        gotw_data = self.active_gotws[gotw_id]
        team1 = gotw_data['team1']
        team2 = gotw_data['team2']
        
        # Get custom emojis with fallbacks
        team1_emoji = self.get_team_emoji(interaction.guild, team1['abbreviation'])
        team2_emoji = self.get_team_emoji(interaction.guild, team2['abbreviation'])
        
        poll_votes = self.votes.get(gotw_id, {})
        team1_votes = [user_id for user_id, vote in poll_votes.items() if vote == team1['abbreviation']]
        team2_votes = [user_id for user_id, vote in poll_votes.items() if vote == team2['abbreviation']]
        
        embed = discord.Embed(
            title="📊 GOTW Voting Results",
            description="Detailed breakdown of votes",
            color=0x00ff00
        )
        
        embed.add_field(
            name=f"{team1_emoji} {team1['name']} ({len(team1_votes)} votes)",
            value="\n".join([f"<@{user_id}>" for user_id in team1_votes]) if team1_votes else "No votes yet",
            inline=True
        )
        
        embed.add_field(
            name=f"{team2_emoji} {team2['name']} ({len(team2_votes)} votes)",
            value="\n".join([f"<@{user_id}>" for user_id in team2_votes]) if team2_votes else "No votes yet",
            inline=True
        )
        
        total_votes = len(self.votes)
        if total_votes > 0:
            team1_percentage = (len(team1_votes) / total_votes) * 100
            team2_percentage = (len(team2_votes) / total_votes) * 100
            
            embed.add_field(
                name="📈 Percentages",
                value=f"{team1_emoji} {team1['name']}: {team1_percentage:.1f}%\n{team2_emoji} {team2['name']}: {team2_percentage:.1f}%",
                inline=False
            )
        
        # Check if winner has already been declared
        winner_declared = self.current_gotw.get('winner_declared', False)
        if winner_declared:
            winner_team = self.current_gotw.get('winner_team')
            winner_name = team1['name'] if winner_team == team1['abbreviation'] else team2['name']
            embed.add_field(
                name="🏆 Winner Declared",
                value=f"**{winner_name}** won! Points have been awarded to voters.",
                inline=False
            )
            embed.color = 0xffd700  # Gold color for winner declared
        else:
            # Add winner declaration buttons for commish
            view = discord.ui.View(timeout=None)
            view.add_item(DeclareWinnerButton(self, team1['abbreviation'], team1['name'], team1_emoji, guild=interaction.guild))
            view.add_item(DeclareWinnerButton(self, team2['abbreviation'], team2['name'], team2_emoji, guild=interaction.guild))
            
            await interaction.response.send_message(embed=embed, view=view)
            return
        
        await interaction.response.send_message(embed=embed)
    
    async def list_teams(self, interaction: discord.Interaction):
        """List all available NFL teams"""
        embed = discord.Embed(
            title="🏈 Available NFL Teams",
            description="Use team names or abbreviations to create GOTW",
            color=0x00ff00
        )
        
        # Group teams by conference
        afc_teams = [team for team in self.teams.values() if team['conference'] == 'AFC']
        nfc_teams = [team for team in self.teams.values() if team['conference'] == 'NFC']
        
        afc_text = "\n".join([f"{team['emoji']} {team['name']} ({team['abbreviation']})" for team in afc_teams])
        nfc_text = "\n".join([f"{team['emoji']} {team['name']} ({team['abbreviation']})" for team in nfc_teams])
        
        embed.add_field(name="🏈 AFC Teams", value=afc_text, inline=True)
        embed.add_field(name="🏈 NFC Teams", value=nfc_text, inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    async def clear_gotw(self, interaction: discord.Interaction):
        """Clear the current GOTW"""
        if not self.current_gotw:
            await interaction.response.send_message("❌ No Game of the Week currently set", ephemeral=True)
            return
        
        self.current_gotw = None
        self.votes = {}
        self.save_gotw_data()
        
        await interaction.response.send_message("✅ Game of the Week cleared!", ephemeral=True)
    
    async def setup_gotw_channel(self, interaction: discord.Interaction):
        """Setup a dedicated GOTW channel"""
        try:
            # Create the GOTW channel
            channel = await interaction.guild.create_text_channel(
                name="game-of-the-week",
                topic="🏈 Game of the Week voting and discussions",
                reason=f"GOTW channel created by {interaction.user.display_name}"
            )
            
            # Create an embed to welcome users
            embed = discord.Embed(
                title="🏈 Welcome to Game of the Week!",
                description="This channel is dedicated to Game of the Week matchups and voting.",
                color=0x00ff00
            )
            
            embed.add_field(
                name="📋 Available Commands",
                value="• `/gotw create <team1> <team2>` - Create a new matchup\n"
                      "• `/gotw vote` - Show current voting card\n"
                      "• `/gotw list` - List all NFL teams\n"
                      "• `/gotw clear` - Clear current GOTW\n"
                      "• **📊 Show Results** - Use the button on the GOTW card",
                inline=False
            )
            
            embed.add_field(
                name="🎯 Quick Start",
                value="Try: `/gotw create` and select teams from the dropdown menus!",
                inline=False
            )
            
            await channel.send(embed=embed)
            
            await interaction.response.send_message(
                f"✅ Created GOTW channel: {channel.mention}\n"
                f"Head over there to start creating matchups!",
                ephemeral=True
            )
            
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to create channels", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error creating channel: {str(e)}", ephemeral=True)
    

    
    def has_admin_permission(self, interaction):
        """Check if user has commish role or administrator permissions"""
        # Check if user has administrator permission
        if interaction.user.guild_permissions.administrator:
            return True
        
        # Check if user has commish role
        commish_role = discord.utils.get(interaction.guild.roles, name="commish")
        if commish_role and commish_role in interaction.user.roles:
            return True
        
        return False
    
    async def handle_vote(self, interaction: discord.Interaction, team_abbreviation: str, gotw_id: str):
        """Handle a user's vote"""
        logger.info(f"🔍 handle_vote called: gotw_id={gotw_id}, team={team_abbreviation}, user={interaction.user.id}")
        logger.info(f"🔍 Active GOTWs: {list(self.active_gotws.keys())}")
        
        if gotw_id not in self.active_gotws:
            logger.error(f"❌ GOTW {gotw_id} not found in active_gotws")
            await interaction.response.send_message("❌ This poll no longer exists", ephemeral=True)
            return
        
        gotw_data = self.active_gotws[gotw_id]
        logger.info(f"🔍 Found GOTW data: {gotw_data.get('id', 'no_id')}")
        
        # Check if poll is locked
        if gotw_data.get('is_locked', False):
            await interaction.response.send_message("🔒 **Poll is locked!** No more votes can be cast.", ephemeral=True)
            return
        
        user_id = str(interaction.user.id)
        
        # Check if user already voted in this specific poll
        if gotw_id not in self.votes:
            self.votes[gotw_id] = {}
            
        if user_id in self.votes[gotw_id]:
            old_vote = self.votes[gotw_id][user_id]
            if old_vote == team_abbreviation:
                await interaction.response.send_message("❌ You already voted for this team!", ephemeral=True)
                return
            else:
                # Update existing vote
                self.votes[gotw_id][user_id] = team_abbreviation
                logger.info(f"Updated vote for user {user_id} in poll {gotw_id}: {old_vote} -> {team_abbreviation}")
                await interaction.response.send_message(f"✅ Vote changed to {team_abbreviation}!", ephemeral=True)
        else:
            # New vote
            self.votes[gotw_id][user_id] = team_abbreviation
            logger.info(f"New vote recorded for user {user_id} in poll {gotw_id}: {team_abbreviation}")
            await interaction.response.send_message(f"✅ Vote recorded for {team_abbreviation}!", ephemeral=True)
        
        logger.info(f"Votes before save: {self.votes}")
        self.save_gotw_data()
        logger.info(f"Votes after save: {self.votes}")
        
        # Update the original message with new vote counts
        try:
            # Find the specific GOTW message using stored message ID
            message_id = gotw_data.get('message_id')
            logger.info(f"🔍 Attempting to update message: message_id={message_id}")
            
            if message_id:
                logger.info(f"🔍 Fetching message by ID: {message_id}")
                message = await interaction.channel.fetch_message(message_id)
                logger.info(f"🔍 Found message, updating vote display")
                await self.update_vote_message(message, gotw_id)
                logger.info(f"✅ Successfully updated vote message")
            else:
                logger.warning(f"⚠️ No message_id stored for GOTW {gotw_id}, using fallback search")
                # Fallback: find by searching (less reliable)
                async for message in interaction.channel.history(limit=50):
                    if (message.embeds and 
                        len(message.embeds) > 0 and 
                        message.embeds[0].title and 
                        "GAME OF THE WEEK" in message.embeds[0].title and
                        message.author == self.bot.user):
                        logger.info(f"🔍 Found GOTW message by search, updating")
                        await self.update_vote_message(message, gotw_id)
                        break
        except Exception as e:
            logger.error(f"❌ Failed to update vote message: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            # Don't fail the vote if message update fails

    async def handle_lock_poll(self, interaction: discord.Interaction, gotw_id: str):
        """Handle locking the poll"""
        if not self.has_admin_permission(interaction):
            await interaction.response.send_message("❌ You need administrator permissions or the 'commish' role to lock the poll.", ephemeral=True)
            return
        
        if gotw_id not in self.active_gotws:
            await interaction.response.send_message("❌ This poll no longer exists", ephemeral=True)
            return
        
        # Lock the poll
        self.active_gotws[gotw_id]['is_locked'] = True
        self.active_gotws[gotw_id]['locked_by'] = interaction.user.id
        self.active_gotws[gotw_id]['locked_at'] = datetime.now().isoformat()
        
        self.save_gotw_data()
        
        # Update the message with locked status
        await self.update_vote_message(interaction.message, gotw_id, is_locked=True)
        
        await interaction.response.send_message("🔒 **Poll locked!** No more votes can be cast.", ephemeral=True)

    async def handle_declare_winner(self, interaction: discord.Interaction, team_abbreviation: str, team_name: str):
        """Handle declaring a winner and awarding points"""
        if not self.has_admin_permission(interaction):
            await interaction.response.send_message("❌ You need administrator permissions or the 'commish' role to declare a winner.", ephemeral=True)
            return
        
        if not self.current_gotw:
            await interaction.response.send_message("❌ No Game of the Week currently set", ephemeral=True)
            return
        
        # Check if winner already declared
        if self.current_gotw.get('winner_declared', False):
            await interaction.response.send_message("❌ Winner has already been declared for this poll!", ephemeral=True)
            return
        
        # Get voters for the winning team
        winning_voters = [user_id for user_id, vote in self.votes.items() if vote == team_abbreviation]
        
        # Award points to winning voters
        points_awarded = 0
        if winning_voters:
            # Import points system to award points
            points_cog = self.bot.get_cog('PointsSystemSupabase')
            if points_cog:
                for user_id in winning_voters:
                    try:
                        await points_cog.add_user_points(int(user_id), 1)
                        points_awarded += 1
                        logger.info(f"Awarded 1 point to user {user_id} for winning GOTW vote")
                    except Exception as e:
                        logger.error(f"Error awarding points to user {user_id}: {e}")
            else:
                logger.error("PointsSystemSupabase cog not found - cannot award points")
        
        # Mark winner as declared
        self.current_gotw['winner_declared'] = True
        self.current_gotw['winner_team'] = team_abbreviation
        self.current_gotw['winner_declared_by'] = interaction.user.id
        self.current_gotw['winner_declared_at'] = datetime.now().isoformat()
        
        self.save_gotw_data()
        
        # Create success embed
        embed = discord.Embed(
            title="🏆 Winner Declared!",
            description=f"**{team_name}** has been declared the winner!",
            color=0xffd700
        )
        
        embed.add_field(
            name="📊 Points Awarded",
            value=f"**{points_awarded}** voters received **+1 point** each",
            inline=False
        )
        
        if winning_voters:
            embed.add_field(
                name="🎉 Winning Voters",
                value="\n".join([f"<@{user_id}>" for user_id in winning_voters]),
                inline=False
            )
        else:
            embed.add_field(
                name="😔 No Winning Voters",
                value="No one voted for the winning team",
                inline=False
            )
        
        embed.set_footer(text=f"Declared by {interaction.user.display_name}")
        
        # Get league role for mention
        league_role = discord.utils.get(interaction.guild.roles, name="League")
        league_mention = league_role.mention if league_role else "@League"
        
        await interaction.response.send_message(content=league_mention, embed=embed)

    async def update_vote_message(self, message, gotw_id, is_locked=None):
        """Update the vote message with current counts and lock status"""
        try:
            if gotw_id not in self.active_gotws:
                logger.warning(f"No GOTW found with ID {gotw_id} when trying to update vote message")
                return
            
            gotw_data = self.active_gotws[gotw_id]
            
            # Update the embed
            embed = message.embeds[0]
            
            team1 = gotw_data['team1']
            team2 = gotw_data['team2']
            
            poll_votes = self.votes.get(gotw_id, {})
            team1_votes = len([v for v in poll_votes.values() if v == team1['abbreviation']])
            team2_votes = len([v for v in poll_votes.values() if v == team2['abbreviation']])
            
            logger.info(f"Updating vote message: {team1['name']}={team1_votes}, {team2['name']}={team2_votes}")
            logger.info(f"Total votes in self.votes: {len(self.votes)}")
            logger.info(f"Votes dict: {self.votes}")
            
            # Get custom emojis with fallbacks
            team1_emoji = self.get_team_emoji(message.guild, team1['abbreviation'])
            team2_emoji = self.get_team_emoji(message.guild, team2['abbreviation'])
            
            # Update the votes field
            for field in embed.fields:
                if field.name == "📊 Current Votes":
                    field.value = f"{team1_emoji} {team1['name']}: **{team1_votes}**\n{team2_emoji} {team2['name']}: **{team2_votes}**"
                    logger.info(f"Updated field value: {field.value}")
                    break
            
            # Update footer based on lock status
            if is_locked is None:
                is_locked = gotw_data.get('is_locked', False)
            
            if is_locked:
                embed.set_footer(text="🔒 Poll Locked - No more votes can be cast")
            else:
                embed.set_footer(text="Click the buttons below to vote!")
            
            # Create new view with updated lock status
            view = GOTWView(self, team1, team2, gotw_id, is_locked=is_locked, guild=message.guild)
            
            # Get league role for mention
            league_role = discord.utils.get(message.guild.roles, name="League")
            league_mention = league_role.mention if league_role else "@League"
            
            await message.edit(content=league_mention, embed=embed, view=view)
            logger.info("Successfully updated vote message")
            
        except Exception as e:
            logger.error(f"Error updating vote message: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")

async def setup(bot):
    await bot.add_cog(GOTWSystem(bot))
