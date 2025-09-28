import openai
import json
import re
from config.settings import OPENAI_API_KEY
from .player_lookup import player_lookup

class TradeParser:
    def __init__(self):
        if OPENAI_API_KEY:
            self.client = openai.OpenAI(api_key=OPENAI_API_KEY)
        else:
            self.client = None
    
    def _clean_discord_input(self, text):
        """Remove Discord emojis and clean up the input"""
        # Remove Discord custom emojis
        text = re.sub(r'<:[^:]+:[0-9]+>', '', text)
        # Remove Discord animated emojis
        text = re.sub(r'<a:[^:]+:[0-9]+>', '', text)
        # Clean up extra spaces
        text = ' '.join(text.split())
        return text
    
    async def parse_trade_input(self, raw_input):
        """Parse raw trade input using AI and return structured data"""
        if not self.client:
            raise Exception("OpenAI API key not configured")
        
        # Clean Discord formatting
        cleaned_input = self._clean_discord_input(raw_input)
        
        # First, ask AI to structure the input
        parsing_prompt = f"""
Parse this trade proposal into structured JSON format. Extract all players and draft picks mentioned.
For each player, identify: name, overall_rating (if mentioned), age (if mentioned), development_trait (x-factor/superstar/star/normal), position.
For draft picks, identify: year, round, pick_number.

Input: {cleaned_input}

Important notes:
- If a draft pick doesn't specify a pick number (e.g., just "2nd round"), use null for pick
- If a draft pick doesn't specify a year, use null for year
- Common abbreviations: xf/XF=x-factor, ss/SS=superstar, HB/RB=running back, CB=cornerback, etc.
- "ovl" means "overall"
- "yrs" means "years old"

Return ONLY a JSON object with this structure:
{{
    "team1": {{
        "players": [
            {{"name": "Player Name", "ovr": 95, "age": 28, "dev": "superstar", "position": "qb"}}
        ],
        "picks": [
            {{"year": 2024, "round": 1, "pick": 15}}
        ]
    }},
    "team2": {{
        "players": [...],
        "picks": [...]
    }}
}}

If a value is not specified, use null.
"""

        try:
            response = self.client.chat.completions.create(
                model="gpt-4",  # Using GPT-4 for better parsing
                messages=[
                    {"role": "system", "content": "You are a precise data parser for NFL Madden trades. Interpret 'sends' as what a team gives away. Return only valid JSON."},
                    {"role": "user", "content": parsing_prompt}
                ],
                max_tokens=1000,
                temperature=0.1
            )
            
            # Extract JSON from response
            ai_response = response.choices[0].message.content.strip()
            
            # Clean up response to extract JSON
            json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                parsed_data = json.loads(json_str)
            else:
                parsed_data = json.loads(ai_response)
            
            # Fill in missing player data
            parsed_data = await self._complete_player_data(parsed_data)
            
            return parsed_data
            
        except Exception as e:
            print(f"AI parsing error: {e}")
            # Fallback to basic parsing
            return await self._fallback_parse(raw_input)
    
    async def _complete_player_data(self, parsed_data):
        """Fill in missing player data using AI and lookup"""
        for team_key in ['team1', 'team2']:
            if team_key not in parsed_data:
                continue
                
            for player in parsed_data[team_key].get('players', []):
                # Fill missing data using AI knowledge + lookup
                if any(player.get(field) is None for field in ['ovr', 'age', 'dev', 'position']):
                    complete_data = await self._get_complete_player_data(player['name'])
                    
                    # Fill in missing fields
                    for field in ['ovr', 'age', 'dev', 'position']:
                        if player.get(field) is None and field in complete_data:
                            player[field] = complete_data[field]
        
        return parsed_data
    
    async def _get_complete_player_data(self, player_name):
        """Get complete player data using AI + lookup"""
        try:
            # First try web lookup
            lookup_data = await player_lookup.lookup_player_data(player_name)
            if lookup_data:
                return lookup_data
            
            # Fallback to AI knowledge
            ai_prompt = f"""
What are the current Madden 25/26 ratings for {player_name}?
Provide: overall rating (50-99), age, position (QB/RB/WR/TE/OL/DL/LB/CB/S/K/P), development trait (normal/star/superstar/x-factor).

Response format:
Overall: 95
Age: 28
Position: QB  
Dev Trait: superstar
"""
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a Madden NFL expert. Provide accurate current player ratings."},
                    {"role": "user", "content": ai_prompt}
                ],
                max_tokens=150,
                temperature=0.1
            )
            
            ai_text = response.choices[0].message.content
            
            # Parse AI response
            ovr_match = re.search(r'Overall:?\s*(\d+)', ai_text, re.IGNORECASE)
            age_match = re.search(r'Age:?\s*(\d+)', ai_text, re.IGNORECASE)
            pos_match = re.search(r'Position:?\s*(\w+)', ai_text, re.IGNORECASE)
            dev_match = re.search(r'(?:Dev )?Trait:?\s*([\w-]+)', ai_text, re.IGNORECASE)
            
            return {
                'ovr': int(ovr_match.group(1)) if ovr_match else 80,
                'age': int(age_match.group(1)) if age_match else 26,
                'position': pos_match.group(1).lower() if pos_match else 'wr',
                'dev': dev_match.group(1).lower().replace('-', '') if dev_match else 'normal'
            }
            
        except Exception as e:
            print(f"Error getting complete data for {player_name}: {e}")
            return {'ovr': 80, 'age': 26, 'position': 'wr', 'dev': 'normal'}
    
    async def _fallback_parse(self, raw_input):
        """Simple fallback parsing if AI fails"""
        # Very basic parsing as fallback
        lines = raw_input.strip().split('\n')
        
        return {
            "team1": {
                "players": [{"name": "Player 1", "ovr": 80, "age": 26, "dev": "normal", "position": "wr"}],
                "picks": []
            },
            "team2": {
                "players": [{"name": "Player 2", "ovr": 80, "age": 26, "dev": "normal", "position": "wr"}],
                "picks": []
            }
        }
    
    async def analyze_trade(self, parsed_data, team1_value, team2_value):
        """Generate trade analysis using AI"""
        try:
            # Create summary of trade
            team1_summary = []
            team2_summary = []
            
            # Team 1 assets
            for player in parsed_data['team1'].get('players', []):
                team1_summary.append(f"{player['name']} ({player['ovr']} OVR, {player['age']} yo, {player['position'].upper()})")
            for pick in parsed_data['team1'].get('picks', []):
                year_str = str(pick['year']) if pick['year'] else "Future"
                pick_str = f"P{pick['pick']}" if pick['pick'] else ""
                team1_summary.append(f"{year_str} R{pick['round']} {pick_str}".strip())
            
            # Team 2 assets
            for player in parsed_data['team2'].get('players', []):
                team2_summary.append(f"{player['name']} ({player['ovr']} OVR, {player['age']} yo, {player['position'].upper()})")
            for pick in parsed_data['team2'].get('picks', []):
                year_str = str(pick['year']) if pick['year'] else "Future"
                pick_str = f"P{pick['pick']}" if pick['pick'] else ""
                team2_summary.append(f"{year_str} R{pick['round']} {pick_str}".strip())
            
            analysis_prompt = f"""
Analyze this Madden NFL trade:

Team 1 trades: {', '.join(team1_summary)} (Total Value: {team1_value:,})
Team 2 trades: {', '.join(team2_summary)} (Total Value: {team2_value:,})

Value difference: {abs(team1_value - team2_value):,} points

Provide a concise analysis (2-3 sentences) covering:
1. Which team benefits more and why
2. Key factors (age, position value, draft capital)
3. Overall assessment of trade fairness

Keep it under 200 words and focus on Madden franchise value.
"""
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a Madden franchise mode expert analyzing trades for long-term team building."},
                    {"role": "user", "content": analysis_prompt}
                ],
                max_tokens=200,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            print(f"Trade analysis error: {e}")
            return "Analysis temporarily unavailable. Trade values calculated successfully."

# Global instance
trade_parser = TradeParser()
