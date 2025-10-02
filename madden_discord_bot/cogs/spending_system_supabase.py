import discord
from discord.ext import commands
from discord import app_commands
import logging
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class SpendingSystemSupabase(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # Initialize Supabase client
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            logger.error("SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment variables")
            raise ValueError("Supabase credentials not found")
        
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        
        # Position and attribute definitions
        # Expanded positions for dropdown selection
        self.POSITIONS = [
            "QB", "RB", "WR", "TE",
            "LT/RT", "LG/RG", "C",
            "Edge", "LB", "CB", "S",
            "FB", "K", "P"
        ]
        # Attribute definitions per position. Each entry is (Display Name, Code)
        self.ATTRIBUTES = {
            "QB": [
                ("Throw Accuracy Short", "SAC"),
                ("Throw Accuracy Medium", "MAC"),
                ("Throw Accuracy Deep", "DAC"),
                ("Throw on the Run", "RUN"),
                ("Play Action", "PAC"),
                ("Throw Under Pressure", "TUP"),
                ("Awareness", "AWR"),
                ("Break Sack", "BSK"),
                ("Carrying", "CAR"),
            ],
            "RB": [
                ("Carrying", "CAR"),("Ball Carrier Vision", "BCV"),("Stiff Arm", "SFA"),("Spin Move", "SPM"),
                ("Juke Move", "JKM"),("Trucking", "TRK"),("Break Tackle", "BTK"),("Catching", "CTH"),
                ("Catch in Traffic", "CIT"),("Short Route Running", "SRR"),("Medium Route Running", "MRR"),
                ("Release", "RLS"),("Awareness", "AWR")
            ],
            "WR": [
                ("Catching", "CTH"),("Catch in Traffic", "CIT"),("Spectacular Catch", "SPC"),("Release", "RLS"),
                ("Short Route Running", "SRR"),("Medium Route Running", "MRR"),("Deep Route Running", "DRR"),
                ("Awareness", "AWR")
            ],
            "TE": [
                ("Catching", "CTH"),("Catch in Traffic", "CIT"),("Spectacular Catch", "SPC"),("Release", "RLS"),
                ("Short Route Running", "SRR"),("Medium Route Running", "MRR"),("Run Block", "RBK"),
                ("Pass Block", "PBK"),("Lead Block", "LBK"),("Impact Block", "IBK"),("Awareness", "AWR")
            ],
            "LT/RT": [
                ("Pass Block", "PBK"),("Pass Block Power", "PBP"),("Pass Block Finesse", "PBF"),("Run Block", "RBK"),
                ("Run Block Power", "RBP"),("Run Block Finesse", "RBF"),("Lead Block", "LBK"),("Impact Block", "IBK"),
                ("Awareness", "AWR")
            ],
            "LG/RG": [
                ("Pass Block", "PBK"),("Pass Block Power", "PBP"),("Pass Block Finesse", "PBF"),("Run Block", "RBK"),
                ("Run Block Power", "RBP"),("Run Block Finesse", "RBF"),("Lead Block", "LBK"),("Impact Block", "IBK"),
                ("Awareness", "AWR")
            ],
            "C": [
                ("Pass Block", "PBK"),("Pass Block Power", "PBP"),("Pass Block Finesse", "PBF"),("Run Block", "RBK"),
                ("Run Block Power", "RBP"),("Run Block Finesse", "RBF"),("Lead Block", "LBK"),("Impact Block", "IBK"),
                ("Awareness", "AWR")
            ],
            "Edge": [
                ("Finesse Moves", "FMV"),("Power Moves", "PMV"),("Block Shedding", "BSH"),("Tackling", "TAK"),
                ("Play Recognition", "PRC"),("Pursuit", "PUR"),("Awareness", "AWR")
            ],
            "LB": [
                ("Tackling", "TAK"),("Play Recognition", "PRC"),("Block Shedding", "BSH"),("Pursuit", "PUR"),
                ("Awareness", "AWR"),("Finesse Moves", "FMV"),("Power Moves", "PMV"),("Zone Coverage", "ZCV"),
                ("Man Coverage", "MCV"),("Catching", "CTH")
            ],
            "CB": [
                ("Man Coverage", "MCV"),("Zone Coverage", "ZCV"),("Press", "PRS"),("Play Recognition", "PRC"),
                ("Awareness", "AWR"),("Catching", "CTH"),("Catch in Traffic", "CIT"),("Pursuit", "PUR")
            ],
            "S": [
                ("Zone Coverage", "ZCV"),("Man Coverage", "MCV"),("Play Recognition", "PRC"),("Pursuit", "PUR"),
                ("Awareness", "AWR"),("Catching", "CTH"),("Catch in Traffic", "CIT"),("Tackling", "TAK")
            ],
            "FB": [
                ("Run Block", "RBK"),("Lead Block", "LBK"),("Impact Block", "IBK"),("Catching", "CTH"),
                ("Catch in Traffic", "CIT"),("Short Route Running", "SRR"),("Trucking", "TRK"),("Stiff Arm", "SFA"),
                ("Carrying", "CAR"),("Awareness", "AWR")
            ],
            "K": [
                ("Kick Accuracy", "KAC"),("Awareness", "AWR")
            ],
            "P": [
                ("Kick Accuracy", "KAC"),("Awareness", "AWR")
            ],
        }
        
        # Cost per attribute point
        self.ATTRIBUTE_COST = 1  # 1 point per +1 attribute
        
        logger.info("✅ SpendingSystemSupabase cog initialized")
    
    async def attribute_autocomplete(self, interaction: discord.Interaction, current: str):
        """Autocomplete provider for the attribute option, dependent on selected position."""
        try:
            # Retrieve the selected position value from interaction namespace if present
            selected_position = None
            if interaction.namespace and hasattr(interaction.namespace, 'position'):
                pos = interaction.namespace.position
                selected_position = pos.value if isinstance(pos, app_commands.Choice) else str(pos)
            
            if not selected_position:
                return []
            
            attrs = self.ATTRIBUTES.get(selected_position.upper(), [])
            # Filter by current input
            choices = []
            for display_name, code in attrs:
                label = f"{display_name} ({code})"
                if current.lower() in label.lower():
                    choices.append(app_commands.Choice(name=label, value=code))
            return choices[:25]
        except Exception:
            return []
    
    async def get_user_points(self, user_id):
        """Get user's current points from the points system"""
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
    
    async def deduct_user_points(self, user_id, points_to_deduct, display_name=None, username=None):
        """Deduct points from user's account"""
        try:
            current_points = await self.get_user_points(user_id)
            new_points = max(0, current_points - points_to_deduct)
            
            user_data = {
                "id": user_id,
                "total_points": new_points
            }
            
            if display_name:
                user_data["display_name"] = display_name
            if username:
                user_data["username"] = username
            
            result = self.supabase.table("users").upsert(user_data).execute()
            return new_points
        except Exception as e:
            logger.error(f"Error deducting user points for {user_id}: {e}")
            return 0
    
    async def get_user_cards(self, user_id):
        """Get user's player cards from database"""
        try:
            result = self.supabase.table("player_cards").select("*").eq("user_id", user_id).execute()
            
            if result.data:
                # Convert database format to the expected format
                cards = {}
                for card in result.data:
                    position = card["position"]
                    attributes = card["attributes"]
                    cards[position] = attributes
                return cards
            else:
                return {}
        except Exception as e:
            logger.error(f"Error getting user cards for {user_id}: {e}")
            return {}
    
    async def add_player_upgrade(self, user_id, position, player_name, attribute, points_spent, display_name=None, username=None):
        """Add or update a player upgrade"""
        try:
            # Get existing card or create new one
            existing_result = self.supabase.table("player_cards").select("*").eq("user_id", user_id).eq("position", f"{position} {player_name}").execute()
            
            if existing_result.data and len(existing_result.data) > 0:
                # Update existing card
                card = existing_result.data[0]
                attributes = card["attributes"]
                attributes[attribute] = attributes.get(attribute, 0) + int(points_spent)
                
                result = self.supabase.table("player_cards").update({
                    "attributes": attributes
                }).eq("id", card["id"]).execute()
            else:
                # Create new card
                attributes = {attribute: int(points_spent)}
                result = self.supabase.table("player_cards").insert({
                    "user_id": user_id,
                    "position": f"{position} {player_name}",
                    "attributes": attributes
                }).execute()
            
            # Deduct points
            await self.deduct_user_points(user_id, points_spent, display_name, username)
            
            return True
        except Exception as e:
            logger.error(f"Error adding player upgrade for {user_id}: {e}")
            return False
    
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
    
    @app_commands.command(name="my_cards", description="View your player cards and their upgrades")
    async def my_cards(self, interaction: discord.Interaction):
        """View user's player cards"""
        try:
            user_cards = await self.get_user_cards(interaction.user.id)
            
            if not user_cards:
                embed = discord.Embed(
                    title="🃏 Your Player Cards",
                    description="You don't have any player cards yet! Use `/upgrade` to create some.",
                    color=0x0099ff
                )
                await interaction.response.send_message(embed=embed)
                return
            
            embed = discord.Embed(
                title="🃏 Your Player Cards",
                description="Here are your current player cards and upgrades:",
                color=0x0099ff
            )
            
            for position, attributes in user_cards.items():
                if attributes:
                    attr_text = []
                    for attr, value in attributes.items():
                        if value > 0:
                            attr_text.append(f"**{attr}**: +{value}")
                    
                    if attr_text:
                        embed.add_field(
                            name=position,
                            value="\n".join(attr_text),
                            inline=True
                        )
            
            # Add current points
            current_points = await self.get_user_points(interaction.user.id)
            embed.set_footer(text=f"Current Points: {current_points:,}")
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in my_cards: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ An error occurred while fetching your cards.", 
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "❌ An error occurred while fetching your cards.", 
                    ephemeral=True
                )
    
    @app_commands.command(name="upgrade", description="Upgrade a player card attribute")
    @app_commands.describe(
        position="Player position",
        player_name="Player name",
        attribute="Attribute to upgrade",
        amount="Number of points to apply (min 1)"
    )
    @app_commands.choices(
        position=[
            app_commands.Choice(name=p, value=p) for p in [
                "QB", "RB", "WR", "TE",
                "LT/RT", "LG/RG", "C",
                "Edge", "LB", "CB", "S",
                "FB", "K", "P"
            ]
        ]
    )
    @app_commands.autocomplete(attribute=attribute_autocomplete)
    async def upgrade(self, interaction: discord.Interaction, position: app_commands.Choice[str], player_name: str, attribute: str, amount: app_commands.Range[int, 1, 999]):
        """Upgrade a player card attribute"""
        try:
            # Extract actual string value from choice
            position_value = position.value if isinstance(position, app_commands.Choice) else str(position)

            # Validate position (from dropdown, but keep guard for safety)
            if position_value.upper() not in self.POSITIONS:
                await interaction.response.send_message(
                    f"❌ Invalid position. Available positions: {', '.join(self.POSITIONS)}", 
                    ephemeral=True
                )
                return
            
            # Validate attribute
            valid_attr_pairs = self.ATTRIBUTES.get(position_value.upper())
            valid_codes = [code for (_name, code) in (valid_attr_pairs or [])]
            # Only enforce validation when we have a predefined attribute list for the position
            if valid_attr_pairs and attribute.upper() not in valid_codes:
                await interaction.response.send_message(
                    f"❌ Invalid attribute for {position_value}. Available: {', '.join(valid_codes)}", 
                    ephemeral=True
                )
                return
            
            # Check user total points threshold
            current_points = await self.get_user_points(interaction.user.id)
            if current_points < 2:
                await interaction.response.send_message(
                    "❌ You need at least 2 total points to use the upgrade system.", 
                    ephemeral=True
                )
                return
            
            # Amount validation: must be <= points remaining
            if amount < 1:
                await interaction.response.send_message(
                    "❌ Amount must be at least 1.",
                    ephemeral=True
                )
                return
            if amount > current_points:
                await interaction.response.send_message(
                    f"❌ You tried to spend {amount} points, but you only have {current_points}.",
                    ephemeral=True
                )
                return
            
            # Add the upgrade
            success = await self.add_player_upgrade(
                interaction.user.id, 
                position_value.upper(), 
                player_name, 
                attribute.upper(), 
                amount,
                interaction.user.display_name,
                interaction.user.name
            )
            
            if success:
                new_points = await self.get_user_points(interaction.user.id)
                embed = discord.Embed(
                    title="✅ Upgrade Successful!",
                    description=f"Upgraded **{attribute.upper()}** for **{position_value.upper()} {player_name}**",
                    color=0x00ff00
                )
                embed.add_field(
                    name="Cost",
                    value=f"{amount} points",
                    inline=True
                )
                embed.add_field(
                    name="Remaining Points",
                    value=f"{new_points:,} points",
                    inline=True
                )
                await interaction.response.send_message(embed=embed)
            else:
                await interaction.response.send_message(
                    "❌ Failed to process upgrade. Please try again.", 
                    ephemeral=True
                )
            
        except Exception as e:
            logger.error(f"Error in upgrade: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ An error occurred while processing your upgrade.", 
                    ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "❌ An error occurred while processing your upgrade.", 
                    ephemeral=True
                )

async def setup(bot):
    await bot.add_cog(SpendingSystemSupabase(bot))
    logger.info("✅ SpendingSystemSupabase cog added to bot")
