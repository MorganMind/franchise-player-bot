import discord
from discord.ext import commands
from discord import app_commands
import logging
import json
import os
from datetime import datetime

logger = logging.getLogger(__name__)

class TeamSelect(discord.ui.Select):
    def __init__(self, cog, guild, teams_subset, menu_number):
        self.cog = cog
        self.guild = guild
        self.menu_number = menu_number
        
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
            placeholder=f"Select your team ({menu_number})",
            min_values=1,
            max_values=1,
            options=options
        )
    
    async def callback(self, interaction: discord.Interaction):
        selected_abbrev = self.values[0]
        selected_team_data = self.cog.teams.get(selected_abbrev.upper())
        
        # Update the parent view's selected team
        view: TeamClaimView = self.view
        view.selected_team = selected_abbrev
        
        # Update both select menus to show the selected team
        for item in view.children:
            if isinstance(item, TeamSelect):
                if item == self:
                    # This is the menu that was selected
                    item.placeholder = f"✓ {selected_team_data['name']}"
                else:
                    # This is the other menu - reset its placeholder
                    item.placeholder = f"Select your team ({item.menu_number})"
        
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
            # Defer the response first to avoid conflicts
            await interaction.response.defer(ephemeral=True)
            # Process the claim
            await self.cog.claim_team(interaction, view.selected_team)
            # Delete the original ephemeral message
            try:
                await interaction.delete_original_response()
            except:
                pass  # Ignore if message is already deleted
        else:
            await interaction.response.send_message("❌ Please select a team first!", ephemeral=True)


