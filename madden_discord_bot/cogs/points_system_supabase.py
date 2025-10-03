import discord
from discord.ext import commands
from discord import app_commands
import logging
from supabase import create_client, Client
import os
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class PointsSystemSupabase(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Initialize Supabase client
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            logger.error("SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment variables")
            raise ValueError("Supabase credentials not found")
        
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        logger.info("✅ PointsSystemSupabase cog initialized")
    
    async def get_user_points(self, user_id):
        """Get points for a specific user"""
        try:
            result = self.supabase.table("users").select("total_points").eq("id", user_id).execute()
            
            if result.data and len(result.data) > 0:
                return result.data[0]["total_points"]
            else:
                # User doesn't exist, create them with 0 points
                await self.create_user(user_id)
                return 0
        except Exception as e:
            logger.error(f"Error getting user points for {user_id}: {e}")
            return 0
    
    async def create_user(self, user_id, display_name=None, username=None):
        """Create a new user in the database"""
        try:
            user_data = {
                "id": user_id,
                "total_points": 0,
                "stream_points": 0,
                "other_points": 0
            }
            
            if display_name:
                user_data["display_name"] = display_name
            if username:
                user_data["username"] = username
            
            result = self.supabase.table("users").insert(user_data).execute()
            logger.info(f"Created new user {user_id} in database")
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error creating user {user_id}: {e}")
            return None
    
    async def set_user_points(self, user_id, points, display_name=None, username=None):
        """Set points for a specific user"""
        try:
            user_data = {
                "id": user_id,
                "total_points": points
            }
            
            if display_name:
                user_data["display_name"] = display_name
            if username:
                user_data["username"] = username
            
            result = self.supabase.table("users").upsert(user_data).execute()
            return result.data[0] if result.data else None
        except Exception as e:
            logger.error(f"Error setting user points for {user_id}: {e}")
            return None
    
    async def add_user_points(self, user_id, points_to_add, display_name=None, username=None):
        """Add points to a specific user"""
        try:
            current_points = await self.get_user_points(user_id)
            new_points = current_points + points_to_add
            
            await self.set_user_points(user_id, new_points, display_name, username)
            return current_points, new_points
        except Exception as e:
            logger.error(f"Error adding points to user {user_id}: {e}")
            return 0, 0
    
    async def remove_user_points(self, user_id, points_to_remove, display_name=None, username=None):
        """Remove points from a specific user"""
        try:
            current_points = await self.get_user_points(user_id)
            new_points = max(0, current_points - points_to_remove)
            
            await self.set_user_points(user_id, new_points, display_name, username)
            return current_points, new_points
        except Exception as e:
            logger.error(f"Error removing points from user {user_id}: {e}")
            return 0, 0
    
    async def clear_user_points(self, user_id, display_name=None, username=None):
        """Clear points for a specific user"""
        try:
            current_points = await self.get_user_points(user_id)
            await self.set_user_points(user_id, 0, display_name, username)
            return current_points
        except Exception as e:
            logger.error(f"Error clearing points for user {user_id}: {e}")
            return 0
    
    async def get_leaderboard(self, limit=None):
        """Get all users with points, sorted by points (descending)"""
        try:
            query = self.supabase.table("users").select("id, total_points, display_name, username").gt("total_points", 0).order("total_points", desc=True)
            
            if limit:
                query = query.limit(limit)
            
            result = query.execute()
            
            if result.data:
                return [(str(user["id"]), user["total_points"]) for user in result.data]
            else:
                return []
        except Exception as e:
            logger.error(f"Error getting leaderboard: {e}")
            return []
    
    def has_admin_permission(self, interaction):
        """Check if user has commish role or administrator permissions"""
        # Check if user has administrator permission
        if interaction.user.guild_permissions.administrator:
            logger.info(f"Allowing {interaction.user.display_name} to use admin commands (Administrator)")
            return True
        
        # Check if user has commish role
        commish_role = discord.utils.get(interaction.guild.roles, name="commish")
        if commish_role and commish_role in interaction.user.roles:
            logger.info(f"Allowing {interaction.user.display_name} to use admin commands (@commish role)")
            return True
        
        logger.info(f"Denying {interaction.user.display_name} access to admin commands (no @commish role or admin permissions)")
        return False
    
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
            
            # Defer the response immediately to prevent timeout
            await interaction.response.defer()
            
            points = await self.get_user_points(target_user.id)
            
            # Debug logging
            logger.info(f"Checking stats for user {target_user.id} ({target_user.display_name}): {points} points")
            
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
            
            await interaction.followup.send(embed=embed)
            
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
                old_points, new_points = await self.add_user_points(
                    user.id, 
                    points, 
                    user.display_name, 
                    user.name
                )
                results.append(f"• **{user.display_name}**: {old_points:,} → **{new_points:,}** (+{points:,})")
                
                # Debug logging
                logger.info(f"Added {points} points to user {user.id} ({user.display_name}): {old_points} → {new_points}")
            
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
                old_points, new_points = await self.remove_user_points(
                    user.id, 
                    points, 
                    user.display_name, 
                    user.name
                )
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
                old_points = await self.clear_user_points(
                    user.id, 
                    user.display_name, 
                    user.name
                )
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
            
            leaderboard_data = await self.get_leaderboard(limit)
            
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
            
            # Limit to 20 fields (Discord limit)
            max_fields = min(len(leaderboard_data), 20)
            
            for i, (user_id, points) in enumerate(leaderboard_data[:max_fields], 1):
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
            
            # Add note if we truncated the list
            if len(leaderboard_data) > 20:
                embed.add_field(
                    name="",
                    value=f"... and {len(leaderboard_data) - 20} more users",
                    inline=False
                )
            
            # Count users with points > 0 for accurate footer
            try:
                count_result = self.supabase.table("users").select("id", count="exact").gt("total_points", 0).execute()
                users_with_points_count = count_result.count if count_result.count else len(leaderboard_data)
            except:
                users_with_points_count = len(leaderboard_data)
            
            embed.set_footer(text=f"Total users with points: {users_with_points_count}")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in leaderboard: {e}")
            await interaction.followup.send(
                "❌ An error occurred while fetching the leaderboard.", 
                ephemeral=True
            )
    
    @app_commands.command(name="clearstreampoints", description="Clear stream points from a user (Commish only)")
    @app_commands.describe(user="User to clear stream points from")
    async def clear_stream_points(self, interaction: discord.Interaction, user: discord.Member):
        """Clear stream points from a specific user (Commish only)"""
        if not self.has_admin_permission(interaction):
            await interaction.response.send_message(
                "❌ You need administrator permissions or the 'commish' role to use this command.", 
                ephemeral=True
            )
            return
        
        try:
            # Get current stream points and total points
            from config.supabase_config import supabase
            result = supabase.table("users").select("stream_points, total_points").eq("id", str(user.id)).execute()
            
            if not result.data:
                await interaction.response.send_message(
                    f"ℹ️ {user.display_name} doesn't have any points to clear.", 
                    ephemeral=True
                )
                return
            
            current_stream_points = result.data[0].get("stream_points", 0)
            current_total_points = result.data[0].get("total_points", 0)
            
            if current_stream_points == 0:
                await interaction.response.send_message(
                    f"ℹ️ {user.display_name} doesn't have any stream points to clear.", 
                    ephemeral=True
                )
                return
            
            # Calculate new total points (subtract stream points from total)
            new_total_points = current_total_points - current_stream_points
            
            # Update user to have 0 stream points and reduced total points
            supabase.table("users").upsert(
                {
                    "id": str(user.id),
                    "stream_points": 0,
                    "total_points": new_total_points
                },
                on_conflict="id"
            ).execute()
            
            embed = discord.Embed(
                title="🎯 Stream Points Cleared",
                description=f"Successfully cleared stream points for **{user.display_name}**",
                color=0xff6b6b
            )
            embed.add_field(
                name="Stream Points",
                value=f"{current_stream_points} → **0**",
                inline=True
            )
            embed.add_field(
                name="Total Points",
                value=f"{current_total_points:,} → **{new_total_points:,}**",
                inline=True
            )
            embed.set_thumbnail(url=user.display_avatar.url)
            embed.set_footer(text=f"Cleared by {interaction.user.display_name}")
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in clear_stream_points: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while clearing stream points.", 
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(PointsSystemSupabase(bot))
    logger.info("✅ PointsSystemSupabase cog added to bot")
