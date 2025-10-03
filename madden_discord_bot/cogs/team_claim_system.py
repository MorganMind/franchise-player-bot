import discord
from discord.ext import commands
from discord import app_commands
import logging
import json
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class TeamSelect(discord.ui.Select):
    def __init__(self, cog, guild):
        self.cog = cog
        self.guild = guild
        
        # Create options from teams
        options = []
        for team in cog.teams.values():
            emoji = cog.get_team_emoji(guild, team['abbreviation'])
            options.append(discord.SelectOption(
                label=team['name'],
                description=f"{team['conference']} {team['division']}",
                value=team['abbreviation'],
                emoji=emoji
            ))
        
        super().__init__(
            placeholder="Select your team",
            min_values=1,
            max_values=1,
            options=options[:25]  # Discord limit
        )
    
    async def callback(self, interaction: discord.Interaction):
        selected_abbrev = self.values[0]
        selected_team_data = self.cog.teams.get(selected_abbrev.upper())
        
        # Update the placeholder to show the selected team
        self.placeholder = f"✓ {selected_team_data['name']}"
        
        # Update the parent view's selected team
        view: TeamClaimView = self.view
        view.selected_team = selected_abbrev
        view.update_claim_button()
        
        # Update the message to reflect the new selection
        await interaction.response.edit_message(view=view)

class ClaimTeamButton(discord.ui.Button):
    def __init__(self, cog):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label="Claim Team",
            custom_id="claim_team_button",
            emoji="🏈",
            disabled=True
        )
        self.cog = cog
    
    async def callback(self, interaction: discord.Interaction):
        view: TeamClaimView = self.view
        if view.selected_team:
            await self.cog.claim_team(interaction, view.selected_team)
            # Dismiss the setup message after successful claim
            try:
                await interaction.delete_original_response()
            except:
                pass  # Ignore if message is already deleted
        else:
            await interaction.response.send_message("❌ Please select a team first!", ephemeral=True)

class DismissButton(discord.ui.Button):
    def __init__(self):
        super().__init__(
            style=discord.ButtonStyle.secondary,
            label="Dismiss",
            custom_id="dismiss_claim",
            emoji="❌"
        )
    
    async def callback(self, interaction: discord.Interaction):
        try:
            await interaction.delete_original_response()
        except:
            await interaction.response.send_message("Setup dismissed.", ephemeral=True)

class TeamClaimView(discord.ui.View):
    def __init__(self, cog, guild):
        super().__init__(timeout=300)  # 5 minute timeout
        self.cog = cog
        self.guild = guild
        self.selected_team = None
        
        # Add team selector
        team_select = TeamSelect(cog, guild)
        self.add_item(team_select)
        
        # Add claim button
        self.claim_button = ClaimTeamButton(cog)
        self.add_item(self.claim_button)
        
        # Add dismiss button
        self.add_item(DismissButton())
    
    def update_claim_button(self):
        """Update the claim button state based on selection"""
        if self.selected_team:
            self.claim_button.disabled = False
            self.claim_button.style = discord.ButtonStyle.success
        else:
            self.claim_button.disabled = True
            self.claim_button.style = discord.ButtonStyle.secondary
    
    async def on_timeout(self):
        """Handle timeout by disabling all buttons"""
        for item in self.children:
            item.disabled = True
        
        # Try to edit the message to show it's expired
        try:
            embed = discord.Embed(
                title="⏰ Team Claim Setup Expired",
                description="This setup session has timed out. Use `/claimteam` to start a new one.",
                color=0xff6b6b
            )
            await self.message.edit(embed=embed, view=self)
        except:
            pass  # Ignore if message is already deleted

class TeamClaimSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.teams_file = "data/nfl_teams.json"
        self.teams = {}
        self.load_teams_data()
        
        # Import Supabase client
        try:
            from config.supabase_config import supabase
            self.supabase = supabase
        except ImportError:
            logger.error("Supabase config not found")
            self.supabase = None

    def load_teams_data(self):
        """Load NFL teams data"""
        if os.path.exists(self.teams_file):
            with open(self.teams_file, 'r') as f:
                teams_data = json.load(f)
                # Handle both direct list and wrapped in "teams" object
                if isinstance(teams_data, dict) and 'teams' in teams_data:
                    teams_list = teams_data['teams']
                elif isinstance(teams_data, list):
                    teams_list = teams_data
                else:
                    logger.error(f"Unexpected teams data format: {type(teams_data)}")
                    teams_list = []
                
                self.teams = {team['abbreviation'].upper(): team for team in teams_list}
            logger.info(f"Loaded {len(self.teams)} NFL teams.")
        else:
            logger.error(f"Teams data file not found: {self.teams_file}")
            self.teams = {}

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

    @app_commands.command(name="claimteam", description="Claim your favorite NFL team")
    async def claim_team_command(self, interaction: discord.Interaction):
        """Main team claim command"""
        await self.setup_team_claim(interaction)

    async def setup_team_claim(self, interaction: discord.Interaction):
        """Setup interactive team claim with team selection"""
        # Check if user already has a team claimed
        current_team = await self.get_user_team(interaction.user.id)
        
        embed = discord.Embed(
            title="🏈 Claim Your Team",
            description="Select your current NFL team to claim it as yours!",
            color=0x00ff00
        )
        
        if current_team:
            team_data = self.teams.get(current_team.upper())
            if team_data:
                emoji = self.get_team_emoji(interaction.guild, current_team)
                embed.add_field(
                    name="Current Team",
                    value=f"{emoji} **{team_data['name']}** ({current_team})",
                    inline=False
                )
                embed.add_field(
                    name="Instructions",
                    value="Select a different team below to change your claim, or select the same team to confirm.",
                    inline=False
                )
            else:
                embed.add_field(
                    name="Instructions",
                    value="Select your team from the dropdown below.",
                    inline=False
                )
        else:
            embed.add_field(
                name="Instructions",
                value="Select your team from the dropdown below to claim it!",
                inline=False
            )
        
        embed.add_field(
            name="Benefits",
            value="• Get +2 points when your team wins GOTW\n• Team integration in streams and upgrades",
            inline=False
        )
        
        view = TeamClaimView(self, interaction.guild)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    async def claim_team(self, interaction: discord.Interaction, team_abbrev: str):
        """Process team claim"""
        if not self.supabase:
            await interaction.response.send_message("❌ Database connection error. Please try again later.", ephemeral=True)
            return
        
        team_data = self.teams.get(team_abbrev.upper())
        if not team_data:
            await interaction.response.send_message("❌ Invalid team selected.", ephemeral=True)
            return
        
        # Check if team is already claimed by someone else
        existing_claim = await self.get_team_claim(team_abbrev)
        if existing_claim and existing_claim != str(interaction.user.id):
            existing_user = self.bot.get_user(int(existing_claim))
            user_name = existing_user.display_name if existing_user else "Unknown User"
            await interaction.response.send_message(
                f"❌ **{team_data['name']}** is already claimed by **{user_name}**!\n"
                f"Each team can only be claimed by one person.",
                ephemeral=True
            )
            return
        
        # Check if user is claiming the same team they already have
        current_team = await self.get_user_team(interaction.user.id)
        if current_team == team_abbrev.upper():
            await interaction.response.send_message(
                f"✅ You already have **{team_data['name']}** claimed!",
                ephemeral=True
            )
            return
        
        # Save the team claim
        success = await self.save_team_claim(interaction.user.id, team_abbrev, interaction.user.display_name, interaction.user.name)
        
        if success:
            emoji = self.get_team_emoji(interaction.guild, team_abbrev)
            
            embed = discord.Embed(
                title="🏈 Team Claimed!",
                description=f"**{interaction.user.display_name}** has claimed **{team_data['name']}**!",
                color=0x00ff00
            )
            
            embed.add_field(
                name="Team Details",
                value=f"{emoji} **{team_data['name']}** ({team_abbrev})\n"
                      f"Conference: {team_data['conference']}\n"
                      f"Division: {team_data['division']}",
                inline=False
            )
            
            embed.add_field(
                name="Benefits",
                value="• Your team affiliation will show in GOTW polls\n• You'll get +2 points when your team wins GOTW\n• Team integration in future features",
                inline=False
            )
            
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            embed.set_footer(text=f"Claimed by {interaction.user.display_name}")
            
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("❌ Failed to claim team. Please try again.", ephemeral=True)

    async def get_user_team(self, user_id):
        """Get the team claimed by a user"""
        try:
            result = self.supabase.table("team_claims").select("team_abbreviation").eq("user_id", str(user_id)).execute()
            if result.data and len(result.data) > 0:
                return result.data[0]["team_abbreviation"]
            return None
        except Exception as e:
            logger.error(f"Error getting user team for {user_id}: {e}")
            return None

    async def get_team_claim(self, team_abbrev):
        """Get the user who claimed a team"""
        try:
            result = self.supabase.table("team_claims").select("user_id").eq("team_abbreviation", team_abbrev.upper()).execute()
            if result.data and len(result.data) > 0:
                return result.data[0]["user_id"]
            return None
        except Exception as e:
            logger.error(f"Error getting team claim for {team_abbrev}: {e}")
            return None

    async def save_team_claim(self, user_id, team_abbrev, display_name, username):
        """Save or update a team claim"""
        try:
            # First, remove any existing claim by this user
            self.supabase.table("team_claims").delete().eq("user_id", str(user_id)).execute()
            
            # Then, remove any existing claim for this team
            self.supabase.table("team_claims").delete().eq("team_abbreviation", team_abbrev.upper()).execute()
            
            # Insert the new claim
            claim_data = {
                "user_id": str(user_id),
                "team_abbreviation": team_abbrev.upper(),
                "display_name": display_name,
                "username": username,
                "claimed_at": datetime.now().isoformat()
            }
            
            result = self.supabase.table("team_claims").insert(claim_data).execute()
            logger.info(f"User {user_id} claimed team {team_abbrev}")
            return True
        except Exception as e:
            logger.error(f"Error saving team claim: {e}")
            return False

    async def get_team_claimed_user(self, team_abbrev):
        """Get the user who claimed a specific team"""
        try:
            result = self.supabase.table("team_claims").select("user_id, display_name").eq("team_abbreviation", team_abbrev.upper()).execute()
            if result.data and len(result.data) > 0:
                return result.data[0]
            return None
        except Exception as e:
            logger.error(f"Error getting team claimed user for {team_abbrev}: {e}")
            return None

async def setup(bot):
    await bot.add_cog(TeamClaimSystem(bot))