class TeamClaimView(discord.ui.View):
    def __init__(self, cog, guild):
        super().__init__(timeout=300)  # 5 minute timeout
        self.cog = cog
        self.guild = guild
        self.selected_team = None
        
        # Split teams by conference to respect Discord's 25-option limit
        teams_list = list(cog.teams.values())
        
        # AFC teams (16 teams)
        afc_teams = [team for team in teams_list if team['conference'] == 'AFC']
        afc_teams.sort(key=lambda x: x['name'])  # Sort alphabetically within conference
        
        # NFC teams (16 teams)
        nfc_teams = [team for team in teams_list if team['conference'] == 'NFC']
        nfc_teams.sort(key=lambda x: x['name'])  # Sort alphabetically within conference
        
        # Add team selectors
        team_select1 = TeamSelect(cog, guild, afc_teams, "AFC")
        team_select2 = TeamSelect(cog, guild, nfc_teams, "NFC")
        self.add_item(team_select1)
        self.add_item(team_select2)
        
        # Add claim button
        self.claim_button = ClaimTeamButton(cog)
        self.add_item(self.claim_button)
    
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
            await interaction.followup.send("❌ Database connection error. Please try again later.", ephemeral=True)
            return
        
        team_data = self.teams.get(team_abbrev.upper())
        if not team_data:
            await interaction.followup.send("❌ Invalid team selected.", ephemeral=True)
            return
        
        # Check if team is already claimed by someone else
        existing_claim = await self.get_team_claim(team_abbrev)
        if existing_claim and existing_claim != str(interaction.user.id):
            existing_user = self.bot.get_user(int(existing_claim))
            user_name = existing_user.display_name if existing_user else "Unknown User"
            await interaction.followup.send(
                f"❌ **{team_data['name']}** is already claimed by **{user_name}**!\n"
                f"Each team can only be claimed by one person.",
                ephemeral=True
            )
            return
        
        # Check if user is claiming the same team they already have
        current_team = await self.get_user_team(interaction.user.id)
        if current_team == team_abbrev.upper():
            await interaction.followup.send(
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
                value="• You'll get +2 points when your team wins GOTW\n• Team integration in future features",
                inline=False
            )
            
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            embed.set_footer(text=f"Claimed by {interaction.user.display_name}")
            
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("❌ Failed to claim team. Please try again.", ephemeral=True)

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

    @app_commands.command(name="teamslist", description="List all NFL teams and their claimed status")
    async def teams_list(self, interaction: discord.Interaction):
        """List all teams and show who has claimed them"""
        if not self.supabase:
            await interaction.response.send_message("❌ Database connection error. Please try again later.", ephemeral=True)
            return
        
        try:
            # Get all team claims
            claims_result = self.supabase.table("team_claims").select("team_abbreviation, display_name").execute()
            claims_dict = {claim["team_abbreviation"]: claim["display_name"] for claim in claims_result.data}
            
            # Create embed
            embed = discord.Embed(
                title="🏈 NFL Teams Status",
                description="All 32 NFL teams and their claimed status",
                color=0x00ff00
            )
            
            # Group teams by conference
            afc_teams = []
            nfc_teams = []
            
            for team in self.teams.values():
                team_abbrev = team['abbreviation']
                emoji = self.get_team_emoji(interaction.guild, team_abbrev)
                claimed_by = claims_dict.get(team_abbrev)
                
                if claimed_by:
                    status = f"✅ Claimed by **{claimed_by}**"
                else:
                    status = "❌ Available"
                
                team_info = f"{emoji} **{team['name']}** ({team_abbrev}) - {status}"
                
                if team['conference'] == 'AFC':
                    afc_teams.append(team_info)
                else:
                    nfc_teams.append(team_info)
            
            # Sort teams alphabetically
            afc_teams.sort()
            nfc_teams.sort()
            
            # Add AFC teams
            afc_text = "\n".join(afc_teams)
            embed.add_field(
                name="🏈 AFC Teams (16)",
                value=afc_text[:1024] if len(afc_text) > 1024 else afc_text,
                inline=False
            )
            
            # Add NFC teams
            nfc_text = "\n".join(nfc_teams)
            embed.add_field(
                name="🏈 NFC Teams (16)",
                value=nfc_text[:1024] if len(nfc_text) > 1024 else nfc_text,
                inline=False
            )
            
            # Add summary
            claimed_count = len(claims_dict)
            available_count = 32 - claimed_count
            embed.add_field(
                name="📊 Summary",
                value=f"**Claimed:** {claimed_count}/32 teams\n**Available:** {available_count}/32 teams",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error listing teams: {e}")
            await interaction.response.send_message("❌ Error retrieving team list. Please try again later.", ephemeral=True)

    @app_commands.command(name="removeteam", description="Remove a team claim (Commissioner only)")
    @app_commands.describe(team="Team abbreviation to remove claim from")
    async def remove_team(self, interaction: discord.Interaction, team: str):
        """Remove a team claim - Commissioner only"""
        # Check if user is administrator
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ This command is only available to administrators.", ephemeral=True)
            return
        
        if not self.supabase:
            await interaction.response.send_message("❌ Database connection error. Please try again later.", ephemeral=True)
            return
        
        team_abbrev = team.upper()
        team_data = self.teams.get(team_abbrev)
        
        if not team_data:
            await interaction.response.send_message(f"❌ Invalid team abbreviation: {team}", ephemeral=True)
            return
        
        try:
            # Check if team is claimed
            claim_result = self.supabase.table("team_claims").select("user_id, display_name").eq("team_abbreviation", team_abbrev).execute()
            
            if not claim_result.data:
                await interaction.response.send_message(f"❌ **{team_data['name']}** is not currently claimed.", ephemeral=True)
                return
            
            # Remove the claim
            self.supabase.table("team_claims").delete().eq("team_abbreviation", team_abbrev).execute()
            
            emoji = self.get_team_emoji(interaction.guild, team_abbrev)
            claimed_by = claim_result.data[0]["display_name"]
            
            embed = discord.Embed(
                title="🏈 Team Claim Removed",
                description=f"Successfully removed team claim for **{team_data['name']}**",
                color=0xff6b6b
            )
            
            embed.add_field(
                name="Team Details",
                value=f"{emoji} **{team_data['name']}** ({team_abbrev})\n"
                      f"Conference: {team_data['conference']}\n"
                      f"Division: {team_data['division']}",
                inline=False
            )
            
            embed.add_field(
                name="Removed From",
                value=f"**{claimed_by}**",
                inline=False
            )
            
            embed.set_footer(text=f"Removed by {interaction.user.display_name}")
            
            await interaction.response.send_message(embed=embed)
            logger.info(f"Team {team_abbrev} claim removed by {interaction.user.display_name}")
            
        except Exception as e:
            logger.error(f"Error removing team claim: {e}")
            await interaction.response.send_message("❌ Error removing team claim. Please try again later.", ephemeral=True)

    @remove_team.autocomplete('team')
    async def team_autocomplete(self, interaction: discord.Interaction, current: str):
        """Autocomplete for team removal"""
        teams = []
        for team in self.teams.values():
            if current.lower() in team['name'].lower() or current.lower() in team['abbreviation'].lower():
                # Use default emoji for autocomplete
                default_emoji = team.get('emoji', '🏈')
                teams.append(app_commands.Choice(
                    name=f"{default_emoji} {team['name']} ({team['abbreviation']})",
                    value=team['abbreviation']
                ))
        
        # Sort by name and return first 25
        teams.sort(key=lambda x: x.name)
        return teams[:25]

async def setup(bot):
    await bot.add_cog(TeamClaimSystem(bot))
