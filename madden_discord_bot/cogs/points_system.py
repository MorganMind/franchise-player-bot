import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import logging

logger = logging.getLogger(__name__)

class PointsSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.points_file = "data/points.json"
        self.points_data = self.load_points()
        logger.info("✅ PointsSystem cog initialized")
    
    def load_points(self):
        """Load points data from JSON file"""
        try:
            # Create data directory if it doesn't exist
            os.makedirs(os.path.dirname(self.points_file), exist_ok=True)
            
            if os.path.exists(self.points_file):
                with open(self.points_file, 'r') as f:
                    return json.load(f)
            else:
                # Initialize with empty data
                default_data = {"users": {}, "server_settings": {}}
                self.save_points(default_data)
                return default_data
        except Exception as e:
            logger.error(f"Error loading points data: {e}")
            return {"users": {}, "server_settings": {}}
    
    def save_points(self, data=None):
        """Save points data to JSON file"""
        try:
            if data is None:
                data = self.points_data
            
            with open(self.points_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving points data: {e}")
    
    def get_user_points(self, user_id):
        """Get points for a specific user"""
        user_data = self.points_data.get("users", {}).get(str(user_id))
        if user_data and isinstance(user_data, dict):
            return user_data.get("total", 0)
        elif user_data:
            # Handle old format (just a number)
            return user_data
        return 0
    
    def set_user_points(self, user_id, points):
        """Set points for a specific user"""
        if "users" not in self.points_data:
            self.points_data["users"] = {}
        
        # Handle new format
        if str(user_id) not in self.points_data["users"]:
            self.points_data["users"][str(user_id)] = {"total": 0, "stream_points": 0, "other_points": 0}
        
        user_data = self.points_data["users"][str(user_id)]
        if isinstance(user_data, dict):
            user_data["total"] = points
        else:
            # Convert old format to new format
            self.points_data["users"][str(user_id)] = {"total": points, "stream_points": 0, "other_points": 0}
        
        self.save_points()
    
    def add_user_points(self, user_id, points_to_add):
        """Add points to a specific user"""
        current_points = self.get_user_points(user_id)
        new_points = current_points + points_to_add
        self.set_user_points(user_id, new_points)
        return current_points, new_points
    
    def remove_user_points(self, user_id, points_to_remove):
        """Remove points from a specific user"""
        current_points = self.get_user_points(user_id)
        new_points = max(0, current_points - points_to_remove)  # Don't go below 0
        self.set_user_points(user_id, new_points)
        return current_points, new_points
    
    def clear_user_points(self, user_id):
        """Clear points for a specific user"""
        current_points = self.get_user_points(user_id)
        self.set_user_points(user_id, 0)
        return current_points
    
    def get_leaderboard(self, limit=None):
        """Get all users with points, sorted by points (descending)"""
        users = self.points_data.get("users", {})
        
        # Filter out users with 0 points and handle both old and new data formats
        users_with_points = {}
        for user_id, points_data in users.items():
            if isinstance(points_data, dict):
                # New format: {"total": 50, "stream_points": 30, "other_points": 20}
                total_points = points_data.get("total", 0)
            else:
                # Old format: just a number
                total_points = points_data
            
            if total_points > 0:
                users_with_points[user_id] = total_points
        
        sorted_users = sorted(users_with_points.items(), key=lambda x: x[1], reverse=True)
        
        # If limit is specified, apply it
        if limit:
            return sorted_users[:limit]
        return sorted_users
    
    def has_admin_permission(self, interaction):
        """Temporarily allowing all users for testing"""
        logger.info(f"Temporarily allowing {interaction.user.display_name} to use admin commands")
        return True
    
    async def parse_user_mentions(self, interaction, users_string):
        """Parse user mentions from string and return list of member objects"""
        mentioned_users = []
        
        # Debug logging
        logger.info(f"Raw users input: '{users_string}'")
        logger.info(f"Guild: {interaction.guild.name} (ID: {interaction.guild.id})")
        logger.info(f"Guild member count: {interaction.guild.member_count}")
        logger.info(f"Guild members loaded: {len(interaction.guild.members)}")
        
        # Split by spaces and process each mention
        user_mentions = users_string.split()
        logger.info(f"Split mentions: {user_mentions}")
        
        for user_mention in user_mentions:
            logger.info(f"Processing mention: '{user_mention}'")
            
            # Remove < > @ ! characters and get user ID
            clean_id = user_mention.strip('<>@!')
            logger.info(f"Cleaned ID: '{clean_id}'")
            
            if clean_id.isdigit():
                user_id = int(clean_id)
                
                # Try multiple methods to find the user
                # Method 1: Direct guild member lookup
                member = interaction.guild.get_member(user_id)
                if member:
                    mentioned_users.append(member)
                    logger.info(f"✅ Found user via guild.get_member: {member.display_name}")
                    continue
                
                # Method 2: Search through guild members
                for guild_member in interaction.guild.members:
                    if guild_member.id == user_id:
                        mentioned_users.append(guild_member)
                        logger.info(f"✅ Found user via guild members list: {guild_member.display_name}")
                        break
                else:
                    # Method 3: Try to fetch member directly
                    try:
                        member = await interaction.guild.fetch_member(user_id)
                        if member:
                            mentioned_users.append(member)
                            logger.info(f"✅ Found user via guild.fetch_member: {member.display_name}")
                            continue
                    except discord.NotFound:
                        logger.warning(f"User {user_id} is not a member of this guild")
                    except Exception as e:
                        logger.error(f"Error fetching member {user_id}: {e}")
                    
                    # Method 4: Fallback - fetch user and create a mock member for points system
                    try:
                        user = await interaction.client.fetch_user(user_id)
                        if user:
                            logger.info(f"⚠️ Found user via API but not in guild: {user.display_name}")
                            # For the points system, we'll still add them even if not in guild
                            # Create a simple mock member object
                            class MockMember:
                                def __init__(self, user):
                                    self.id = user.id
                                    self.display_name = user.display_name
                                    self.name = user.name
                            
                            mock_member = MockMember(user)
                            mentioned_users.append(mock_member)
                            logger.info(f"✅ Using mock member for points: {mock_member.display_name}")
                    except Exception as e:
                        logger.error(f"Error fetching user {clean_id}: {e}")
            else:
                logger.warning(f"Invalid user ID format: {clean_id}")
        
        logger.info(f"Total users found: {len(mentioned_users)}")
        return mentioned_users
    
    @app_commands.command(name="checkstats", description="Get points of yourself or mentioned user")
    @app_commands.describe(user="User to check points for (optional)")
    async def check_stats(self, interaction: discord.Interaction, user: discord.Member = None):
        """Check points for yourself or another user"""
        try:
            target_user = user or interaction.user
            
            # Reload points data to ensure we have the latest
            self.points_data = self.load_points()
            points = self.get_user_points(target_user.id)
            
            # Debug logging
            logger.info(f"Checking stats for user {target_user.id} ({target_user.display_name}): {points} points")
            logger.info(f"Points data for user {target_user.id}: {self.points_data.get('users', {}).get(str(target_user.id))}")
            
            embed = discord.Embed(
                title="📊 Points Stats",
                color=0x00ff00
            )
            
            embed.add_field(
                name=f"Points for {target_user.display_name}",
                value=f"**{points:,}** points",
                inline=False
            )
            
            embed.set_thumbnail(url=target_user.display_avatar.url)
            embed.set_footer(text=f"User ID: {target_user.id}")
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in check_stats: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ An error occurred while checking stats.", 
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "❌ An error occurred while checking stats.", 
                    ephemeral=True
                )
    
    @app_commands.command(name="addpoints", description="Add points to the mentioned user(s)")
    @app_commands.describe(
        users="Users to add points to (mention multiple users)",
        points="Number of points to add"
    )
    async def add_points(self, interaction: discord.Interaction, users: str, points: int):
        """Add points to mentioned users (Admin/Commish only)"""
        if not self.has_admin_permission(interaction):
            await interaction.response.send_message(
                "❌ You need administrator permissions or the 'commish' role to use this command.", 
                ephemeral=True
            )
            return
        
        if points <= 0:
            await interaction.response.send_message(
                "❌ Points must be a positive number.", 
                ephemeral=True
            )
            return
        
        # Defer the response to extend timeout
        await interaction.response.defer()
        
        try:
            # Parse mentioned users using helper function
            mentioned_users = await self.parse_user_mentions(interaction, users)
            
            if not mentioned_users:
                await interaction.followup.send(
                    "❌ No valid users mentioned. Please mention users with @username.", 
                    ephemeral=True
                )
                return
            
            # Add points to each user
            results = []
            for user in mentioned_users:
                old_points, new_points = self.add_user_points(user.id, points)
                results.append(f"• **{user.display_name}**: {old_points:,} → **{new_points:,}** (+{points:,})")
                
                # Debug logging
                logger.info(f"Added {points} points to user {user.id} ({user.display_name}): {old_points} → {new_points}")
                logger.info(f"Points data after add: {self.points_data.get('users', {}).get(str(user.id))}")
            
            embed = discord.Embed(
                title="✅ Points Added Successfully",
                description=f"Added **{points:,}** points to {len(mentioned_users)} user(s):",
                color=0x00ff00
            )
            
            for result in results:
                embed.add_field(name="", value=result, inline=False)
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in add_points: {e}")
            await interaction.followup.send(
                "❌ An error occurred while adding points.", 
                ephemeral=True
            )
    
    @app_commands.command(name="removepoints", description="Remove points from the mentioned user(s)")
    @app_commands.describe(
        users="Users to remove points from (mention multiple users)",
        points="Number of points to remove"
    )
    async def remove_points(self, interaction: discord.Interaction, users: str, points: int):
        """Remove points from mentioned users (Admin/Commish only)"""
        if not self.has_admin_permission(interaction):
            await interaction.response.send_message(
                "❌ You need administrator permissions or the 'commish' role to use this command.", 
                ephemeral=True
            )
            return
        
        if points <= 0:
            await interaction.response.send_message(
                "❌ Points must be a positive number.", 
                ephemeral=True
            )
            return
        
        # Defer the response to extend timeout
        await interaction.response.defer()
        
        try:
            # Parse mentioned users using helper function
            mentioned_users = await self.parse_user_mentions(interaction, users)
            
            if not mentioned_users:
                await interaction.followup.send(
                    "❌ No valid users mentioned. Please mention users with @username.", 
                    ephemeral=True
                )
                return
            
            # Remove points from each user
            results = []
            for user in mentioned_users:
                old_points, new_points = self.remove_user_points(user.id, points)
                results.append(f"• **{user.display_name}**: {old_points:,} → **{new_points:,}** (-{points:,})")
            
            embed = discord.Embed(
                title="✅ Points Removed Successfully",
                description=f"Removed **{points:,}** points from {len(mentioned_users)} user(s):",
                color=0xff6600
            )
            
            for result in results:
                embed.add_field(name="", value=result, inline=False)
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in remove_points: {e}")
            await interaction.followup.send(
                "❌ An error occurred while removing points.", 
                ephemeral=True
            )
    
    @app_commands.command(name="clearpoints", description="Clear points from the mentioned user(s)")
    @app_commands.describe(users="Users to clear points from (mention multiple users)")
    async def clear_points(self, interaction: discord.Interaction, users: str):
        """Clear points from mentioned users (Admin/Commish only)"""
        if not self.has_admin_permission(interaction):
            await interaction.response.send_message(
                "❌ You need administrator permissions or the 'commish' role to use this command.", 
                ephemeral=True
            )
            return
        
        # Defer the response to extend timeout
        await interaction.response.defer()
        
        try:
            # Parse mentioned users using helper function
            mentioned_users = await self.parse_user_mentions(interaction, users)
            
            if not mentioned_users:
                await interaction.followup.send(
                    "❌ No valid users mentioned. Please mention users with @username.", 
                    ephemeral=True
                )
                return
            
            # Clear points from each user
            results = []
            for user in mentioned_users:
                old_points = self.clear_user_points(user.id)
                results.append(f"• **{user.display_name}**: {old_points:,} → **0** (cleared)")
            
            embed = discord.Embed(
                title="✅ Points Cleared Successfully",
                description=f"Cleared points from {len(mentioned_users)} user(s):",
                color=0xff0000
            )
            
            for result in results:
                embed.add_field(name="", value=result, inline=False)
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in clear_points: {e}")
            await interaction.followup.send(
                "❌ An error occurred while clearing points.", 
                ephemeral=True
            )
    
    @app_commands.command(name="leaderboard", description="Get server's points leaderboard")
    @app_commands.describe(limit="Number of users to show (optional, max 50)")
    async def leaderboard(self, interaction: discord.Interaction, limit: int = None):
        """Show the server's points leaderboard"""
        # Defer the response to prevent timeouts
        await interaction.response.defer()
        
        try:
            # If limit is specified, validate it
            if limit is not None:
                limit = min(max(1, limit), 50)
            
            leaderboard_data = self.get_leaderboard(limit)
            
            if not leaderboard_data:
                embed = discord.Embed(
                    title="📊 Points Leaderboard",
                    description="No users have points yet!",
                    color=0x0099ff
                )
                await interaction.followup.send(embed=embed)
                return
            
            embed = discord.Embed(
                title="📊 Points Leaderboard",
                description=f"All users with points ({len(leaderboard_data)} total):",
                color=0x0099ff
            )
            
            for i, (user_id, points) in enumerate(leaderboard_data, 1):
                # Try to get user from guild cache first (this gives server nickname)
                user = interaction.guild.get_member(int(user_id))
                display_name = None
                
                if user:
                    # Use server nickname (display_name) if available, otherwise use global name
                    display_name = user.display_name
                else:
                    # Try to fetch user from guild (this gives server nickname)
                    try:
                        user = await interaction.guild.fetch_member(int(user_id))
                        if user:
                            display_name = user.display_name
                    except:
                        # Fallback to global name if not in server
                        try:
                            user_obj = await interaction.client.fetch_user(int(user_id))
                            if user_obj:
                                display_name = user_obj.display_name
                        except:
                            display_name = f"User {user_id}"
                
                if display_name:
                    # Add medal emojis for top 3
                    if i == 1:
                        prefix = "🥇"
                    elif i == 2:
                        prefix = "🥈"
                    elif i == 3:
                        prefix = "🥉"
                    else:
                        prefix = f"**{i}.**"
                    
                    embed.add_field(
                        name=f"{prefix} {display_name}",
                        value=f"**{points:,}** points",
                        inline=False
                    )
            
            # Count users with points > 0 for accurate footer
            users_with_points_count = 0
            for user_id, points_data in self.points_data.get("users", {}).items():
                if isinstance(points_data, dict):
                    total_points = points_data.get("total", 0)
                else:
                    total_points = points_data
                if total_points > 0:
                    users_with_points_count += 1
            
            embed.set_footer(text=f"Total users with points: {users_with_points_count}")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in leaderboard: {e}")
            await interaction.followup.send(
                "❌ An error occurred while fetching the leaderboard.", 
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(PointsSystem(bot))
    logger.info("✅ PointsSystem cog added to bot")
