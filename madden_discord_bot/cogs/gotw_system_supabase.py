import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import asyncio
import logging
from datetime import datetime
from supabase import create_client, Client

logger = logging.getLogger(__name__)

class GOTWSystemSupabase(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.teams_file = "data/nfl_teams.json"
        self.teams = {}
        
        # Initialize Supabase client
        try:
            supabase_url = os.getenv('SUPABASE_URL')
            supabase_key = os.getenv('SUPABASE_ANON_KEY')
            if supabase_url and supabase_key:
                self.supabase: Client = create_client(supabase_url, supabase_key)
                logger.info("✅ Supabase client initialized for GOTW system")
            else:
                logger.error("❌ Supabase credentials not found")
                self.supabase = None
        except Exception as e:
            logger.error(f"❌ Error initializing Supabase client: {e}")
            self.supabase = None
        
        # Load teams data
        self.load_teams()
        
        logger.info(f"✅ GOTWSystemSupabase cog initialized")

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
                logger.error(f"Teams file not found: {self.teams_file}")
                self.teams = {}
        except Exception as e:
            logger.error(f"Error loading teams data: {e}")
            self.teams = {}

    async def create_poll(self, interaction: discord.Interaction, team1_abbr: str, team2_abbr: str):
        """Create a new GOTW poll in the database"""
        if not self.supabase:
            await interaction.response.send_message("❌ Database connection not available.", ephemeral=True)
            return
        
        try:
            # Get team data
            team1 = self.teams.get(team1_abbr)
            team2 = self.teams.get(team2_abbr)
            
            if not team1 or not team2:
                await interaction.response.send_message("❌ Invalid team selection.", ephemeral=True)
                return
            
            # Generate unique poll ID
            poll_id = f"{interaction.user.id}_{int(datetime.now().timestamp())}"
            
            # Create poll in database
            poll_data = {
                'id': poll_id,
                'team1_name': team1['name'],
                'team1_abbr': team1_abbr,
                'team2_name': team2['name'],
                'team2_abbr': team2_abbr,
                'channel_id': interaction.channel.id,
                'guild_id': interaction.guild.id,
                'created_by': interaction.user.id,
                'is_locked': False,
                'winner_declared': False
            }
            
            result = await self.supabase.table('gotw_polls').insert(poll_data).execute()
            
            if result.data:
                logger.info(f"Created poll {poll_id}: {team1['name']} vs {team2['name']}")
                await self.show_gotw_card(interaction, team1, team2, poll_id)
            else:
                await interaction.response.send_message("❌ Failed to create poll.", ephemeral=True)
                
        except Exception as e:
            logger.error(f"Error creating poll: {e}")
            await interaction.response.send_message("❌ Error creating poll. Please try again.", ephemeral=True)

    async def show_gotw_card(self, interaction: discord.Interaction, team1: dict, team2: dict, poll_id: str):
        """Show the GOTW card with voting buttons"""
        try:
            # Create embed
            embed = discord.Embed(
                title="⭐ GAME OF THE WEEK ⭐",
                description=f"**{team1['name']} vs {team2['name']}**",
                color=0x00ff00
            )
            
            # Add team info
            embed.add_field(
                name=f"{team1.get('emoji', '🏈')} {team1['name']}",
                value=f"Conference: {team1['conference']}\nDivision: {team1['division']}",
                inline=True
            )
            
            embed.add_field(
                name=f"{team2.get('emoji', '🏈')} {team2['name']}",
                value=f"Conference: {team2['conference']}\nDivision: {team2['division']}",
                inline=True
            )
            
            embed.set_footer(text="Click the buttons below to vote!")
            
            # Create view with buttons
            view = GOTWView(self, team1, team2, poll_id)
            
            # Send message
            message = await interaction.response.send_message(embed=embed, view=view)
            
            # Update poll with message ID
            await self.update_poll_message_id(poll_id, message.id)
            
        except Exception as e:
            logger.error(f"Error showing GOTW card: {e}")
            await interaction.response.send_message("❌ Error creating poll display.", ephemeral=True)

    async def update_poll_message_id(self, poll_id: str, message_id: int):
        """Update poll with Discord message ID"""
        try:
            await self.supabase.table('gotw_polls').update({
                'message_id': message_id
            }).eq('id', poll_id).execute()
        except Exception as e:
            logger.error(f"Error updating poll message ID: {e}")

    async def handle_vote(self, interaction: discord.Interaction, team_abbr: str, poll_id: str):
        """Handle a vote for a specific team"""
        if not self.supabase:
            await interaction.response.send_message("❌ Database connection not available.", ephemeral=True)
            return
        
        try:
            # Check if poll exists and is not locked
            poll_result = await self.supabase.table('gotw_polls').select('*').eq('id', poll_id).execute()
            
            if not poll_result.data:
                await interaction.response.send_message("❌ Poll not found.", ephemeral=True)
                return
            
            poll_data = poll_result.data[0]
            
            if poll_data['is_locked']:
                await interaction.response.send_message("❌ This poll is locked.", ephemeral=True)
                return
            
            if poll_data['winner_declared']:
                await interaction.response.send_message("❌ This poll has already been completed.", ephemeral=True)
                return
            
            # Remove existing vote for this user
            await self.supabase.table('gotw_votes').delete().eq('poll_id', poll_id).eq('user_id', interaction.user.id).execute()
            
            # Add new vote
            vote_data = {
                'poll_id': poll_id,
                'user_id': interaction.user.id,
                'team_abbr': team_abbr
            }
            
            await self.supabase.table('gotw_votes').insert(vote_data).execute()
            
            # Get team name for confirmation
            team_name = poll_data['team1_name'] if team_abbr == poll_data['team1_abbr'] else poll_data['team2_name']
            
            await interaction.response.send_message(f"✅ Vote recorded for {team_name}!", ephemeral=True)
            
            # Update the message with new vote counts
            await self.update_vote_message(interaction.message, poll_id)
            
        except Exception as e:
            logger.error(f"Error handling vote: {e}")
            await interaction.response.send_message("❌ Error recording vote. Please try again.", ephemeral=True)

    async def show_results(self, interaction: discord.Interaction, poll_id: str):
        """Show poll results"""
        if not self.supabase:
            await interaction.response.send_message("❌ Database connection not available.", ephemeral=True)
            return
        
        try:
            # Try to get poll data with vote counts using the function
            try:
                result = await self.supabase.rpc('get_poll_with_votes', {'poll_id_param': poll_id}).execute()
                if result.data:
                    poll_data = result.data[0]
                else:
                    raise Exception("No data returned from function")
            except Exception as e:
                # Fallback to manual query if function doesn't exist
                logger.warning(f"get_poll_with_votes function failed, using fallback: {e}")
                
                # Get poll data
                poll_result = await self.supabase.table('gotw_polls').select('*').eq('id', poll_id).execute()
                if not poll_result.data:
                    await interaction.response.send_message("❌ Poll not found.", ephemeral=True)
                    return
                
                poll_info = poll_result.data[0]
                
                # Get vote counts manually
                votes_result = await self.supabase.table('gotw_votes').select('team_abbr').eq('poll_id', poll_id).execute()
                
                team1_votes = len([v for v in votes_result.data if v['team_abbr'] == poll_info['team1_abbr']])
                team2_votes = len([v for v in votes_result.data if v['team_abbr'] == poll_info['team2_abbr']])
                total_votes = len(votes_result.data)
                
                # Create poll_data structure
                poll_data = {
                    'team1_name': poll_info['team1_name'],
                    'team1_abbr': poll_info['team1_abbr'],
                    'team2_name': poll_info['team2_name'],
                    'team2_abbr': poll_info['team2_abbr'],
                    'is_locked': poll_info['is_locked'],
                    'winner_declared': poll_info['winner_declared'],
                    'winner_team': poll_info['winner_team'],
                    'team1_votes': team1_votes,
                    'team2_votes': team2_votes,
                    'total_votes': total_votes
                }
            
            # Create results embed
            embed = discord.Embed(
                title="📊 GOTW Voting Results",
                color=0x00ff00
            )
            
            # Add vote breakdown
            team1_votes = poll_data['team1_votes'] or 0
            team2_votes = poll_data['team2_votes'] or 0
            total_votes = poll_data['total_votes'] or 0
            
            team1_percentage = (team1_votes / total_votes * 100) if total_votes > 0 else 0
            team2_percentage = (team2_votes / total_votes * 100) if total_votes > 0 else 0
            
            embed.add_field(
                name=f"{poll_data['team1_name']} ({team1_votes} votes)",
                value=f"{team1_percentage:.1f}%",
                inline=True
            )
            
            embed.add_field(
                name=f"{poll_data['team2_name']} ({team2_votes} votes)",
                value=f"{team2_percentage:.1f}%",
                inline=True
            )
            
            if poll_data['winner_declared']:
                winner_name = poll_data['team1_name'] if poll_data['winner_team'] == poll_data['team1_abbr'] else poll_data['team2_name']
                embed.add_field(
                    name="🏆 Winner",
                    value=f"{winner_name}",
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error showing results: {e}")
            await interaction.response.send_message("❌ Error retrieving results.", ephemeral=True)

    async def lock_poll(self, interaction: discord.Interaction, poll_id: str):
        """Lock or unlock a poll"""
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ You don't have permission to lock polls.", ephemeral=True)
            return
        
        if not self.supabase:
            await interaction.response.send_message("❌ Database connection not available.", ephemeral=True)
            return
        
        try:
            # Get current lock status
            poll_result = await self.supabase.table('gotw_polls').select('is_locked').eq('id', poll_id).execute()
            
            if not poll_result.data:
                await interaction.response.send_message("❌ Poll not found.", ephemeral=True)
                return
            
            current_status = poll_result.data[0]['is_locked']
            new_status = not current_status
            
            # Update lock status
            await self.supabase.table('gotw_polls').update({
                'is_locked': new_status
            }).eq('id', poll_id).execute()
            
            status_text = "locked" if new_status else "unlocked"
            await interaction.response.send_message(f"✅ Poll has been {status_text}.", ephemeral=True)
            
            # Update the message
            await self.update_vote_message(interaction.message, poll_id)
            
        except Exception as e:
            logger.error(f"Error locking poll: {e}")
            await interaction.response.send_message("❌ Error updating poll status.", ephemeral=True)

    async def declare_winner(self, interaction: discord.Interaction, poll_id: str, winning_team: str):
        """Declare a winner for the poll"""
        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ You don't have permission to declare winners.", ephemeral=True)
            return
        
        if not self.supabase:
            await interaction.response.send_message("❌ Database connection not available.", ephemeral=True)
            return
        
        try:
            # Update poll with winner
            await self.supabase.table('gotw_polls').update({
                'winner_declared': True,
                'winner_team': winning_team,
                'winner_declared_by': interaction.user.id,
                'winner_declared_at': datetime.now().isoformat()
            }).eq('id', poll_id).execute()
            
            # Award points to voters and team claimers
            await self.award_points_for_winner(poll_id, winning_team)
            
            # Get team name for confirmation
            poll_result = await self.supabase.table('gotw_polls').select('team1_name', 'team2_name', 'team1_abbr', 'team2_abbr').eq('id', poll_id).execute()
            if poll_result.data:
                poll_data = poll_result.data[0]
                winner_name = poll_data['team1_name'] if winning_team == poll_data['team1_abbr'] else poll_data['team2_name']
                await interaction.response.send_message(f"🏆 {winner_name} has been declared the winner!", ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error declaring winner: {e}")
            await interaction.response.send_message("❌ Error declaring winner.", ephemeral=True)

    async def award_points_for_winner(self, poll_id: str, winning_team: str):
        """Award points to voters and team claimers"""
        try:
            points_cog = self.bot.get_cog('PointsSystemSupabase')
            if not points_cog:
                logger.error("PointsSystemSupabase cog not found")
                return
            
            # Get winning voters
            votes_result = await self.supabase.table('gotw_votes').select('user_id').eq('poll_id', poll_id).eq('team_abbr', winning_team).execute()
            
            # Award points to voters
            for vote in votes_result.data:
                try:
                    await points_cog.add_user_points(vote['user_id'], 1, "GOTW vote")
                except Exception as e:
                    logger.error(f"Error awarding points to user {vote['user_id']}: {e}")
            
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

    async def update_vote_message(self, message: discord.Message, poll_id: str):
        """Update the vote message with current counts and lock status"""
        try:
            if not self.supabase:
                return
            
            # Try to get poll data with vote counts using the function
            try:
                result = await self.supabase.rpc('get_poll_with_votes', {'poll_id_param': poll_id}).execute()
                if result.data:
                    poll_data = result.data[0]
                else:
                    raise Exception("No data returned from function")
            except Exception as e:
                # Fallback to manual query if function doesn't exist
                logger.warning(f"get_poll_with_votes function failed in update_vote_message, using fallback: {e}")
                
                # Get poll data
                poll_result = await self.supabase.table('gotw_polls').select('*').eq('id', poll_id).execute()
                if not poll_result.data:
                    return
                
                poll_info = poll_result.data[0]
                
                # Get vote counts manually
                votes_result = await self.supabase.table('gotw_votes').select('team_abbr').eq('poll_id', poll_id).execute()
                
                team1_votes = len([v for v in votes_result.data if v['team_abbr'] == poll_info['team1_abbr']])
                team2_votes = len([v for v in votes_result.data if v['team_abbr'] == poll_info['team2_abbr']])
                total_votes = len(votes_result.data)
                
                # Create poll_data structure
                poll_data = {
                    'team1_name': poll_info['team1_name'],
                    'team1_abbr': poll_info['team1_abbr'],
                    'team2_name': poll_info['team2_name'],
                    'team2_abbr': poll_info['team2_abbr'],
                    'is_locked': poll_info['is_locked'],
                    'winner_declared': poll_info['winner_declared'],
                    'winner_team': poll_info['winner_team'],
                    'team1_votes': team1_votes,
                    'team2_votes': team2_votes,
                    'total_votes': total_votes
                }
            
            # Get current embed
            if message.embeds:
                embed = message.embeds[0]
                
                # Update lock status in footer
                if poll_data['is_locked']:
                    embed.set_footer(text="🔒 This poll is locked")
                else:
                    embed.set_footer(text="Click the buttons below to vote!")
                
                # Update vote counts in fields
                team1_votes = poll_data['team1_votes'] or 0
                team2_votes = poll_data['team2_votes'] or 0
                total_votes = poll_data['total_votes'] or 0
                
                # Update or add vote count fields
                embed.clear_fields()
                
                embed.add_field(
                    name=f"{poll_data['team1_name']}",
                    value=f"Conference: {poll_data['team1_name']}\nDivision: {poll_data['team1_name']}\nVotes: {team1_votes}",
                    inline=True
                )
                
                embed.add_field(
                    name=f"{poll_data['team2_name']}",
                    value=f"Conference: {poll_data['team2_name']}\nDivision: {poll_data['team2_name']}\nVotes: {team2_votes}",
                    inline=True
                )
                
                if total_votes > 0:
                    embed.add_field(
                        name="Total Votes",
                        value=f"{total_votes}",
                        inline=True
                    )
                
                await message.edit(embed=embed)
                
        except Exception as e:
            logger.error(f"Error updating vote message: {e}")

class GOTWView(discord.ui.View):
    def __init__(self, cog, team1: dict, team2: dict, poll_id: str):
        super().__init__(timeout=None)  # No timeout for persistent views
        self.cog = cog
        self.team1 = team1
        self.team2 = team2
        self.poll_id = poll_id
        
        # Add vote buttons
        self.add_item(VoteButton(team1, cog, poll_id))
        self.add_item(VoteButton(team2, cog, poll_id))
        
        # Add action buttons
        self.add_item(ResultsButton(cog, poll_id))
        self.add_item(LockButton(cog, poll_id))

class VoteButton(discord.ui.Button):
    def __init__(self, team: dict, cog, poll_id: str):
        super().__init__(
            label=f"Vote {team['abbreviation']}",
            style=discord.ButtonStyle.primary,
            custom_id=f"vote_{poll_id}_{team['abbreviation']}"
        )
        self.team = team
        self.cog = cog
        self.poll_id = poll_id

    async def callback(self, interaction: discord.Interaction):
        await self.cog.handle_vote(interaction, self.team['abbreviation'], self.poll_id)

class ResultsButton(discord.ui.Button):
    def __init__(self, cog, poll_id: str):
        super().__init__(
            label="Show Results",
            style=discord.ButtonStyle.secondary,
            custom_id=f"show_results_{poll_id}"
        )
        self.cog = cog
        self.poll_id = poll_id

    async def callback(self, interaction: discord.Interaction):
        await self.cog.show_results(interaction, self.poll_id)

class LockButton(discord.ui.Button):
    def __init__(self, cog, poll_id: str):
        super().__init__(
            label="Lock Poll",
            style=discord.ButtonStyle.danger,
            custom_id=f"lock_poll_{poll_id}"
        )
        self.cog = cog
        self.poll_id = poll_id

    async def callback(self, interaction: discord.Interaction):
        await self.cog.lock_poll(interaction, self.poll_id)

async def setup(bot):
    await bot.add_cog(GOTWSystemSupabase(bot))
