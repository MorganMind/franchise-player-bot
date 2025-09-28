import discord
from discord.ext import commands
from discord import app_commands
import json
import os
import logging

logger = logging.getLogger(__name__)

class SpendingSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cards_file = "data/player_cards.json"
        self.cards_data = self.load_cards()
        
        # Position and attribute definitions
        self.POSITIONS = ["QB", "WR", "HB"]
        self.ATTRIBUTES = {
            "QB": ["MAC", "DAC", "SAC", "TUP", "TOR"],
            "WR": ["MAC", "DAC", "SAC", "TUP", "TOR"],  # Same for now, will be customized later
            "HB": ["MAC", "DAC", "SAC", "TUP", "TOR"]   # Same for now, will be customized later
        }
        
        # Cost per attribute point
        self.ATTRIBUTE_COST = 1  # 1 point per +1 attribute
        
        logger.info("✅ SpendingSystem cog initialized")
    
    def load_cards(self):
        """Load player cards data from JSON file"""
        if os.path.exists(self.cards_file):
            try:
                with open(self.cards_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading cards: {e}")
                return {"users": {}}
        else:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.cards_file), exist_ok=True)
            return {"users": {}}
    
    def save_cards(self):
        """Save player cards data to JSON file"""
        try:
            with open(self.cards_file, 'w') as f:
                json.dump(self.cards_data, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving cards: {e}")
    
    def get_user_points(self, user_id):
        """Get user's current points from the points system"""
        try:
            points_file = "data/points.json"
            if os.path.exists(points_file):
                with open(points_file, 'r') as f:
                    points_data = json.load(f)
                    return points_data.get("users", {}).get(str(user_id), 0)
            return 0
        except Exception as e:
            logger.error(f"Error getting user points: {e}")
            return 0
    
    def deduct_user_points(self, user_id, points_to_deduct):
        """Deduct points from user's account"""
        try:
            points_file = "data/points.json"
            if os.path.exists(points_file):
                with open(points_file, 'r') as f:
                    points_data = json.load(f)
                
                current_points = points_data.get("users", {}).get(str(user_id), 0)
                new_points = max(0, current_points - points_to_deduct)
                points_data["users"][str(user_id)] = new_points
                
                with open(points_file, 'w') as f:
                    json.dump(points_data, f, indent=2)
                
                return new_points
            return 0
        except Exception as e:
            logger.error(f"Error deducting user points: {e}")
            return 0
    
    def get_user_cards(self, user_id):
        """Get user's player cards"""
        return self.cards_data.get("users", {}).get(str(user_id), {})
    
    def add_player_upgrade(self, user_id, position, player_name, attribute, points_spent):
        """Add or update a player upgrade"""
        if str(user_id) not in self.cards_data["users"]:
            self.cards_data["users"][str(user_id)] = {}
        
        user_cards = self.cards_data["users"][str(user_id)]
        
        # Create player key (position + name)
        player_key = f"{position} {player_name}"
        
        if player_key not in user_cards:
            user_cards[player_key] = {
                "position": position,
                "player_name": player_name,
                "attributes": {},
                "attribute_points_spent": {},  # Track points spent per attribute
                "total_points_spent": 0
            }
        
        # Add or update attribute
        if attribute not in user_cards[player_key]["attributes"]:
            user_cards[player_key]["attributes"][attribute] = 0
            user_cards[player_key]["attribute_points_spent"][attribute] = 0
        
        # Calculate how many attribute points this purchase adds
        attribute_points = points_spent // self.ATTRIBUTE_COST
        user_cards[player_key]["attributes"][attribute] += attribute_points
        user_cards[player_key]["attribute_points_spent"][attribute] += points_spent
        user_cards[player_key]["total_points_spent"] += points_spent
        
        self.save_cards()
    
    @app_commands.command(name="buyupgrade", description="Spend points to upgrade a player's attributes")
    @app_commands.describe(
        position="Player position",
        player_name="Player name",
        attribute="Attribute to upgrade",
        points="Number of points to spend (1 point = +1 attribute)"
    )
    async def buy_upgrade(
        self, 
        interaction: discord.Interaction, 
        position: str, 
        player_name: str, 
        attribute: str, 
        points: int
    ):
        """Buy attribute upgrades for players"""
        try:
            # Validate position
            position = position.upper()
            if position not in self.POSITIONS:
                await interaction.response.send_message(
                    f"❌ Invalid position. Please choose from: {', '.join(self.POSITIONS)}",
                    ephemeral=True
                )
                return
            
            # Validate attribute
            attribute = attribute.upper()
            if attribute not in self.ATTRIBUTES[position]:
                await interaction.response.send_message(
                    f"❌ Invalid attribute for {position}. Please choose from: {', '.join(self.ATTRIBUTES[position])}",
                    ephemeral=True
                )
                return
            
            # Validate points
            if points <= 0:
                await interaction.response.send_message(
                    "❌ Points must be a positive number.",
                    ephemeral=True
                )
                return
            
            if points % self.ATTRIBUTE_COST != 0:
                await interaction.response.send_message(
                    f"❌ Points must be a multiple of {self.ATTRIBUTE_COST} (1 point = +1 attribute).",
                    ephemeral=True
                )
                return
            
            # Check if user has enough points
            user_points = self.get_user_points(interaction.user.id)
            if user_points < points:
                await interaction.response.send_message(
                    f"❌ You don't have enough points. You have {user_points:,} points, but need {points:,} points.",
                    ephemeral=True
                )
                return
            
            # Calculate attribute increase
            attribute_increase = points // self.ATTRIBUTE_COST
            
            # Add the upgrade
            self.add_player_upgrade(interaction.user.id, position, player_name, attribute, points)
            
            # Deduct points
            remaining_points = self.deduct_user_points(interaction.user.id, points)
            
            # Create response embed
            embed = discord.Embed(
                title="✅ Upgrade Purchased!",
                description=f"Successfully upgraded **{player_name}** ({position})",
                color=0x00ff00
            )
            
            embed.add_field(
                name="Upgrade Details",
                value=f"**{attribute}**: +{attribute_increase}\n**Points Spent**: {points:,}\n**Points Remaining**: {remaining_points:,}",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in buy_upgrade: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while processing your purchase.",
                ephemeral=True
            )
    
    @app_commands.command(name="mycards", description="View your player cards and upgrades")
    async def my_cards(self, interaction: discord.Interaction):
        """Show user's player cards"""
        try:
            user_cards = self.get_user_cards(interaction.user.id)
            
            if not user_cards:
                embed = discord.Embed(
                    title="📋 Your Player Cards",
                    description="You don't have any player cards yet. Use `/buyupgrade` to create your first card!",
                    color=0x0099ff
                )
                await interaction.response.send_message(embed=embed)
                return
            
            embed = discord.Embed(
                title="📋 Your Player Cards",
                description=f"You have {len(user_cards)} player card(s):",
                color=0x0099ff
            )
            
            for player_key, card_data in user_cards.items():
                position = card_data["position"]
                player_name = card_data["player_name"]
                attributes = card_data["attributes"]
                attribute_points_spent = card_data.get("attribute_points_spent", {})
                total_spent = card_data["total_points_spent"]
                
                # Format attributes with points spent
                attr_text = ""
                for attr, value in attributes.items():
                    if value > 0:
                        points_spent = attribute_points_spent.get(attr, value)  # Fallback to value if not tracked
                        attr_text += f"+{points_spent} {attr}\n"
                
                if not attr_text:
                    attr_text = "No upgrades yet"
                
                embed.add_field(
                    name=f"{position} {player_name}",
                    value=f"{attr_text}\n**Total Points Spent**: {total_spent:,}",
                    inline=False
                )
            
            # Add current points
            current_points = self.get_user_points(interaction.user.id)
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
    
    @app_commands.command(name="carddetails", description="View detailed breakdown of a specific player card")
    @app_commands.describe(
        position="Player position",
        player_name="Player name"
    )
    async def card_details(self, interaction: discord.Interaction, position: str, player_name: str):
        """Show detailed breakdown of a specific player card"""
        try:
            position = position.upper()
            player_key = f"{position} {player_name}"
            user_cards = self.get_user_cards(interaction.user.id)
            
            if player_key not in user_cards:
                await interaction.response.send_message(
                    f"❌ You don't have a card for {player_key}.",
                    ephemeral=True
                )
                return
            
            card_data = user_cards[player_key]
            attributes = card_data["attributes"]
            attribute_points_spent = card_data.get("attribute_points_spent", {})
            total_spent = card_data["total_points_spent"]
            
            embed = discord.Embed(
                title=f"📋 {player_key} - Detailed Breakdown",
                description=f"**Total Points Spent**: {total_spent:,}",
                color=0x0099ff
            )
            
            # Show each attribute and its total
            for attr, value in attributes.items():
                if value > 0:
                    points_spent = attribute_points_spent.get(attr, value)  # Fallback to value if not tracked
                    embed.add_field(
                        name=f"{attr}",
                        value=f"+{points_spent} (cost: {points_spent:,} points)",
                        inline=True
                    )
            
            # Calculate total attribute points
            total_attr_points = sum(attributes.values())
            embed.add_field(
                name="Summary",
                value=f"**Total Attribute Points**: {total_attr_points}\n**Points per Attribute**: 1:1 ratio",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            logger.error(f"Error in card_details: {e}")
            await interaction.response.send_message(
                "❌ An error occurred while fetching card details.",
                ephemeral=True
            )

async def setup(bot):
    await bot.add_cog(SpendingSystem(bot))
    logger.info("✅ SpendingSystem cog added to bot")
