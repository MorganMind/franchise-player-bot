import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class NFLSchedule(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.schedule_file = "data/nfl_schedule.json"
        self.teams_file = "data/nfl_teams.json"
        self.current_week = None
        self.schedule_data = {}
        self.load_schedule_data()
        self.load_teams()
        logger.info("✅ NFLSchedule cog initialized")
    
    def load_teams(self):
        """Load NFL teams data"""
        try:
            if os.path.exists(self.teams_file):
                with open(self.teams_file, 'r') as f:
                    teams_data = json.load(f)
                    self.teams = {team['abbreviation']: team for team in teams_data['teams']}
            else:
                # Fallback teams data
                self.teams = {
                    "ARI": {"name": "Arizona Cardinals", "abbreviation": "ARI", "emoji": "🃏"},
                    "ATL": {"name": "Atlanta Falcons", "abbreviation": "ATL", "emoji": "🦅"},
                    "BAL": {"name": "Baltimore Ravens", "abbreviation": "BAL", "emoji": "🐦‍⬛"},
                    "BUF": {"name": "Buffalo Bills", "abbreviation": "BUF", "emoji": "🦬"},
                    "CAR": {"name": "Carolina Panthers", "abbreviation": "CAR", "emoji": "🐆"},
                    "CHI": {"name": "Chicago Bears", "abbreviation": "CHI", "emoji": "🐻"},
                    "CIN": {"name": "Cincinnati Bengals", "abbreviation": "CIN", "emoji": "🐯"},
                    "CLE": {"name": "Cleveland Browns", "abbreviation": "CLE", "emoji": "🐕"},
                    "DAL": {"name": "Dallas Cowboys", "abbreviation": "DAL", "emoji": "⭐"},
                    "DEN": {"name": "Denver Broncos", "abbreviation": "DEN", "emoji": "🐎"},
                    "DET": {"name": "Detroit Lions", "abbreviation": "DET", "emoji": "🦁"},
                    "GB": {"name": "Green Bay Packers", "abbreviation": "GB", "emoji": "🧀"},
                    "HOU": {"name": "Houston Texans", "abbreviation": "HOU", "emoji": "🤠"},
                    "IND": {"name": "Indianapolis Colts", "abbreviation": "IND", "emoji": "🐎"},
                    "JAX": {"name": "Jacksonville Jaguars", "abbreviation": "JAX", "emoji": "🐆"},
                    "KC": {"name": "Kansas City Chiefs", "abbreviation": "KC", "emoji": "🏹"},
                    "LV": {"name": "Las Vegas Raiders", "abbreviation": "LV", "emoji": "🏴‍☠️"},
                    "LAC": {"name": "Los Angeles Chargers", "abbreviation": "LAC", "emoji": "⚡"},
                    "LAR": {"name": "Los Angeles Rams", "abbreviation": "LAR", "emoji": "🐏"},
                    "MIA": {"name": "Miami Dolphins", "abbreviation": "MIA", "emoji": "🐬"},
                    "MIN": {"name": "Minnesota Vikings", "abbreviation": "MIN", "emoji": "🛡️"},
                    "NE": {"name": "New England Patriots", "abbreviation": "NE", "emoji": "🇺🇸"},
                    "NO": {"name": "New Orleans Saints", "abbreviation": "NO", "emoji": "⛪"},
                    "NYG": {"name": "New York Giants", "abbreviation": "NYG", "emoji": "👹"},
                    "NYJ": {"name": "New York Jets", "abbreviation": "NYJ", "emoji": "✈️"},
                    "PHI": {"name": "Philadelphia Eagles", "abbreviation": "PHI", "emoji": "🦅"},
                    "PIT": {"name": "Pittsburgh Steelers", "abbreviation": "PIT", "emoji": "⚫"},
                    "SF": {"name": "San Francisco 49ers", "abbreviation": "SF", "emoji": "💎"},
                    "SEA": {"name": "Seattle Seahawks", "abbreviation": "SEA", "emoji": "🦅"},
                    "TB": {"name": "Tampa Bay Buccaneers", "abbreviation": "TB", "emoji": "☠️"},
                    "TEN": {"name": "Tennessee Titans", "abbreviation": "TEN", "emoji": "⚔️"},
                    "WAS": {"name": "Washington Commanders", "abbreviation": "WAS", "emoji": "⚔️"}
                }
        except Exception as e:
            logger.error(f"Error loading teams: {e}")
            self.teams = {}
    
    def load_schedule_data(self):
        """Load schedule data from JSON file"""
        try:
            os.makedirs(os.path.dirname(self.schedule_file), exist_ok=True)
            
            if os.path.exists(self.schedule_file):
                with open(self.schedule_file, 'r') as f:
                    data = json.load(f)
                    self.current_week = data.get('current_week')
                    self.schedule_data = data.get('schedule', {})
            else:
                self.save_schedule_data()
        except Exception as e:
            logger.error(f"Error loading schedule data: {e}")
            self.current_week = None
            self.schedule_data = {}
    
    def save_schedule_data(self):
        """Save schedule data to JSON file"""
        try:
            data = {
                'current_week': self.current_week,
                'schedule': self.schedule_data
            }
            with open(self.schedule_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving schedule data: {e}")
    
    def get_current_nfl_week(self):
        """Get the current NFL week (simplified calculation)"""
        # NFL season typically starts first Thursday in September
        # This is a simplified calculation - you might want to use an API
        today = datetime.now()
        season_start = datetime(today.year, 9, 1)  # Approximate
        
        # Find first Thursday
        while season_start.weekday() != 3:  # Thursday is 3
            season_start += timedelta(days=1)
        
        weeks_since_start = (today - season_start).days // 7
        return max(1, min(18, weeks_since_start + 1))  # NFL has 18 weeks
    
    @app_commands.command(name="nfl", description="NFL Schedule management commands")
    @app_commands.describe(
        action="Action to perform: setup, create, list, clear, delete, bulk-delete, bulk-delete-confirm",
        week="NFL week number (1-18)",
        delete_previous="Delete previous week's channels",
        announcement_channel="Channel to announce new week"
    )
    async def nfl(self, interaction: discord.Interaction, action: str, week: int = None, delete_previous: bool = False, announcement_channel: discord.TextChannel = None):
        """Main NFL schedule command"""
        if action.lower() == "setup":
            await self.setup_nfl_channels(interaction)
        elif action.lower() == "create":
            await self.create_week_channels(interaction, week, delete_previous, announcement_channel)
        elif action.lower() == "list":
            await self.list_schedule(interaction, week)
        elif action.lower() == "clear":
            await self.clear_schedule(interaction)
        elif action.lower() == "delete":
            await self.delete_week_channels(interaction, week)
        elif action.lower() == "bulk-delete":
            await self.bulk_delete_nfl_channels(interaction)
        elif action.lower() == "bulk-delete-confirm":
            await self.bulk_delete_nfl_channels_confirm(interaction)
        else:
            await interaction.response.send_message("❌ Invalid action. Use: setup, create, list, clear, delete, bulk-delete, or bulk-delete-confirm", ephemeral=True)
    
    async def setup_nfl_channels(self, interaction: discord.Interaction):
        """Setup NFL schedule category and channels - MVP Version"""
        # Defer the response immediately to avoid timeout
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Create Week 1 category
            category = await interaction.guild.create_category(
                name="Week 1",
                reason=f"Week 1 category created by {interaction.user.display_name}"
            )
            
            # Create one fictional game channel
            game_channel = await interaction.guild.create_text_channel(
                name="cowboys-vs-eagles",
                category=category,
                topic="Dallas Cowboys vs Philadelphia Eagles - Week 1 | NFL-BOT-CHANNEL",
                reason="Week 1 game channel"
            )
            
            # Create game embed
            embed = discord.Embed(
                title="🏈 Week 1 - Cowboys vs Eagles",
                description="⭐ **Dallas Cowboys** @ 🦅 **Philadelphia Eagles**",
                color=0x00ff00
            )
            
            embed.add_field(
                name="📅 Game Info",
                value="**Week:** 1\n**Time:** Sunday 4:25 PM ET\n**Venue:** Lincoln Financial Field",
                inline=True
            )
            
            embed.add_field(
                name="📺 Broadcast",
                value="FOX",
                inline=True
            )
            
            embed.set_footer(text=f"Channel created by {interaction.user.display_name} | NFL-BOT-CHANNEL")
            
            await game_channel.send(embed=embed)
            
            await interaction.followup.send(
                f"✅ Created Week 1 category with game channel: {game_channel.mention}",
                ephemeral=True
            )
            
        except discord.Forbidden:
            await interaction.followup.send("❌ I don't have permission to create channels. Please make sure I have 'Manage Channels' permission.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error creating channels: {str(e)}", ephemeral=True)
    
    async def create_week_channels(self, interaction: discord.Interaction, week: int = None, delete_previous: bool = False, announcement_channel: discord.TextChannel = None):
        """Create channels for a specific NFL week"""
        # Defer the response immediately to avoid timeout
        await interaction.response.defer(ephemeral=True)
        
        if week is None:
            week = self.get_current_nfl_week()
        
        if week < 1 or week > 18:
            await interaction.followup.send("❌ NFL week must be between 1 and 18", ephemeral=True)
            return
        
        try:
            # Delete previous week if requested
            deleted_channels = []
            if delete_previous:
                previous_week = week - 1
                if previous_week >= 1:
                    deleted_channels = await self.delete_week_channels_internal(interaction.guild, previous_week)
            
            # Create category with internal app ID
            category_name = f"Week {week} - NFL Schedule"
            category = discord.utils.get(interaction.guild.categories, name=category_name)
            if not category:
                category = await interaction.guild.create_category(
                    name=category_name,
                    reason=f"Week {week} NFL schedule category created by {interaction.user.display_name}"
                )
            
            # Get sample schedule for the week
            week_games = self.get_sample_schedule(week)
            
            created_channels = []
            
            for i, game in enumerate(week_games, 1):
                away_team = self.teams.get(game['away'], {})
                home_team = self.teams.get(game['home'], {})
                
                # Create channel name with internal app ID
                channel_name = f"week{week}-{i:02d}-{game['away']}-vs-{game['home']}"
                
                # Create channel
                channel = await interaction.guild.create_text_channel(
                    name=channel_name,
                    category=category,
                    topic=f"{away_team.get('name', game['away'])} vs {home_team.get('name', game['home'])} - Week {week} | NFL-BOT-CHANNEL",
                    reason=f"Week {week} game channel"
                )
                
                # Create game embed
                embed = discord.Embed(
                    title=f"🏈 Week {week} - Game {i}",
                    description=f"{away_team.get('emoji', '🏈')} **{away_team.get('name', game['away'])}** @ {home_team.get('emoji', '🏈')} **{home_team.get('name', game['home'])}**",
                    color=0x00ff00
                )
                
                embed.add_field(
                    name="📅 Game Info",
                    value=f"**Week:** {week}\n**Game:** {i}\n**Time:** {game.get('time', 'TBD')}",
                    inline=True
                )
                
                embed.add_field(
                    name="🏟️ Venue",
                    value=game.get('venue', 'TBD'),
                    inline=True
                )
                
                embed.add_field(
                    name="📺 Broadcast",
                    value=game.get('broadcast', 'TBD'),
                    inline=True
                )
                
                embed.set_footer(text=f"Channel created by {interaction.user.display_name} | NFL-BOT-CHANNEL")
                
                await channel.send(embed=embed)
                created_channels.append(channel)
            
            # Save schedule data
            self.current_week = week
            self.schedule_data[str(week)] = week_games
            self.save_schedule_data()
            
            # Create response message
            response_parts = []
            
            if delete_previous and deleted_channels:
                response_parts.append(f"🗑️ Deleted {len(deleted_channels)} channels from Week {week-1}")
            
            response_parts.append(f"✅ Created {len(created_channels)} channels for Week {week}")
            response_parts.append(f"Channels: {', '.join([ch.mention for ch in created_channels])}")
            
            await interaction.followup.send("\n".join(response_parts), ephemeral=True)
            
            # Send announcement if channel provided
            if announcement_channel:
                announcement_embed = discord.Embed(
                    title=f"🏈 NFL Week {week} is Here!",
                    description=f"Game channels have been created for Week {week}!",
                    color=0x00ff00
                )
                
                announcement_embed.add_field(
                    name="📋 Games This Week",
                    value=f"**{len(week_games)} games** scheduled",
                    inline=True
                )
                
                announcement_embed.add_field(
                    name="📍 Category",
                    value=category.mention,
                    inline=True
                )
                
                announcement_embed.add_field(
                    name="🎯 Quick Access",
                    value="\n".join([f"• {ch.mention}" for ch in created_channels[:5]]),  # Show first 5 channels
                    inline=False
                )
                
                if len(created_channels) > 5:
                    announcement_embed.add_field(
                        name="📁 More Games",
                        value=f"Check {category.mention} for all {len(created_channels)} game channels",
                        inline=False
                    )
                
                await announcement_channel.send(embed=announcement_embed)
            
        except discord.Forbidden:
            await interaction.followup.send("❌ I don't have permission to create channels", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error creating week channels: {str(e)}", ephemeral=True)
    
    def get_sample_schedule(self, week):
        """Get sample schedule for a week (replace with real API data)"""
        # This is sample data - you would typically fetch this from an NFL API
        sample_games = {
            1: [
                {"away": "DET", "home": "KC", "time": "Thursday 8:20 PM ET", "venue": "Arrowhead Stadium", "broadcast": "NBC"},
                {"away": "CAR", "home": "ATL", "time": "Sunday 1:00 PM ET", "venue": "Mercedes-Benz Stadium", "broadcast": "FOX"},
                {"away": "CIN", "home": "CLE", "time": "Sunday 1:00 PM ET", "venue": "FirstEnergy Stadium", "broadcast": "CBS"},
                {"away": "HOU", "home": "BAL", "time": "Sunday 1:00 PM ET", "venue": "M&T Bank Stadium", "broadcast": "CBS"},
                {"away": "JAX", "home": "IND", "time": "Sunday 1:00 PM ET", "venue": "Lucas Oil Stadium", "broadcast": "FOX"},
                {"away": "TB", "home": "MIN", "time": "Sunday 1:00 PM ET", "venue": "U.S. Bank Stadium", "broadcast": "CBS"},
                {"away": "TEN", "home": "NO", "time": "Sunday 1:00 PM ET", "venue": "Caesars Superdome", "broadcast": "CBS"},
                {"away": "SF", "home": "PIT", "time": "Sunday 1:00 PM ET", "venue": "Acrisure Stadium", "broadcast": "FOX"},
                {"away": "ARI", "home": "WAS", "time": "Sunday 1:00 PM ET", "venue": "FedExField", "broadcast": "FOX"},
                {"away": "GB", "home": "CHI", "time": "Sunday 4:25 PM ET", "venue": "Soldier Field", "broadcast": "FOX"},
                {"away": "LV", "home": "DEN", "time": "Sunday 4:25 PM ET", "venue": "Empower Field", "broadcast": "CBS"},
                {"away": "MIA", "home": "LAC", "time": "Sunday 4:25 PM ET", "venue": "SoFi Stadium", "broadcast": "CBS"},
                {"away": "PHI", "home": "NE", "time": "Sunday 4:25 PM ET", "venue": "Gillette Stadium", "broadcast": "CBS"},
                {"away": "LAR", "home": "SEA", "time": "Sunday 4:25 PM ET", "venue": "Lumen Field", "broadcast": "FOX"},
                {"away": "DAL", "home": "NYG", "time": "Sunday 8:20 PM ET", "venue": "MetLife Stadium", "broadcast": "NBC"},
                {"away": "BUF", "home": "NYJ", "time": "Monday 8:15 PM ET", "venue": "MetLife Stadium", "broadcast": "ESPN"}
            ],
            2: [
                {"away": "PHI", "home": "MIN", "time": "Thursday 8:20 PM ET", "venue": "U.S. Bank Stadium", "broadcast": "Prime Video"},
                {"away": "GB", "home": "ATL", "time": "Sunday 1:00 PM ET", "venue": "Mercedes-Benz Stadium", "broadcast": "FOX"},
                {"away": "LV", "home": "BUF", "time": "Sunday 1:00 PM ET", "venue": "Highmark Stadium", "broadcast": "CBS"},
                {"away": "BAL", "home": "CIN", "time": "Sunday 1:00 PM ET", "venue": "Paycor Stadium", "broadcast": "CBS"},
                {"away": "SEA", "home": "DET", "time": "Sunday 1:00 PM ET", "venue": "Ford Field", "broadcast": "FOX"},
                {"away": "LAC", "home": "TEN", "time": "Sunday 1:00 PM ET", "venue": "Nissan Stadium", "broadcast": "CBS"},
                {"away": "CHI", "home": "TB", "time": "Sunday 1:00 PM ET", "venue": "Raymond James Stadium", "broadcast": "FOX"},
                {"away": "IND", "home": "HOU", "time": "Sunday 1:00 PM ET", "venue": "NRG Stadium", "broadcast": "CBS"},
                {"away": "KC", "home": "JAX", "time": "Sunday 1:00 PM ET", "venue": "EverBank Stadium", "broadcast": "CBS"},
                {"away": "CLE", "home": "PIT", "time": "Monday 8:15 PM ET", "venue": "Acrisure Stadium", "broadcast": "ABC"}
            ]
        }
        
        return sample_games.get(week, [
            {"away": "DAL", "home": "PHI", "time": "Sunday 1:00 PM ET", "venue": "Lincoln Financial Field", "broadcast": "FOX"},
            {"away": "KC", "home": "BUF", "time": "Sunday 4:25 PM ET", "venue": "Highmark Stadium", "broadcast": "CBS"}
        ])
    
    async def list_schedule(self, interaction: discord.Interaction, week: int = None):
        """List schedule for a specific week"""
        if week is None:
            week = self.get_current_nfl_week()
        
        if week < 1 or week > 18:
            await interaction.response.send_message("❌ NFL week must be between 1 and 18", ephemeral=True)
            return
        
        week_games = self.schedule_data.get(str(week), self.get_sample_schedule(week))
        
        embed = discord.Embed(
            title=f"📋 NFL Week {week} Schedule",
            description=f"Games scheduled for Week {week}",
            color=0x00ff00
        )
        
        for i, game in enumerate(week_games, 1):
            away_team = self.teams.get(game['away'], {})
            home_team = self.teams.get(game['home'], {})
            
            embed.add_field(
                name=f"Game {i}: {away_team.get('name', game['away'])} @ {home_team.get('name', game['home'])}",
                value=f"**Time:** {game.get('time', 'TBD')}\n"
                      f"**Venue:** {game.get('venue', 'TBD')}\n"
                      f"**Broadcast:** {game.get('broadcast', 'TBD')}",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    
    async def clear_schedule(self, interaction: discord.Interaction):
        """Clear all schedule data"""
        self.current_week = None
        self.schedule_data = {}
        self.save_schedule_data()
        
        await interaction.response.send_message("✅ NFL schedule data cleared!", ephemeral=True)
    
    async def delete_week_channels(self, interaction: discord.Interaction, week: int = None):
        """Delete channels for a specific NFL week"""
        await interaction.response.defer(ephemeral=True)
        
        if week is None:
            await interaction.followup.send("❌ Please specify a week number to delete", ephemeral=True)
            return
        
        if week < 1 or week > 18:
            await interaction.followup.send("❌ NFL week must be between 1 and 18", ephemeral=True)
            return
        
        try:
            deleted_channels = await self.delete_week_channels_internal(interaction.guild, week)
            
            if deleted_channels:
                await interaction.followup.send(
                    f"🗑️ Deleted {len(deleted_channels)} channels from Week {week}",
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    f"❌ No channels found for Week {week}",
                    ephemeral=True
                )
                
        except Exception as e:
            await interaction.followup.send(f"❌ Error deleting week channels: {str(e)}", ephemeral=True)
    
    async def delete_week_channels_internal(self, guild, week: int):
        """Internal method to delete channels for a specific week"""
        deleted_channels = []
        
        # Find and delete the category
        category_name = f"Week {week} - NFL Schedule"
        category = discord.utils.get(guild.categories, name=category_name)
        
        if category:
            # Delete all channels in the category
            for channel in category.channels:
                if "NFL-BOT-CHANNEL" in channel.topic or channel.name.startswith(f"week{week}-"):
                    try:
                        await channel.delete(reason=f"Deleting Week {week} NFL channels")
                        deleted_channels.append(channel.name)
                    except Exception as e:
                        logger.error(f"Error deleting channel {channel.name}: {e}")
            
            # Delete the category itself
            try:
                await category.delete(reason=f"Deleting Week {week} NFL category")
                deleted_channels.append(category.name)
            except Exception as e:
                logger.error(f"Error deleting category {category.name}: {e}")
        
        return deleted_channels
    
    async def bulk_delete_nfl_channels(self, interaction: discord.Interaction):
        """Delete all NFL bot channels across all weeks"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # First, scan and identify what would be deleted
            channels_to_delete = []
            categories_to_delete = []
            
            # Find all categories that match NFL schedule pattern
            for category in interaction.guild.categories:
                if "NFL Schedule" in category.name:
                    # Identify channels to delete
                    for channel in category.channels:
                        # DOUBLE SAFETY CHECK: Must have both topic identifier AND name pattern
                        has_bot_topic = channel.topic and "NFL-BOT-CHANNEL" in channel.topic
                        has_week_pattern = channel.name.startswith("week") and "-" in channel.name
                        
                        if has_bot_topic or (has_week_pattern and channel.name.count("-") >= 2):
                            channels_to_delete.append(channel)
                    
                    categories_to_delete.append(category)
            
            # Also find any orphaned channels with NFL-BOT-CHANNEL in topic
            for channel in interaction.guild.channels:
                if hasattr(channel, 'topic') and channel.topic and "NFL-BOT-CHANNEL" in channel.topic:
                    if channel not in channels_to_delete:
                        channels_to_delete.append(channel)
            
            # Show what will be deleted
            if not channels_to_delete and not categories_to_delete:
                await interaction.followup.send("❌ No NFL bot channels found to delete", ephemeral=True)
                return
            
            # Create preview message
            preview_embed = discord.Embed(
                title="⚠️ Bulk Delete Preview",
                description="The following channels and categories will be deleted:",
                color=0xff0000
            )
            
            if channels_to_delete:
                channel_list = [f"• {ch.name}" for ch in channels_to_delete[:15]]
                if len(channels_to_delete) > 15:
                    channel_list.append(f"... and {len(channels_to_delete) - 15} more")
                
                preview_embed.add_field(
                    name=f"📁 Channels to Delete ({len(channels_to_delete)})",
                    value="\n".join(channel_list),
                    inline=False
                )
            
            if categories_to_delete:
                category_list = [f"• {cat.name}" for cat in categories_to_delete]
                preview_embed.add_field(
                    name=f"📂 Categories to Delete ({len(categories_to_delete)})",
                    value="\n".join(category_list),
                    inline=False
                )
            
            preview_embed.add_field(
                name="🔒 Safety Check",
                value="✅ Only channels with 'NFL-BOT-CHANNEL' in topic or specific week naming pattern will be deleted",
                inline=False
            )
            
            preview_embed.set_footer(text="This action cannot be undone!")
            
            await interaction.followup.send(
                "⚠️ **BULK DELETE PREVIEW** ⚠️\n"
                f"Found {len(channels_to_delete)} channels and {len(categories_to_delete)} categories to delete.\n"
                "**This action cannot be undone!**\n\n"
                "To proceed with deletion, run: `/nfl bulk-delete-confirm`",
                embed=preview_embed,
                ephemeral=True
            )
                
        except Exception as e:
            await interaction.followup.send(f"❌ Error during bulk delete preview: {str(e)}", ephemeral=True)
    
    async def bulk_delete_nfl_channels_confirm(self, interaction: discord.Interaction):
        """Confirm and execute bulk deletion of NFL channels"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            deleted_channels = []
            deleted_categories = []
            
            # Find all categories that match NFL schedule pattern
            for category in interaction.guild.categories:
                if "NFL Schedule" in category.name:
                    # Delete all channels in the category
                    for channel in category.channels:
                        # DOUBLE SAFETY CHECK: Must have both topic identifier AND name pattern
                        has_bot_topic = channel.topic and "NFL-BOT-CHANNEL" in channel.topic
                        has_week_pattern = channel.name.startswith("week") and "-" in channel.name
                        
                        if has_bot_topic or (has_week_pattern and channel.name.count("-") >= 2):
                            try:
                                await channel.delete(reason="Bulk deleting NFL bot channels")
                                deleted_channels.append(channel.name)
                            except Exception as e:
                                logger.error(f"Error deleting channel {channel.name}: {e}")
                    
                    # Delete the category
                    try:
                        await category.delete(reason="Bulk deleting NFL schedule category")
                        deleted_categories.append(category.name)
                    except Exception as e:
                        logger.error(f"Error deleting category {category.name}: {e}")
            
            # Also find any orphaned channels with NFL-BOT-CHANNEL in topic
            for channel in interaction.guild.channels:
                if hasattr(channel, 'topic') and channel.topic and "NFL-BOT-CHANNEL" in channel.topic:
                    if channel.name not in deleted_channels:
                        try:
                            await channel.delete(reason="Bulk deleting orphaned NFL bot channel")
                            deleted_channels.append(channel.name)
                        except Exception as e:
                            logger.error(f"Error deleting orphaned channel {channel.name}: {e}")
            
            # Clear schedule data
            self.current_week = None
            self.schedule_data = {}
            self.save_schedule_data()
            
            if deleted_channels or deleted_categories:
                await interaction.followup.send(
                    f"🗑️ **BULK DELETE COMPLETED** 🗑️\n"
                    f"✅ Deleted {len(deleted_channels)} channels and {len(deleted_categories)} categories\n"
                    f"📁 Channels: {', '.join(deleted_channels[:10])}{'...' if len(deleted_channels) > 10 else ''}",
                    ephemeral=True
                )
            else:
                await interaction.followup.send("❌ No NFL bot channels found to delete", ephemeral=True)
                
        except Exception as e:
            await interaction.followup.send(f"❌ Error during bulk delete: {str(e)}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(NFLSchedule(bot))
