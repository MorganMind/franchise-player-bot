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
            "EDGE": [
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
        """Autocomplete provider for the attribute option, dependent on selected position.
        Falls back to a merged list when position isn't available yet.
        """
        try:
            # Retrieve the selected position value from interaction namespace if present
            selected_position = None
            if getattr(interaction, 'namespace', None) is not None and hasattr(interaction.namespace, 'position'):
                pos = interaction.namespace.position
                selected_position = pos.value if isinstance(pos, app_commands.Choice) else str(pos)

            # Build attribute pool
            if selected_position and selected_position.upper() in self.ATTRIBUTES:
                attrs = self.ATTRIBUTES[selected_position.upper()]
            else:
                # Fallback: merge all unique attributes (limit to 25 in the UI)
                seen = set()
                merged = []
                for pairs in self.ATTRIBUTES.values():
                    for display_name, code in pairs:
                        if code not in seen:
                            seen.add(code)
                            merged.append((display_name, code))
                attrs = merged

            # Filter by current input
            current_lower = (current or "").lower()
            choices = []
            for display_name, code in attrs:
                label = f"{display_name} ({code})"
                if current_lower in label.lower():
                    choices.append(app_commands.Choice(name=label[:100], value=code[:100]))
                if len(choices) >= 25:
                    break
            # Ensure we always return something to avoid client error
            if not choices:
                for display_name, code in attrs[:10]:
                    choices.append(app_commands.Choice(name=f"{display_name} ({code})"[:100], value=code[:100]))
            return choices
        except Exception as e:
            logger.exception(f"Attribute autocomplete error: {e}")
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
                    title="📝 Your Player Cards",
                    description="You don't have any player cards yet! Use `/upgrade` to create some.",
                    color=0x0099ff
                )
                await interaction.response.send_message(embed=embed)
                return
            
            # Count total cards
            total_cards = len([pos for pos, attrs in user_cards.items() if attrs])
            
            embed = discord.Embed(
                title="📝 Your Player Cards",
                description=f"You have {total_cards} player card(s):",
                color=0x0099ff
            )
            
            # Build the description with clean formatting
            description_parts = []
            
            for position, attributes in user_cards.items():
                if attributes:
                    # Calculate total points spent for this player
                    total_spent = 0
                    upgrade_lines = []
                    
                    for attr, value in attributes.items():
                        try:
                            numeric_value = int(value)
                        except Exception:
                            # Skip non-numeric values gracefully
                            continue
                        if numeric_value > 0:
                            total_spent += numeric_value
                            upgrade_lines.append(f"  +{numeric_value} {attr}")
                    
                    if upgrade_lines:
                        # Add player name
                        description_parts.append(f"**{position}**")
                        # Add upgrades (indented)
                        description_parts.extend(upgrade_lines)
                        # Add total points spent
                        description_parts.append(f"  Total Points Spent: {total_spent}")
                        # Add spacing between players
                        description_parts.append("")
            
            # Join all parts and add to embed
            if description_parts:
                # Remove the last empty line
                if description_parts[-1] == "":
                    description_parts.pop()
                embed.description = f"You have {total_cards} player card(s):\n\n" + "\n".join(description_parts)
            
            # Add current points
            current_points = await self.get_user_points(interaction.user.id)
            embed.set_footer(text=f"Current Points: {current_points}")
            
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
        player_name="Player name"
    )
    @app_commands.choices(
        position=[
            app_commands.Choice(name=p, value=p) for p in [
                "QB", "RB", "WR", "TE",
                "LT/RT", "LG/RG", "C",
                "EDGE", "LB", "CB", "S",
                "FB", "K", "P"
            ]
        ]
    )
    async def upgrade(self, interaction: discord.Interaction, position: app_commands.Choice[str], player_name: str):
        """Upgrade a player card attribute with multi-step flow"""
        try:
            position_value = position.value if isinstance(position, app_commands.Choice) else str(position)
            attributes = self.ATTRIBUTES.get(position_value.upper(), [])
            if not attributes:
                await interaction.response.send_message(
                    f"No attributes configured for {position_value} yet.", ephemeral=True
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

            # Build a Select menu of attributes for the chosen position, then amount
            class AmountSelect(discord.ui.Select):
                def __init__(self, max_amount: int, chosen_attr_code: str, chosen_attr_label: str, cog_instance):
                    capped = max(1, min(25, max_amount))
                    options = [
                        discord.SelectOption(label=f"{i}", value=str(i)) for i in range(1, capped + 1)
                    ]
                    super().__init__(placeholder="Choose amount to spend", min_values=1, max_values=1, options=options)
                    self.chosen_attr_code = chosen_attr_code
                    self.chosen_attr_label = chosen_attr_label
                    self.cog = cog_instance

                async def callback(self, inner_interaction: discord.Interaction):
                    amount_str = self.values[0]
                    amount = int(amount_str)
                    
                    # Check if this upgrade would exceed the 90 attribute limit
                    user_cards = await self.cog.get_user_cards(inner_interaction.user.id)
                    player_key = f"{position_value.upper()} {player_name}"
                    current_attr_value = 0
                    
                    if player_key in user_cards:
                        current_attr_value = user_cards[player_key].get(self.chosen_attr_code.upper(), 0)
                    
                    if current_attr_value + amount > 90:
                        await inner_interaction.response.send_message(
                            f"❌ **No attribute can be increased over 90!**\n"
                            f"Current {self.chosen_attr_label}: **{current_attr_value}**\n"
                            f"Attempted upgrade: **+{amount}**\n"
                            f"Would result in: **{current_attr_value + amount}**\n\n"
                            f"*Check your players and reduce the amount.*",
                            ephemeral=True
                        )
                        return
                    
                    # Actually perform the upgrade
                    success = await self.cog.add_player_upgrade(
                        inner_interaction.user.id, 
                        position_value.upper(), 
                        player_name, 
                        self.chosen_attr_code.upper(), 
                        amount,
                        inner_interaction.user.display_name,
                        inner_interaction.user.name
                    )
                    
                    if success:
                        new_points = await self.cog.get_user_points(inner_interaction.user.id)
                        summary = discord.Embed(
                            title="✅ Upgrade Successful!",
                            description=(
                                f"Position: **{position_value.upper()}**\n"
                                f"Player: **{player_name}**\n"
                                f"Attribute: **{self.chosen_attr_label} ({self.chosen_attr_code})**\n"
                                f"Amount: **{amount}** point(s)\n"
                                f"Remaining Points: **{new_points}**"
                            ),
                            color=0x00ff00
                        )
                        await inner_interaction.response.send_message(embed=summary)
                    else:
                        await inner_interaction.response.send_message(
                            "❌ Failed to process upgrade. Please try again.", 
                            ephemeral=True
                        )

            class AttributeSelect(discord.ui.Select):
                def __init__(self, attrs: list[tuple[str, str]]):
                    options = [
                        discord.SelectOption(label=disp_name[:100], value=code[:100])
                        for disp_name, code in attrs[:25]
                    ]
                    super().__init__(placeholder="Choose an attribute", min_values=1, max_values=1, options=options)

                async def callback(self, inner_interaction: discord.Interaction):
                    chosen_code = self.values[0]
                    # Find display label
                    label = next((d for d, c in attributes if c == chosen_code), chosen_code)
                    # Swap the view to show amount choices
                    amount_view = discord.ui.View(timeout=180)
                    amount_view.add_item(AmountSelect(current_points, chosen_code, label, self))
                    await inner_interaction.response.edit_message(
                        content=f"Now choose how many points to spend (you have {current_points}).",
                        view=amount_view
                    )

            class UpgradeView(discord.ui.View):
                def __init__(self, attrs: list[tuple[str, str]]):
                    super().__init__(timeout=180)
                    self.add_item(AttributeSelect(attrs))

            view = UpgradeView(attributes)
            header = discord.Embed(
                title="Upgrade Player",
                description=(
                    f"Pick an attribute for {position_value.upper()} {player_name}.\n"
                    f"Then pick an amount to spend.\n"
                    f"Your current points: **{current_points}**\n\n"
                    f"⚠️ **Note: No attribute can be increased over 90!**"
                ),
                color=0x0099ff
            )
            await interaction.response.send_message(embed=header, view=view, ephemeral=True)
        except Exception as e:
            logger.error(f"Error in upgrade: {e}")
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "❌ Failed to show upgrade menu.", ephemeral=True
                )
            else:
                await interaction.followup.send(
                    "❌ Failed to show upgrade menu.", ephemeral=True
                )

async def setup(bot):
    await bot.add_cog(SpendingSystemSupabase(bot))
    logger.info("✅ SpendingSystemSupabase cog added to bot")
