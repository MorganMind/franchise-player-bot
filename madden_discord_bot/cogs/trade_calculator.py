import discord
from discord.ext import commands
from discord import app_commands
import openai
from config.settings import OPENAI_API_KEY, SYSTEM_PROMPT
import traceback
import sys
import os
import asyncio
import logging

# Set up logging
logger = logging.getLogger(__name__)

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.calculator import Player, DraftPick, parse_player_input, parse_draft_pick_input
from utils.ai_parser import trade_parser
from utils.player_lookup import player_lookup
from utils.validation import validator

# Set up OpenAI
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY

class TradeCalculator(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        logger.info("✅ TradeCalculator cog initialized")
    
    @app_commands.command(name="calc_player", description="Calculate a player's trade value")
    async def calc_player(
        self, 
        interaction: discord.Interaction,
        player_info: str
    ):
        """Calculate single player value"""
        try:
            # Parse player info
            player = parse_player_input(player_info)
            details = player.get_details()
            
            embed = discord.Embed(
                title=f"📊 Player Trade Value",
                color=0x00ff00
            )
            embed.add_field(name="Player", value=details['name'], inline=True)
            embed.add_field(name="OVR", value=details['ovr'], inline=True)
            embed.add_field(name="Age", value=details['age'], inline=True)
            embed.add_field(name="Position", value=details['position'], inline=True)
            embed.add_field(name="Dev Trait", value=details['dev_trait'], inline=True)
            embed.add_field(name="**Trade Value**", value=f"**{details['value']:,}**", inline=True)
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            print(f"❌ Error in calc_player: {e}")
            traceback.print_exc()
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
    
    @app_commands.command(name="trade", description="Compare trade values between teams")
    async def trade(
        self, 
        interaction: discord.Interaction,
        team1_assets: str,
        team2_assets: str
    ):
        """Full trade calculator"""
        print(f"Trade command: Team 1: {team1_assets} | Team 2: {team2_assets}")
        
        try:
            await interaction.response.defer()
            
            # Parse assets for both teams
            team1_items = self._parse_trade_assets(team1_assets)
            team2_items = self._parse_trade_assets(team2_assets)
            
            # Calculate total values
            team1_total = sum(item['value'] for item in team1_items)
            team2_total = sum(item['value'] for item in team2_items)
            
            # Determine fairness
            difference = abs(team1_total - team2_total)
            percentage_diff = (difference / max(team1_total, team2_total)) * 100
            
            if percentage_diff <= 5:
                fairness = "✅ Very Fair Trade"
                color = 0x00ff00
            elif percentage_diff <= 15:
                fairness = "⚠️ Slightly Uneven"
                color = 0xffff00
            else:
                fairness = "❌ Unbalanced Trade"
                color = 0xff0000
            
            # Create embed
            embed = discord.Embed(
                title="🏈 Trade Analysis",
                description=fairness,
                color=color
            )
            
            # Team 1 assets
            team1_text = "\n".join([f"• {item['description']}: **{item['value']:,}**" for item in team1_items])
            embed.add_field(
                name=f"Team 1 Sends (Total: {team1_total:,})",
                value=team1_text or "No assets",
                inline=False
            )
            
            # Team 2 assets
            team2_text = "\n".join([f"• {item['description']}: **{item['value']:,}**" for item in team2_items])
            embed.add_field(
                name=f"Team 2 Sends (Total: {team2_total:,})",
                value=team2_text or "No assets",
                inline=False
            )
            
            # Summary
            if team1_total > team2_total:
                winner = "Team 2 wins by"
            elif team2_total > team1_total:
                winner = "Team 1 wins by"
            else:
                winner = "Perfectly even -"
            
            embed.add_field(
                name="Summary",
                value=f"{winner} **{difference:,}** points ({percentage_diff:.1f}% difference)",
                inline=False
            )
            
            # Get AI analysis if available
            if OPENAI_API_KEY and percentage_diff > 5:
                ai_prompt = f"Analyze this Madden trade: Team 1 gives {team1_assets} (value: {team1_total}). Team 2 gives {team2_assets} (value: {team2_total}). The difference is {percentage_diff:.1f}%. Give a brief analysis in 2-3 sentences."
                
                try:
                    ai_analysis = await self._get_openai_analysis(ai_prompt)
                    embed.add_field(
                        name="AI Analysis",
                        value=ai_analysis[:500],
                        inline=False
                    )
                except:
                    pass
            
            embed.set_footer(text="Use /calc_player or /calc_pick to check individual values")
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            print(f"❌ Error in trade: {e}")
            traceback.print_exc()
            await interaction.followup.send(f"❌ Error: {str(e)}")
    
    @app_commands.command(name="calc_pick", description="Calculate a draft pick's trade value")
    async def calc_pick(
        self, 
        interaction: discord.Interaction,
        pick_info: str
    ):
        """Calculate draft pick value"""
        try:
            # Parse pick info
            pick = parse_draft_pick_input(pick_info)
            details = pick.get_details()
            
            embed = discord.Embed(
                title=f"📊 Draft Pick Trade Value",
                color=0x0099ff
            )
            embed.add_field(name="Pick", value=details['description'], inline=True)
            embed.add_field(name="Overall", value=f"#{details['overall']}", inline=True)
            embed.add_field(name="**Trade Value**", value=f"**{details['value']:,}**", inline=True)
            
            await interaction.response.send_message(embed=embed)
            
        except Exception as e:
            print(f"❌ Error in calc_pick: {e}")
            await interaction.response.send_message(f"❌ Error: {str(e)}", ephemeral=True)
    
    def _parse_trade_assets(self, assets_string):
        """Parse a string of trade assets into players and picks"""
        items = []
        
        # Split by common delimiters
        parts = assets_string.replace(' and ', ',').replace(' + ', ',').replace(';', ',').split(',')
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            # Check if it's a draft pick (contains round/pick indicators)
            if any(indicator in part.lower() for indicator in ['round', 'r1', 'r2', 'r3', 'pick', '1st', '2nd', '3rd', '2024', '2025']):
                try:
                    pick = parse_draft_pick_input(part)
                    details = pick.get_details()
                    items.append({
                        'description': details['description'],
                        'value': details['value'],
                        'type': 'pick'
                    })
                except:
                    pass
            else:
                # Assume it's a player
                try:
                    player = parse_player_input(part)
                    details = player.get_details()
                    items.append({
                        'description': f"{details['name']} ({details['ovr']} {details['position']})",
                        'value': details['value'],
                        'type': 'player'
                    })
                except:
                    pass
        
        return items
    
    async def _get_openai_analysis(self, prompt):
        """Get AI analysis of the trade"""
        try:
            client = openai.OpenAI(api_key=OPENAI_API_KEY)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=150,
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"OpenAI error: {e}")
            return ""
    
    @app_commands.command(name="tradecommittee", description="Advanced trade analysis with AI parsing")
    @app_commands.describe(
        trade_details="Paste your trade details here (multi-line supported). Format: Team A gives X, Team B gives Y"
    )
    async def trade_committee(
        self,
        interaction: discord.Interaction,
        trade_details: str
    ):
        """Advanced trade analysis with AI parsing and web lookup"""
        logger.info(f"Trade Committee command called by {interaction.user} with: {trade_details[:100]}...")
        
        # Defer immediately to prevent timeout
        await interaction.response.defer()
        
        try:
            # Send initial "processing" message
            status_msg = await interaction.followup.send(
                "🤖 **Processing trade...** This may take 10-30 seconds.\n\n" + 
                "📋 Parsing trade details with AI...\n" +
                "🔍 Looking up missing player data...\n" +
                "🧮 Calculating trade values...", 
                ephemeral=False
            )
            
            # Step 1: Parse the trade using AI
            logger.info("Step 1: AI Parsing...")
            try:
                parsed_data = await trade_parser.parse_trade_input(trade_details)
                logger.info(f"Successfully parsed trade data")
            except Exception as e:
                logger.error(f"Failed to parse trade: {e}")
                raise ValueError(f"Could not parse trade details. Please check format and try again.")
            
            # Step 2: Validate and convert data
            logger.info("Step 2: Validating and converting data...")
            team1_items = []
            team2_items = []
            validation_errors = []
            
            # Process Team 1
            try:
                for player_data in parsed_data.get('team1', {}).get('players', []):
                    try:
                        validated_data = validator.validate_player_data(player_data)
                        player = Player(
                            name=validated_data['name'],
                            ovr=validated_data['ovr'],
                            age=validated_data['age'],
                            dev_trait=validated_data['dev'],
                            position=validated_data['position']
                        )
                        details = player.get_details()
                        team1_items.append({
                            'description': f"{details['name']} ({details['ovr']} {details['position']}, {details['age']}yo, {details['dev_trait']})",
                            'value': details['value'],
                            'type': 'player'
                        })
                    except Exception as e:
                        error_msg = f"Error processing Team 1 player {player_data.get('name', 'Unknown')}: {str(e)}"
                        logger.error(error_msg)
                        validation_errors.append(error_msg)
                
                for pick_data in parsed_data.get('team1', {}).get('picks', []):
                    try:
                        validated_data = validator.validate_pick_data(pick_data)
                        # Check if this is a "Next" year pick
                        is_next_year = pick_data.get('is_next_year', False)
                        pick = DraftPick(
                            round_num=validated_data['round'],
                            pick_num=validated_data['pick'],
                            year=validated_data['year'],
                            is_next_year=is_next_year
                        )
                        details = pick.get_details()
                        team1_items.append({
                            'description': details['description'],
                            'value': details['value'],
                            'type': 'pick'
                        })
                    except Exception as e:
                        error_msg = f"Error processing Team 1 pick: {str(e)}"
                        logger.error(error_msg)
                        validation_errors.append(error_msg)
            
            except Exception as e:
                logger.error(f"Critical error processing Team 1: {e}")
                validation_errors.append(f"Could not process Team 1 assets: {str(e)}")
            
            # Process Team 2 (similar logic)
            try:
                for player_data in parsed_data.get('team2', {}).get('players', []):
                    try:
                        validated_data = validator.validate_player_data(player_data)
                        player = Player(
                            name=validated_data['name'],
                            ovr=validated_data['ovr'],
                            age=validated_data['age'],
                            dev_trait=validated_data['dev'],
                            position=validated_data['position']
                        )
                        details = player.get_details()
                        team2_items.append({
                            'description': f"{details['name']} ({details['ovr']} {details['position']}, {details['age']}yo, {details['dev_trait']})",
                            'value': details['value'],
                            'type': 'player'
                        })
                    except Exception as e:
                        error_msg = f"Error processing Team 2 player {player_data.get('name', 'Unknown')}: {str(e)}"
                        logger.error(error_msg)
                        validation_errors.append(error_msg)
                
                for pick_data in parsed_data.get('team2', {}).get('picks', []):
                    try:
                        validated_data = validator.validate_pick_data(pick_data)
                        # Check if this is a "Next" year pick
                        is_next_year = pick_data.get('is_next_year', False)
                        pick = DraftPick(
                            round_num=validated_data['round'],
                            pick_num=validated_data['pick'],
                            year=validated_data['year'],
                            is_next_year=is_next_year
                        )
                        details = pick.get_details()
                        team2_items.append({
                            'description': details['description'],
                            'value': details['value'],
                            'type': 'pick'
                        })
                    except Exception as e:
                        error_msg = f"Error processing Team 2 pick: {str(e)}"
                        logger.error(error_msg)
                        validation_errors.append(error_msg)
            
            except Exception as e:
                logger.error(f"Critical error processing Team 2: {e}")
                validation_errors.append(f"Could not process Team 2 assets: {str(e)}")
            
            # Check if we have valid items
            if not team1_items and not team2_items:
                raise ValueError("No valid trade items could be processed. Please check your input format.")
            
            # Step 3: Calculate totals and fairness
            team1_total = sum(item['value'] for item in team1_items)
            team2_total = sum(item['value'] for item in team2_items)
            
            # Prevent division by zero
            if max(team1_total, team2_total) == 0:
                percentage_diff = 0
            else:
                difference = abs(team1_total - team2_total)
                percentage_diff = (difference / max(team1_total, team2_total)) * 100
            
            # Determine fairness based on your criteria
            if percentage_diff <= 10:
                fairness = "✅ **FAIR TRADE**"
                fairness_color = 0x00ff00
            elif percentage_diff >= 30:
                fairness = "❌ **UNFAIR TRADE**"
                fairness_color = 0xff0000
            else:
                fairness = "⚠️ **OKAY TRADE**"
                fairness_color = 0xffff00
            
            # Step 4: Get AI analysis
            logger.info("Step 4: Getting AI analysis...")
            try:
                ai_analysis = await trade_parser.analyze_trade(parsed_data, team1_total, team2_total)
            except Exception as e:
                logger.error(f"AI analysis failed: {e}")
                ai_analysis = "AI analysis temporarily unavailable."
            
            # Step 5: Create comprehensive embed
            embed = discord.Embed(
                title="🏛️ Trade Committee Analysis",
                description=f"{fairness}\n*{percentage_diff:.1f}% value difference*",
                color=fairness_color
            )
            
            # Add validation warnings if any
            if validation_errors:
                embed.add_field(
                    name="⚠️ Data Issues",
                    value="\n".join(validation_errors[:3]),  # Show first 3 errors
                    inline=False
                )
            
            # Team 1 section
            if team1_items:
                team1_text = "\n".join([f"• {item['description']}: **{item['value']:,}**" for item in team1_items])
                embed.add_field(
                    name=f"📤 Team 1 Sends (Total: {team1_total:,})",
                    value=team1_text[:1024],
                    inline=False
                )
            else:
                embed.add_field(
                    name="📤 Team 1 Sends",
                    value="*No valid assets*",
                    inline=False
                )
            
            # Team 2 section
            if team2_items:
                team2_text = "\n".join([f"• {item['description']}: **{item['value']:,}**" for item in team2_items])
                embed.add_field(
                    name=f"📥 Team 2 Sends (Total: {team2_total:,})",
                    value=team2_text[:1024],
                    inline=False
                )
            else:
                embed.add_field(
                    name="📥 Team 2 Sends",
                    value="*No valid assets*",
                    inline=False
                )
            
            # Value summary
            if team1_total > team2_total:
                winner_text = f"Team 2 gets **{abs(team1_total - team2_total):,}** more value"
            elif team2_total > team1_total:
                winner_text = f"Team 1 gets **{abs(team2_total - team1_total):,}** more value"
            else:
                winner_text = "Perfectly balanced trade"
            
            embed.add_field(
                name="📊 Value Summary",
                value=winner_text,
                inline=False
            )
            
            # AI Analysis
            if ai_analysis and ai_analysis != "AI analysis temporarily unavailable.":
                embed.add_field(
                    name="🤖 Expert Analysis",
                    value=ai_analysis[:1024],
                    inline=False
                )
            
            # Footer with additional info
            footer_text = "✨ AI-powered analysis with validated data"
            if validation_errors:
                footer_text += f" | ⚠️ {len(validation_errors)} data issues resolved"
            embed.set_footer(text=footer_text)
            
            # Edit the original message with results
            await interaction.edit_original_response(content=None, embed=embed)
            logger.info("Trade committee analysis completed successfully")
            
        except Exception as e:
            logger.error(f"❌ Critical error in trade_committee: {e}")
            traceback.print_exc()
            
            try:
                error_embed = discord.Embed(
                    title="❌ Trade Committee Error",
                    description=f"Sorry, there was an error processing your trade:\n```{str(e)}```",
                    color=0xff0000
                )
                error_embed.add_field(
                    name="💡 Tips for Better Results",
                    value=(
                        "• Use clear player names (e.g., 'Patrick Mahomes' not 'Mahomes')\n"
                        "• Include positions when possible (QB, RB, WR, etc.)\n"
                        "• Format picks as '2024 R1 P15' or '2024 1st round'\n"
                        "• Separate teams clearly with 'gives', 'sends', or 'trades'"
                    ),
                    inline=False
                )
                error_embed.add_field(
                    name="📝 Example Format",
                    value=(
                        "Team A sends: Josh Jacobs 90 OVR 27yo SS RB\n"
                        "Team B sends: Trevon Diggs 84 OVR CB + 2024 2nd round"
                    ),
                    inline=False
                )
                await interaction.edit_original_response(content=None, embed=error_embed)
            except Exception as followup_error:
                logger.error(f"Failed to send error message: {followup_error}")
                await interaction.followup.send("❌ An unexpected error occurred. Please try again.")
        
        finally:
            # Clean up resources
            try:
                await player_lookup.close_session()
            except:
                pass
    
    @app_commands.command(name="test_values", description="Test player and pick values for debugging")
    async def test_values(self, interaction: discord.Interaction):
        """Test command to verify player and pick values"""
        
        embed = discord.Embed(
            title="📊 Trade Value Test",
            color=0x0099ff
        )
        
        # Test some players
        test_players = [
            ("Patrick Mahomes", 99, 28, "x-factor", "qb"),
            ("Josh Jacobs", 90, 27, "superstar", "rb"),
            ("Young Star", 85, 22, "superstar", "wr"),  # Young player to show boost
            ("Veteran Player", 75, 26, "normal", "wr"),
        ]
        
        player_results = []
        for name, ovr, age, dev, pos in test_players:
            player = Player(name, ovr, age, dev, pos)
            details = player.get_details()
            player_results.append(f"• {name}: **{details['value']:,}** points")
        
        embed.add_field(
            name="Sample Player Values (Doubled + Age Boost)",
            value="\n".join(player_results),
            inline=False
        )
        
        # Test some picks
        test_picks = [
            (1, 1, 2025),    # 1st overall (current year)
            (1, 16, 2025),   # Mid 1st (current year)
            (2, 1, 2025),    # Top of 2nd (current year)
            (1, 1, None, True),  # Next 1st round (discounted to 2nd)
        ]
        
        pick_results = []
        for pick_data in test_picks:
            if len(pick_data) == 4:  # Has is_next_year parameter
                round_num, pick_num, year, is_next_year = pick_data
                pick = DraftPick(round_num, pick_num, year, is_next_year)
            else:  # Standard format
                round_num, pick_num, year = pick_data
                pick = DraftPick(round_num, pick_num, year)
            details = pick.get_details()
            pick_results.append(f"• {details['description']}: **{details['value']:,}** points")
        
        embed.add_field(
            name="Sample Pick Values (Original)",
            value="\n".join(pick_results),
            inline=False
        )
        
        embed.set_footer(text="Players: 2x value + age boost, picks: exact chart values + Next year discount")
        
        await interaction.response.send_message(embed=embed)
    
    async def cog_unload(self):
        """Clean up when cog is unloaded"""
        await player_lookup.close_session()

async def setup(bot):
    await bot.add_cog(TradeCalculator(bot))
    logger.info("✅ TradeCalculator cog added to bot")
