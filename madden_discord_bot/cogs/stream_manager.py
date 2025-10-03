import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import logging
import re
import aiohttp
import time

logger = logging.getLogger(__name__)

class StreamManager(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.streams_file = "data/stream_links.json"
        self.streams_data = self.load_streams()
        
        # Stream cooldown settings (45 minutes = 2700 seconds)
        self.STREAM_COOLDOWN = 2700  # 45 minutes in seconds
        
        # Stream channel settings
        self.stream_channel_file = "data/stream_channel.json"
        self.stream_channel_data = self.load_stream_channel()
        
        # Track active streams
        self.active_streams = {}  # {user_id: stream_info}
        
        logger.info("✅ StreamManager cog initialized")
    
    def load_streams(self):
        """Load stream links data from JSON file"""
        if os.path.exists(self.streams_file):
            try:
                with open(self.streams_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading stream links: {e}")
                return {"users": {}}
        else:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.streams_file), exist_ok=True)
            return {"users": {}}
    
    def save_streams(self):
        """Save stream links data to JSON file"""
        try:
            with open(self.streams_file, 'w') as f:
                json.dump(self.streams_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving stream links: {e}")
    
    def load_stream_channel(self):
        """Load stream channel data from JSON file"""
        if os.path.exists(self.stream_channel_file):
            try:
                with open(self.stream_channel_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading stream channel: {e}")
                return {"guilds": {}}
        else:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.stream_channel_file), exist_ok=True)
            return {"guilds": {}}
    
    def save_stream_channel(self):
        """Save stream channel data to JSON file"""
        try:
            with open(self.stream_channel_file, 'w') as f:
                json.dump(self.stream_channel_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving stream channel: {e}")
    
    def get_stream_channel(self, guild_id):
        """Get designated stream channel for a guild"""
        return self.stream_channel_data.get("guilds", {}).get(str(guild_id))
    
    def set_stream_channel(self, guild_id, channel_id):
        """Set designated stream channel for a guild"""
        if "guilds" not in self.stream_channel_data:
            self.stream_channel_data["guilds"] = {}
        
        self.stream_channel_data["guilds"][str(guild_id)] = channel_id
        self.save_stream_channel()
    
    async def get_user_points(self, user_id):
        """Get user's current points from the Supabase points system"""
        try:
            # Import the points system cog to get points from Supabase
            points_cog = self.bot.get_cog('PointsSystemSupabase')
            if points_cog:
                return await points_cog.get_user_points(user_id)
            else:
                logger.error("PointsSystemSupabase cog not found")
                return 0
        except Exception as e:
            logger.error(f"Error getting user points from Supabase: {e}")
            return 0
    
    def check_stream_cooldown(self, user_id):
        """Check if user is on cooldown for stream points"""
        try:
            points_file = "data/points.json"
            if os.path.exists(points_file):
                with open(points_file, 'r') as f:
                    points_data = json.load(f)
                    
                    # Check point history for recent stream points
                    history = points_data.get("point_history", {}).get(str(user_id), [])
                    current_time = time.time()
                    
                    # Look for the most recent stream point
                    for entry in reversed(history):
                        if entry.get("type") == "stream":
                            last_stream_time = entry.get("timestamp", 0)
                            time_since_last = current_time - last_stream_time
                            
                            if time_since_last < self.STREAM_COOLDOWN:
                                remaining_time = self.STREAM_COOLDOWN - time_since_last
                                return False, remaining_time
                            break
                    
                    return True, 0  # No cooldown
            return True, 0  # No history, no cooldown
        except Exception as e:
            logger.error(f"Error checking stream cooldown: {e}")
            return True, 0  # Error, allow it
    
    async def add_user_points(self, user_id, points_to_add, point_type="stream"):
        """Add points to user's account using Supabase"""
        try:
            # Import the points system cog to add points via Supabase
            points_cog = self.bot.get_cog('PointsSystemSupabase')
            if points_cog:
                # Add points using the Supabase system
                await points_cog.add_user_points(user_id, points_to_add)
                # Get the new total
                new_total = await points_cog.get_user_points(user_id)
                return new_total
            else:
                logger.error("PointsSystemSupabase cog not found")
                return 0
        except Exception as e:
            logger.error(f"Error adding user points via Supabase: {e}")
            return 0
    
    def get_user_stream_link(self, user_id):
        """Get user's registered stream link"""
        return self.streams_data.get("users", {}).get(str(user_id))
    
    def set_user_stream_link(self, user_id, stream_link):
        """Set user's stream link"""
        if "users" not in self.streams_data:
            self.streams_data["users"] = {}
        
        self.streams_data["users"][str(user_id)] = stream_link
        self.save_streams()
    
    def extract_twitch_username(self, twitch_url):
        """Extract Twitch username from various Twitch URL formats"""
        # Handle different Twitch URL formats
        patterns = [
            r'twitch\.tv/([a-zA-Z0-9_]+)',  # twitch.tv/username
            r'twitch\.tv/([a-zA-Z0-9_]+)\?',  # twitch.tv/username?params
            r'twitch\.tv/([a-zA-Z0-9_]+)/',  # twitch.tv/username/
        ]
        
        for pattern in patterns:
            match = re.search(pattern, twitch_url)
            if match:
                return match.group(1)
        
        return None
    
    async def get_twitch_profile_info(self, username):
        """Get Twitch profile information including avatar and details"""
        try:
            # Try multiple Twitch profile image URL formats
            profile_image_urls = [
                f"https://static-cdn.jtvnw.net/jtv_user_pictures/{username}-profile_image-300x300.png",
                f"https://static-cdn.jtvnw.net/jtv_user_pictures/{username}-profile_image-150x150.png",
                f"https://static-cdn.jtvnw.net/jtv_user_pictures/{username}-profile_image-70x70.png"
            ]
            
            # For now, use the first URL format (most common)
            profile_image_url = profile_image_urls[0]
            
            # Log for debugging
            logger.info(f"Generated Twitch profile URL for {username}: {profile_image_url}")
            
            return {
                "username": username,
                "profile_image": profile_image_url,
                "display_name": username,
                "description": f"Twitch streamer {username}"
            }
        except Exception as e:
            logger.error(f"Error getting Twitch profile info: {e}")
            return {
                "username": username,
                "profile_image": None,
                "display_name": username,
                "description": f"Twitch streamer {username}"
            }
    
    @app_commands.command(name="addstream", description="Add your Twitch stream link")
    @app_commands.describe(stream_link="Your Twitch stream URL (e.g., https://twitch.tv/yourusername)")
    async def add_stream(self, interaction: discord.Interaction, stream_link: str):
        """Add user's Twitch stream link"""
        try:
            # Validate Twitch URL
            if "twitch.tv" not in stream_link.lower():
                await interaction.response.send_message(
                    "❌ Please provide a valid Twitch URL (e.g., https://twitch.tv/yourusername)",
                    ephemeral=True
                )
                return
            
            # Extract username
            username = self.extract_twitch_username(stream_link)
            if not username:
                await interaction.response.send_message(
                    "❌ Could not extract Twitch username from the provided URL. Please check the format.",
                    ephemeral=True
                )
                return
            
            # Get Twitch profile info
            profile_info = await self.get_twitch_profile_info(username)
            
            # Store the stream link
            self.set_user_stream_link(interaction.user.id, stream_link)
            
            embed = discord.Embed(
                title="✅ Stream Link Added!",
                description=f"Your Twitch stream link has been registered.",
                color=0x00ff00
            )
            
            embed.add_field(
                name="Twitch Username",
                value=f"**{profile_info['display_name']}**",
                inline=True
            )
            
            embed.add_field(
                name="Stream Link",
                value=f"[{stream_link}]({stream_link})",
                inline=True
            )
            
            embed.add_field(
                name="Next Steps",
                value="Use `/streamgame` to start streaming and earn points!",
                inline=False
            )
            
            # Add profile image if available
            if profile_info['profile_image']:
                logger.info(f"Setting thumbnail for {username}: {profile_info['profile_image']}")
                embed.set_thumbnail(url=profile_info['profile_image'])
            else:
                logger.warning(f"No profile image available for {username}")
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in add_stream: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while adding your stream link.",
                ephemeral=True
            )
    
    @app_commands.command(name="streamgame", description="Start streaming and earn points!")
    async def stream_game(self, interaction: discord.Interaction):
        """Start streaming and post stream link"""
        try:
            # Check if user has a registered stream link
            stream_link = self.get_user_stream_link(interaction.user.id)
            
            if not stream_link:
                await interaction.response.send_message(
                    "❌ You don't have a registered stream link!\n\n"
                    "**To register your stream:**\n"
                    "1. Use `/addstream` with your Twitch URL\n"
                    "2. Or paste your Twitch link here and I'll store it for next time\n\n"
                    "**Example:** `/addstream https://twitch.tv/yourusername`",
                    ephemeral=True
                )
                return
            
            # Extract username for display
            username = self.extract_twitch_username(stream_link)
            
            # Get Twitch profile info
            profile_info = await self.get_twitch_profile_info(username)
            
            # Check stream cooldown
            can_stream, remaining_time = self.check_stream_cooldown(interaction.user.id)
            
            if not can_stream:
                minutes_remaining = int(remaining_time // 60)
                seconds_remaining = int(remaining_time % 60)
                await interaction.response.send_message(
                    f"⏰ **Stream Cooldown Active!**\n\n"
                    f"You can earn stream points again in **{minutes_remaining}m {seconds_remaining}s**.\n\n"
                    f"Stream points have a 45-minute cooldown to prevent spam.",
                    ephemeral=True
                )
                return
            
            # Add points for streaming
            points_earned = 1
            new_total = await self.add_user_points(interaction.user.id, points_earned, "stream")
            
            # Create stream announcement embed
            embed = discord.Embed(
                title="🎮 Live Stream Started!",
                description=f"**{interaction.user.display_name}** is now streaming Madden!",
                color=0x9146ff,  # Twitch purple
                url=stream_link
            )
            
            embed.add_field(
                name="🎯 Streamer",
                value=f"**{profile_info['display_name']}**",
                inline=True
            )
            
            embed.add_field(
                name="💰 Points Earned",
                value=f"+{points_earned} point",
                inline=True
            )
            
            embed.add_field(
                name="📺 Watch Now",
                value=f"[Click here to watch!]({stream_link})",
                inline=False
            )
            
            # Add Twitch profile image
            if profile_info['profile_image']:
                logger.info(f"Setting stream thumbnail for {username}: {profile_info['profile_image']}")
                embed.set_thumbnail(url=profile_info['profile_image'])
            else:
                logger.warning(f"No profile image available for {username}, using fallback")
                embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1009146ff.png")  # Twitch emoji fallback
            
            embed.set_footer(text=f"Total Points: {new_total:,}")
            
            # Post in the current channel
            await interaction.response.send_message(embed=embed)
            
            # Cross-post to designated stream channel if different from current channel
            designated_channel_id = self.get_stream_channel(interaction.guild.id)
            if designated_channel_id and designated_channel_id != interaction.channel.id:
                try:
                    designated_channel = interaction.guild.get_channel(int(designated_channel_id))
                    if designated_channel:
                        # Create a slightly different embed for the designated channel
                        cross_post_embed = discord.Embed(
                            title="🎮 Live Stream Started!",
                            description=f"**{interaction.user.display_name}** is now streaming Madden!",
                            color=0x9146ff,
                            url=stream_link
                        )
                        
                        cross_post_embed.add_field(
                            name="🎯 Streamer",
                            value=f"**{profile_info['display_name']}**",
                            inline=True
                        )
                        
                        cross_post_embed.add_field(
                            name="📺 Watch Now",
                            value=f"[Click here to watch!]({stream_link})",
                            inline=False
                        )
                        
                        if profile_info['profile_image']:
                            logger.info(f"Setting cross-post thumbnail for {username}: {profile_info['profile_image']}")
                            cross_post_embed.set_thumbnail(url=profile_info['profile_image'])
                        else:
                            logger.warning(f"No profile image available for {username} in cross-post")
                            cross_post_embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1009146ff.png")
                        
                        cross_post_embed.set_footer(text=f"Originally posted in #{interaction.channel.name}")
                        
                        await designated_channel.send(embed=cross_post_embed)
                        
                except Exception as e:
                    logger.error(f"Error cross-posting to designated channel: {e}")
            
        except Exception as e:
            logger.error(f"Error in stream_game: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while starting your stream.",
                ephemeral=True
            )
    
    @app_commands.command(name="mystream", description="View your registered stream link")
    async def my_stream(self, interaction: discord.Interaction):
        """Show user's registered stream link"""
        try:
            stream_link = self.get_user_stream_link(interaction.user.id)
            
            if not stream_link:
                embed = discord.Embed(
                    title="📺 Your Stream Link",
                    description="You don't have a registered stream link yet.",
                    color=0xff6600
                )
                
                embed.add_field(
                    name="How to Register",
                    value="Use `/addstream` with your Twitch URL to register your stream link.",
                    inline=False
                )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            username = self.extract_twitch_username(stream_link)
            
            # Get Twitch profile info
            profile_info = await self.get_twitch_profile_info(username)
            
            embed = discord.Embed(
                title="📺 Your Stream Link",
                description="Your registered Twitch stream link:",
                color=0x9146ff
            )
            
            embed.add_field(
                name="Twitch Username",
                value=f"**{profile_info['display_name']}**",
                inline=True
            )
            
            embed.add_field(
                name="Stream Link",
                value=f"[{stream_link}]({stream_link})",
                inline=True
            )
            
            embed.add_field(
                name="Quick Action",
                value="Use `/streamgame` to start streaming and earn points!",
                inline=False
            )
            
            # Add profile image if available
            if profile_info['profile_image']:
                logger.info(f"Setting mystream thumbnail for {username}: {profile_info['profile_image']}")
                embed.set_thumbnail(url=profile_info['profile_image'])
            else:
                logger.warning(f"No profile image available for {username} in mystream")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in my_stream: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while fetching your stream link.",
                ephemeral=True
            )
    
    @app_commands.command(name="setstreamchannel", description="Set the designated stream announcement channel (Admin)")
    @app_commands.describe(channel_name="The name of the channel (e.g., 'general' or 'streams')")
    async def set_stream_channel_command(self, interaction: discord.Interaction, channel_name: str):
        """Set designated stream channel for the server"""
        try:
            # Temporarily allowing all users (as requested)
            # if not interaction.user.guild_permissions.administrator:
            #     await interaction.response.send_message(
            #         "❌ You need administrator permissions to set the stream channel.",
            #         ephemeral=True
            #     )
            #     return
            
            # Search for channel by name
            channel = None
            for guild_channel in interaction.guild.channels:
                if (isinstance(guild_channel, discord.TextChannel) and 
                    guild_channel.name.lower() == channel_name.lower()):
                    channel = guild_channel
                    break
            
            if not channel:
                # Try partial match
                for guild_channel in interaction.guild.channels:
                    if (isinstance(guild_channel, discord.TextChannel) and 
                        channel_name.lower() in guild_channel.name.lower()):
                        channel = guild_channel
                        break
            
            if not channel:
                await interaction.response.send_message(
                    f"❌ **Channel Not Found**\n\n"
                    f"Could not find a channel named: `{channel_name}`\n\n"
                    "**Try:**\n"
                    "• Use `/listchannels` to see available channels\n"
                    "• Use `/setstreamchannelid` with the channel ID\n"
                    "• Check the spelling of the channel name",
                    ephemeral=True
                )
                return
            
            # Log the channel info for debugging
            logger.info(f"Setting stream channel: {channel.name} (ID: {channel.id}) in guild {interaction.guild.name}")
            
            # Set the stream channel
            self.set_stream_channel(interaction.guild.id, channel.id)
            
            embed = discord.Embed(
                title="✅ Stream Channel Set!",
                description=f"Stream announcements will now be cross-posted to {channel.mention}",
                color=0x00ff00
            )
            
            embed.add_field(
                name="Current Stream Channel",
                value=f"**#{channel.name}**",
                inline=True
            )
            
            embed.add_field(
                name="Channel ID",
                value=f"`{channel.id}`",
                inline=True
            )
            
            embed.add_field(
                name="How It Works",
                value="When someone uses `/streamgame`, the announcement will:\n"
                      "1. Post in the channel where the command was used\n"
                      "2. Cross-post to this designated channel (if different)",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in set_stream_channel: {e}")
            
            # Check if it's a transformer error (emoji issue)
            if "TransformerError" in str(type(e)) or "Failed to convert" in str(e):
                await interaction.response.send_message(
                    "❌ **Channel Selection Error**\n\n"
                    "Discord had trouble selecting that channel. This can happen with channels that have emojis in their names.\n\n"
                    "**Solutions:**\n"
                    "• Try selecting the channel from the dropdown instead of typing\n"
                    "• Or mention the channel directly: #channel-name\n"
                    "• Or use `/streamchannel` to see the current setting",
                    ephemeral=True
                )
            else:
                await interaction.response.send_message(
                    "❌ An error occurred while setting the stream channel.",
                    ephemeral=True
                )
    
    @app_commands.command(name="setstreamchannelid", description="Set stream channel using channel ID")
    @app_commands.describe(channel_id="The ID of the channel (enable Developer Mode, then right-click channel > Copy ID)")
    async def set_stream_channel_by_id(self, interaction: discord.Interaction, channel_id: str):
        """Set designated stream channel using channel ID (works better with emoji channels)"""
        try:
            # Validate channel ID format
            if not channel_id.isdigit():
                await interaction.response.send_message(
                    "❌ **Invalid Channel ID**\n\n"
                    "Please provide a valid channel ID (numbers only).\n\n"
                    "**How to get Channel ID:**\n"
                    "1. Enable Developer Mode in Discord Settings → Advanced\n"
                    "2. Right-click on the channel\n"
                    "3. Select 'Copy ID'\n"
                    "4. Paste the ID here",
                    ephemeral=True
                )
                return
            
            # Debug logging
            logger.info(f"Looking for channel ID: {channel_id} in guild: {interaction.guild.name} (ID: {interaction.guild.id})")
            logger.info(f"Bot can see {len(interaction.guild.channels)} channels in this guild")
            
            # Try to get the channel using multiple methods
            channel = None
            
            # Method 1: Direct guild lookup
            channel = interaction.guild.get_channel(int(channel_id))
            
            # Method 2: Search through all channels if Method 1 fails
            if not channel:
                for guild_channel in interaction.guild.channels:
                    if guild_channel.id == int(channel_id) and isinstance(guild_channel, discord.TextChannel):
                        channel = guild_channel
                        logger.info(f"Found channel via search: {channel.name}")
                        break
            
            # Method 3: Try to fetch channel directly if still not found
            if not channel:
                try:
                    channel = await interaction.guild.fetch_channel(int(channel_id))
                    if not isinstance(channel, discord.TextChannel):
                        channel = None
                        logger.warning(f"Channel {channel_id} is not a text channel")
                except Exception as e:
                    logger.warning(f"Could not fetch channel {channel_id}: {e}")
            
            if not channel:
                # List available channels for debugging
                available_channels = [f"{c.name} (ID: {c.id})" for c in interaction.guild.channels if isinstance(c, discord.TextChannel)]
                logger.warning(f"Channel {channel_id} not found. Available text channels: {available_channels}")
                
                await interaction.response.send_message(
                    f"❌ **Channel Not Found**\n\n"
                    f"Could not find a channel with ID: `{channel_id}`\n\n"
                    f"**Debug Info:**\n"
                    f"• Guild: {interaction.guild.name}\n"
                    f"• Bot can see {len(interaction.guild.channels)} channels\n"
                    f"• Available text channels: {len([c for c in interaction.guild.channels if isinstance(c, discord.TextChannel)])}\n\n"
                    "**Possible Issues:**\n"
                    "• Channel might be in a different server\n"
                    "• Bot might not have permission to see the channel\n"
                    "• Channel ID might be incorrect\n\n"
                    "Try using `/streamchannel` to see current setting.",
                    ephemeral=True
                )
                return
            
            # Check if it's a text channel
            if not isinstance(channel, discord.TextChannel):
                await interaction.response.send_message(
                    f"❌ **Invalid Channel Type**\n\n"
                    f"The channel `{channel.name}` is not a text channel.\n\n"
                    "Please select a text channel for stream announcements.",
                    ephemeral=True
                )
                return
            
            # Log the channel info for debugging
            logger.info(f"Setting stream channel by ID: {channel.name} (ID: {channel.id}) in guild {interaction.guild.name}")
            
            # Set the stream channel
            self.set_stream_channel(interaction.guild.id, channel.id)
            
            embed = discord.Embed(
                title="✅ Stream Channel Set!",
                description=f"Stream announcements will now be cross-posted to {channel.mention}",
                color=0x00ff00
            )
            
            embed.add_field(
                name="Channel Set",
                value=f"**{channel.name}**",
                inline=True
            )
            
            embed.add_field(
                name="Channel ID",
                value=f"`{channel.id}`",
                inline=True
            )
            
            embed.add_field(
                name="How It Works",
                value="When someone uses `/streamgame`, the announcement will:\n"
                      "1. Post in the channel where the command was used\n"
                      "2. Cross-post to this designated channel (if different)",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed)
            
        except ValueError:
            await interaction.response.send_message(
                "❌ **Invalid Channel ID Format**\n\n"
                "The channel ID must be a number.",
                ephemeral=True
            )
        except Exception as e:
            logger.error(f"Error in set_stream_channel_by_id: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while setting the stream channel.",
                ephemeral=True
                            )
    
    @app_commands.command(name="listchannels", description="List all channels the bot can see (Debug)")
    async def list_channels(self, interaction: discord.Interaction):
        """List all channels the bot can see for debugging"""
        try:
            # Debug guild information
            logger.info(f"Guild info: {interaction.guild.name} (ID: {interaction.guild.id})")
            logger.info(f"Bot member: {interaction.guild.me.display_name if interaction.guild.me else 'Not found'}")
            logger.info(f"Bot permissions: {interaction.guild.me.guild_permissions if interaction.guild.me else 'No permissions'}")
            logger.info(f"Total channels: {len(interaction.guild.channels)}")
            
            text_channels = [c for c in interaction.guild.channels if isinstance(c, discord.TextChannel)]
            
            embed = discord.Embed(
                title="📋 Available Text Channels",
                description=f"Bot can see {len(text_channels)} text channels in {interaction.guild.name}:",
                color=0x0099ff
            )
            
            # Group channels by category
            channels_by_category = {}
            for channel in text_channels:
                category_name = channel.category.name if channel.category else "No Category"
                if category_name not in channels_by_category:
                    channels_by_category[category_name] = []
                channels_by_category[category_name].append(channel)
            
            for category, channels in channels_by_category.items():
                channel_list = []
                for channel in channels:
                    channel_list.append(f"• **#{channel.name}** (ID: `{channel.id}`)")
                
                embed.add_field(
                    name=f"📁 {category}",
                    value="\n".join(channel_list),
                    inline=False
                )
            
            embed.set_footer(text=f"Total: {len(text_channels)} text channels")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in list_channels: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while listing channels.",
                ephemeral=True
            )
    
    @app_commands.command(name="streamchannel", description="View the current designated stream channel")
    async def view_stream_channel(self, interaction: discord.Interaction):
        """View the current designated stream channel"""
        try:
            channel_id = self.get_stream_channel(interaction.guild.id)
            
            if not channel_id:
                embed = discord.Embed(
                    title="📺 Stream Channel",
                    description="No designated stream channel has been set.",
                    color=0xff6600
                )
                
                embed.add_field(
                    name="How to Set",
                    value="Use `/setstreamchannel` to designate a channel for stream announcements.",
                    inline=False
                )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            channel = interaction.guild.get_channel(int(channel_id))
            
            if not channel:
                embed = discord.Embed(
                    title="📺 Stream Channel",
                    description="The designated stream channel no longer exists.",
                    color=0xff0000
                )
                
                embed.add_field(
                    name="Channel ID",
                    value=f"`{channel_id}`",
                    inline=True
                )
                
                embed.add_field(
                    name="Action Required",
                    value="Use `/setstreamchannel` to set a new stream channel.",
                    inline=False
                )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            embed = discord.Embed(
                title="📺 Stream Channel",
                description=f"Current designated stream channel:",
                color=0x9146ff
            )
            
            embed.add_field(
                name="Channel",
                value=f"**#{channel.name}**",
                inline=True
            )
            
            embed.add_field(
                name="Channel ID",
                value=f"`{channel.id}`",
                inline=True
            )
            
            embed.add_field(
                name="How It Works",
                value="Stream announcements will be cross-posted to this channel when users use `/streamgame`.",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in view_stream_channel: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while fetching the stream channel.",
                ephemeral=True
            )
    
    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        """Detect when a user starts or stops streaming"""
        try:
            # Check if streaming status changed
            was_streaming = before.activity and isinstance(before.activity, discord.Streaming)
            is_streaming = after.activity and isinstance(after.activity, discord.Streaming)
            
            if not was_streaming and is_streaming:
                # User started streaming
                await self.handle_stream_start(after)
            elif was_streaming and not is_streaming:
                # User stopped streaming
                await self.handle_stream_stop(after)
                
        except Exception as e:
            logger.error(f"Error in on_member_update: {e}")
    
    async def handle_stream_start(self, member):
        """Handle when a user starts streaming"""
        try:
            logger.info(f"User {member.display_name} started streaming: {member.activity.name if member.activity else 'Unknown'}")
            
            # Check if user has registered stream link
            stream_link = self.get_user_stream_link(member.id)
            if not stream_link:
                logger.info(f"User {member.display_name} is streaming but has no registered stream link")
                return
            
            # Check cooldown
            can_stream, remaining_time = self.check_stream_cooldown(member.id)
            if not can_stream:
                logger.info(f"User {member.display_name} is on cooldown, skipping auto-announcement")
                return
            
            # Add points for streaming
            points_earned = 1
            new_total = await self.add_user_points(member.id, points_earned, "stream")
            
            # Store active stream info
            self.active_streams[member.id] = {
                "started_at": time.time(),
                "activity": member.activity.name if member.activity else "Unknown",
                "guild_id": member.guild.id
            }
            
            # Get Twitch profile info
            username = self.extract_twitch_username(stream_link)
            profile_info = await self.get_twitch_profile_info(username)
            
            # Create stream announcement embed
            embed = discord.Embed(
                title="🎮 Live Stream Detected!",
                description=f"**{member.display_name}** is now streaming!",
                color=0x9146ff,
                url=stream_link
            )
            
            embed.add_field(
                name="🎯 Streamer",
                value=f"**{profile_info['display_name']}**",
                inline=True
            )
            
            embed.add_field(
                name="💰 Points Earned",
                value=f"+{points_earned} point",
                inline=True
            )
            
            embed.add_field(
                name="📺 Watch Now",
                value=f"[Click here to watch!]({stream_link})",
                inline=False
            )
            
            if profile_info['profile_image']:
                embed.set_thumbnail(url=profile_info['profile_image'])
            else:
                embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1009146ff.png")
            
            embed.set_footer(text=f"Total Points: {new_total:,} | Auto-detected")
            
            # Post in designated stream channel if set
            designated_channel_id = self.get_stream_channel(member.guild.id)
            if designated_channel_id:
                try:
                    designated_channel = member.guild.get_channel(int(designated_channel_id))
                    if designated_channel:
                        await designated_channel.send(embed=embed)
                        logger.info(f"Auto-announced stream for {member.display_name} in {designated_channel.name}")
                except Exception as e:
                    logger.error(f"Error posting auto-announcement: {e}")
            
        except Exception as e:
            logger.error(f"Error handling stream start: {e}")
    
    async def handle_stream_stop(self, member):
        """Handle when a user stops streaming"""
        try:
            logger.info(f"User {member.display_name} stopped streaming")
            
            # Remove from active streams
            if member.id in self.active_streams:
                stream_info = self.active_streams.pop(member.id)
                duration = time.time() - stream_info["started_at"]
                logger.info(f"Stream ended for {member.display_name} after {duration:.0f} seconds")
            
        except Exception as e:
            logger.error(f"Error handling stream stop: {e}")
    
    @app_commands.command(name="streamdiscord", description="Verify you're streaming in Discord and earn points!")
    async def stream_discord(self, interaction: discord.Interaction):
        """Verify user is streaming in Discord and give points"""
        try:
            # Debug logging
            logger.info(f"User {interaction.user.display_name} used /streamdiscord")
            logger.info(f"User activity: {interaction.user.activity}")
            logger.info(f"Activity type: {type(interaction.user.activity)}")
            logger.info(f"Is streaming: {isinstance(interaction.user.activity, discord.Streaming)}")
            
            # Check if user is currently streaming in Discord (Go Live) OR screen sharing
            is_streaming_activity = interaction.user.activity and isinstance(interaction.user.activity, discord.Streaming)
            is_screen_sharing = False
            
            # Check if user is in a voice channel and screen sharing
            if interaction.user.voice:
                voice_state = interaction.user.voice
                # Check if user is screen sharing (self_video is True when screen sharing)
                is_screen_sharing = voice_state.self_video or voice_state.self_stream
            
            # User must be either streaming (Go Live) OR screen sharing
            if not is_streaming_activity and not is_screen_sharing:
                await interaction.response.send_message(
                    "❌ **Not Streaming in Discord**\n\n"
                    "You need to be streaming in Discord to use this command.\n\n"
                    "**How to stream in Discord:**\n"
                    "1. Join a voice channel\n"
                    "2. Click 'Go Live' (for streaming) OR 'Screen Share' (for sharing)\n"
                    "3. Start your stream/screen share\n"
                    "4. Then use this command again\n\n"
                    "**Note:** Both 'Go Live' and 'Screen Share' work with this command!",
                    ephemeral=True
                )
                return
            
            # Check stream cooldown
            can_stream, remaining_time = self.check_stream_cooldown(interaction.user.id)
            
            if not can_stream:
                minutes_remaining = int(remaining_time // 60)
                seconds_remaining = int(remaining_time % 60)
                await interaction.response.send_message(
                    f"⏰ **Stream Cooldown Active!**\n\n"
                    f"You can earn stream points again in **{minutes_remaining}m {seconds_remaining}s**.\n\n"
                    f"Stream points have a 45-minute cooldown to prevent spam.",
                    ephemeral=True
                )
                return
            
            # Add points for streaming
            points_earned = 1
            new_total = await self.add_user_points(interaction.user.id, points_earned, "stream")
            
            # Get stream info
            stream_activity = interaction.user.activity
            stream_name = stream_activity.name if stream_activity else "Unknown"
            stream_url = stream_activity.url if stream_activity else None
            
            # Determine what type of streaming they're doing
            if is_streaming_activity:
                stream_type = "Go Live Stream"
                stream_description = f"**{interaction.user.display_name}** is now streaming in Discord!"
            else:
                stream_type = "Screen Share"
                stream_description = f"**{interaction.user.display_name}** is now screen sharing in Discord!"
            
            # Create verification embed (similar to Twitch stream style)
            embed = discord.Embed(
                title="🎮 Live Stream Started!",
                description=stream_description,
                color=0x9146ff,  # Discord purple
                url=stream_url
            )
            
            embed.add_field(
                name="🎯 Streamer",
                value=f"**{interaction.user.display_name}**",
                inline=True
            )
            
            embed.add_field(
                name="📺 Stream Type",
                value=f"**{stream_type}**",
                inline=True
            )
            
            embed.add_field(
                name="💰 Points Earned",
                value=f"+{points_earned} point",
                inline=True
            )
            
            embed.add_field(
                name="📺 Watch Now",
                value=f"[Click here to watch!](https://discord.com/channels/1039342526206844980/1167311841668632607)",
                inline=False
            )
            
            # Try to get Twitch profile photo if user has registered stream link
            stream_link = self.get_user_stream_link(interaction.user.id)
            if stream_link:
                username = self.extract_twitch_username(stream_link)
                if username:
                    profile_info = await self.get_twitch_profile_info(username)
                    if profile_info['profile_image']:
                        embed.set_thumbnail(url=profile_info['profile_image'])
                        logger.info(f"Using Twitch profile photo for {username}: {profile_info['profile_image']}")
                    else:
                        embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1009146ff.png")
                        logger.warning(f"No Twitch profile image available for {username}")
                else:
                    embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1009146ff.png")
            else:
                # No registered stream link, use Discord icon
                embed.set_thumbnail(url="https://cdn.discordapp.com/emojis/1009146ff.png")
            
            embed.set_footer(text=f"Total Points: {new_total:,}")
            
            # Post in designated stream channel if set
            designated_channel_id = self.get_stream_channel(interaction.guild.id)
            if designated_channel_id and designated_channel_id != interaction.channel.id:
                try:
                    designated_channel = interaction.guild.get_channel(int(designated_channel_id))
                    if designated_channel:
                        # Create cross-post embed
                        cross_post_embed = discord.Embed(
                            title="🎮 Discord Stream Started!",
                            description=f"**{interaction.user.display_name}** is streaming in Discord!",
                            color=0x9146ff,
                            url=stream_url
                        )
                        
                        cross_post_embed.add_field(
                            name="🎮 Stream Activity",
                            value=f"**{stream_name}**",
                            inline=True
                        )
                        
                        cross_post_embed.add_field(
                            name="📺 Watch Now",
                            value=f"[Click here to watch!](https://discord.com/channels/1039342526206844980/1167311841668632607)",
                            inline=False
                        )
                        
                        cross_post_embed.set_footer(text=f"Originally posted in #{interaction.channel.name}")
                        
                        await designated_channel.send(embed=cross_post_embed)
                        
                except Exception as e:
                    logger.error(f"Error cross-posting Discord stream: {e}")
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in stream_discord: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while verifying your Discord stream.",
                ephemeral=True
            )
    
    @app_commands.command(name="activestreams", description="Show currently active streams")
    async def active_streams_command(self, interaction: discord.Interaction):
        """Show currently active streams"""
        try:
            if not self.active_streams:
                embed = discord.Embed(
                    title="📺 Active Streams",
                    description="No active streams detected.",
                    color=0xff6600
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            embed = discord.Embed(
                title="📺 Active Streams",
                description=f"Currently detecting {len(self.active_streams)} active stream(s):",
                color=0x9146ff
            )
            
            for user_id, stream_info in self.active_streams.items():
                try:
                    user = interaction.guild.get_member(user_id)
                    if user:
                        stream_link = self.get_user_stream_link(user_id)
                        duration = time.time() - stream_info["started_at"]
                        
                        embed.add_field(
                            name=f"🎮 {user.display_name}",
                            value=f"**Activity:** {stream_info['activity']}\n"
                                  f"**Duration:** {duration:.0f}s\n"
                                  f"**Link:** {stream_link if stream_link else 'Not registered'}",
                            inline=False
                        )
                except Exception as e:
                    logger.error(f"Error processing active stream for {user_id}: {e}")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Error in active_streams: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while fetching active streams.",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(StreamManager(bot))
    logger.info("✅ StreamManager cog added to bot")
