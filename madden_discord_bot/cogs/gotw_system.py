import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class VoteButton(discord.ui.Button):
    def __init__(self, team, cog):
        super().__init__(
            style=discord.ButtonStyle.primary,
            label=f"Vote {team['name']}",
            custom_id=f"vote_{team['abbreviation']}",
            emoji=team.get('emoji', '🏈')
        )
        self.team = team
        self.cog = cog
    
    async def callback(self, interaction: discord.Interaction):
        await self.cog.handle_vote(interaction, self.team['abbreviation'])

class GOTWView(discord.ui.View):
    def __init__(self, cog, team1, team2):
        super().__init__(timeout=None)  # No timeout
        self.cog = cog
        self.team1 = team1
        self.team2 = team2
        
        # Create buttons for voting
        self.add_item(VoteButton(team1, cog))
        self.add_item(VoteButton(team2, cog))

class GOTWSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.gotw_file = "data/gotw.json"
        self.teams_file = "data/nfl_teams.json"
        self.current_gotw = None
        self.votes = {}
        self.load_gotw_data()
        self.load_teams()
        logger.info("✅ GOTWSystem cog initialized")
    
    def load_teams(self):
        """Load NFL teams data"""
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
    
    def load_gotw_data(self):
        """Load GOTW data from JSON file"""
        try:
            os.makedirs(os.path.dirname(self.gotw_file), exist_ok=True)
            
            if os.path.exists(self.gotw_file):
                with open(self.gotw_file, 'r') as f:
                    data = json.load(f)
                    self.current_gotw = data.get('current_gotw')
                    self.votes = data.get('votes', {})
            else:
                self.save_gotw_data()
        except Exception as e:
            logger.error(f"Error loading GOTW data: {e}")
            self.current_gotw = None
            self.votes = {}
    
    def save_gotw_data(self):
        """Save GOTW data to JSON file"""
        try:
            data = {
                'current_gotw': self.current_gotw,
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
    
    @app_commands.command(name="gotw", description="Game of the Week commands")
    @app_commands.describe(
        action="Action to perform: create, vote, results, list, clear",
        team1="First team (name or abbreviation)",
        team2="Second team (name or abbreviation)"
    )
    async def gotw(self, interaction: discord.Interaction, action: str, team1: str = None, team2: str = None):
        """Main GOTW command"""
        if action.lower() == "create":
            await self.create_gotw(interaction, team1, team2)
        elif action.lower() == "vote":
            await self.show_vote_card(interaction)
        elif action.lower() == "results":
            await self.show_results(interaction)
        elif action.lower() == "list":
            await self.list_teams(interaction)
        elif action.lower() == "clear":
            await self.clear_gotw(interaction)
        else:
            await interaction.response.send_message("❌ Invalid action. Use: create, vote, results, list, or clear", ephemeral=True)
    
    async def create_gotw(self, interaction: discord.Interaction, team1_name: str, team2_name: str):
        """Create a new Game of the Week"""
        if not team1_name or not team2_name:
            await interaction.response.send_message("❌ Please provide both team names", ephemeral=True)
            return
        
        team1 = self.get_team_by_name(team1_name)
        team2 = self.get_team_by_name(team2_name)
        
        if not team1:
            await interaction.response.send_message(f"❌ Team '{team1_name}' not found", ephemeral=True)
            return
        
        if not team2:
            await interaction.response.send_message(f"❌ Team '{team2_name}' not found", ephemeral=True)
            return
        
        if team1['abbreviation'] == team2['abbreviation']:
            await interaction.response.send_message("❌ Cannot create GOTW with the same team", ephemeral=True)
            return
        
        # Create new GOTW
        self.current_gotw = {
            'team1': team1,
            'team2': team2,
            'created_by': interaction.user.id,
            'created_at': datetime.now().isoformat(),
            'votes': {}
        }
        
        # Clear previous votes
        self.votes = {}
        
        self.save_gotw_data()
        
        # Show the GOTW card
        await self.show_gotw_card(interaction)
    
    async def show_gotw_card(self, interaction: discord.Interaction):
        """Display the current GOTW card"""
        if not self.current_gotw:
            await interaction.response.send_message("❌ No Game of the Week currently set", ephemeral=True)
            return
        
        team1 = self.current_gotw['team1']
        team2 = self.current_gotw['team2']
        
        # Create embed
        embed = discord.Embed(
            title="🏈 GAME OF THE WEEK 🏈",
            description="**Head to Head Matchup**",
            color=0x00ff00
        )
        
        # Add team information
        embed.add_field(
            name=f"{team1['emoji']} {team1['name']} ({team1['abbreviation']})",
            value=f"Conference: {team1['conference']}\nDivision: {team1['division']}",
            inline=True
        )
        
        embed.add_field(
            name="VS",
            value="",
            inline=True
        )
        
        embed.add_field(
            name=f"{team2['emoji']} {team2['name']} ({team2['abbreviation']})",
            value=f"Conference: {team2['conference']}\nDivision: {team2['division']}",
            inline=True
        )
        
        # Add team helmet images
        embed.set_thumbnail(url=team1['helmet_url'])
        embed.set_image(url=team2['helmet_url'])
        
        # Add voting information
        team1_votes = len([v for v in self.votes.values() if v == team1['abbreviation']])
        team2_votes = len([v for v in self.votes.values() if v == team2['abbreviation']])
        
        embed.add_field(
            name="📊 Current Votes",
            value=f"{team1['emoji']} {team1['name']}: **{team1_votes}**\n{team2['emoji']} {team2['name']}: **{team2_votes}**",
            inline=False
        )
        
        embed.set_footer(text="Click the buttons below to vote!")
        
        # Create view with voting buttons
        view = GOTWView(self, team1, team2)
        
        await interaction.response.send_message(embed=embed, view=view)
    
    async def show_vote_card(self, interaction: discord.Interaction):
        """Show the current GOTW voting card"""
        await self.show_gotw_card(interaction)
    
    async def show_results(self, interaction: discord.Interaction):
        """Show detailed voting results"""
        if not self.current_gotw:
            await interaction.response.send_message("❌ No Game of the Week currently set", ephemeral=True)
            return
        
        team1 = self.current_gotw['team1']
        team2 = self.current_gotw['team2']
        
        team1_votes = [user_id for user_id, vote in self.votes.items() if vote == team1['abbreviation']]
        team2_votes = [user_id for user_id, vote in self.votes.items() if vote == team2['abbreviation']]
        
        embed = discord.Embed(
            title="📊 GOTW Voting Results",
            description="Detailed breakdown of votes",
            color=0x00ff00
        )
        
        embed.add_field(
            name=f"{team1['emoji']} {team1['name']} ({len(team1_votes)} votes)",
            value="\n".join([f"<@{user_id}>" for user_id in team1_votes]) if team1_votes else "No votes yet",
            inline=True
        )
        
        embed.add_field(
            name=f"{team2['emoji']} {team2['name']} ({len(team2_votes)} votes)",
            value="\n".join([f"<@{user_id}>" for user_id in team2_votes]) if team2_votes else "No votes yet",
            inline=True
        )
        
        total_votes = len(self.votes)
        if total_votes > 0:
            team1_percentage = (len(team1_votes) / total_votes) * 100
            team2_percentage = (len(team2_votes) / total_votes) * 100
            
            embed.add_field(
                name="📈 Percentages",
                value=f"{team1['name']}: {team1_percentage:.1f}%\n{team2['name']}: {team2_percentage:.1f}%",
                inline=False
            )
        
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
                      "• `/gotw results` - Show detailed results\n"
                      "• `/gotw list` - List all NFL teams\n"
                      "• `/gotw clear` - Clear current GOTW",
                inline=False
            )
            
            embed.add_field(
                name="🎯 Quick Start",
                value="Try: `/gotw create DAL PHI` to create a Cowboys vs Eagles matchup!",
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
    

    
    async def handle_vote(self, interaction: discord.Interaction, team_abbreviation: str):
        """Handle a user's vote"""
        if not self.current_gotw:
            await interaction.response.send_message("❌ No Game of the Week currently set", ephemeral=True)
            return
        
        user_id = str(interaction.user.id)
        
        # Check if user already voted
        if user_id in self.votes:
            old_vote = self.votes[user_id]
            if old_vote == team_abbreviation:
                await interaction.response.send_message("❌ You already voted for this team!", ephemeral=True)
                return
            else:
                # Update existing vote
                self.votes[user_id] = team_abbreviation
                await interaction.response.send_message(f"✅ Vote changed to {team_abbreviation}!", ephemeral=True)
        else:
            # New vote
            self.votes[user_id] = team_abbreviation
            await interaction.response.send_message(f"✅ Vote recorded for {team_abbreviation}!", ephemeral=True)
        
        self.save_gotw_data()
        
        # Update the original message with new vote counts
        try:
            # Get the original message
            message = interaction.message
            
            # Update the embed
            embed = message.embeds[0]
            
            team1 = self.current_gotw['team1']
            team2 = self.current_gotw['team2']
            
            team1_votes = len([v for v in self.votes.values() if v == team1['abbreviation']])
            team2_votes = len([v for v in self.votes.values() if v == team2['abbreviation']])
            
            # Update the votes field
            for field in embed.fields:
                if field.name == "📊 Current Votes":
                    field.value = f"{team1['emoji']} {team1['name']}: **{team1_votes}**\n{team2['emoji']} {team2['name']}: **{team2_votes}**"
                    break
            
            await message.edit(embed=embed)
            
        except Exception as e:
            logger.error(f"Error updating vote message: {e}")

async def setup(bot):
    await bot.add_cog(GOTWSystem(bot))
