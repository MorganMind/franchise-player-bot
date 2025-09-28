import math
from config.settings import (
    BASE_CONSTANT, OVR_COEFFICIENT, AGE_COEFFICIENT, AGE_BASELINE,
    DEV_OFFSETS, POSITION_OFFSETS, DRAFT_PICK_VALUES, PLAYER_VALUE_MULTIPLIER
)

class Player:
    def __init__(self, name, ovr, age, dev_trait, position, years_left=3, cap_hit=0):
        self.name = name
        self.ovr = ovr
        self.age = age
        self.dev_trait = dev_trait.lower()
        self.position = position.lower()
        self.years_left = years_left
        self.cap_hit = cap_hit
    
    def calculate_value(self):
        """Calculate player trade value using log-scale formula"""
        # Get development offset
        dev_offset = DEV_OFFSETS.get(self.dev_trait, -0.400)  # default to normal (updated)
        
        # Get position offset
        pos_offset = POSITION_OFFSETS.get(self.position, -1.0)  # default to mid-tier
        
        # Calculate age coefficient - boost for younger players
        if self.age < AGE_BASELINE:
            # Younger players get a boost: +0.138 for each year under 26 (instead of -0.138)
            age_coefficient = 0.138
        else:
            # Older players still get penalized
            age_coefficient = AGE_COEFFICIENT
        
        # Calculate log value
        log_value = (
            BASE_CONSTANT + 
            OVR_COEFFICIENT * self.ovr + 
            age_coefficient * (self.age - AGE_BASELINE) + 
            dev_offset + 
            pos_offset
        )
        
        # Convert from log scale to actual value
        base_value = math.exp(log_value) - 1
        
        # Apply player multiplier (2x to double player values)
        value = base_value * PLAYER_VALUE_MULTIPLIER
        
        # Contract adjustment (optional - reduce value for expensive contracts)
        if self.cap_hit > 20:  # $20M+
            value *= 0.9
        elif self.cap_hit > 30:  # $30M+
            value *= 0.8
        
        return max(1, int(value))  # Ensure minimum value of 1
    
    def get_details(self):
        """Get formatted player details"""
        value = self.calculate_value()
        return {
            'name': self.name,
            'ovr': self.ovr,
            'age': self.age,
            'dev_trait': self.dev_trait.title(),
            'position': self.position.upper(),
            'value': value,
            'years_left': self.years_left,
            'cap_hit': self.cap_hit
        }

class DraftPick:
    def __init__(self, round_num, pick_num=None, year=None, is_next_year=False):
        # Handle "Next" year logic - if it's next year, discount by 1 round
        if is_next_year and year is None:
            year = 2026  # Next year from 2025
        elif is_next_year and year is not None:
            year = year + 1  # Add one year to specified year
        
        # If year not specified, assume current year (2025)
        if year is None:
            self.year = 2025
        else:
            self.year = max(2025, min(2030, year))  # Clamp year between 2025-2030
        
        # Apply 1-round discount for future years
        years_ahead = self.year - 2025
        if years_ahead > 0:
            # Discount by 1 round per year ahead
            adjusted_round = round_num + years_ahead
            self.round = max(1, min(7, adjusted_round))  # Clamp round between 1-7
        else:
            self.round = max(1, min(7, round_num))  # Clamp round between 1-7
        
        # If pick number not specified, use middle of round as estimate
        if pick_num is None:
            self.pick = 16  # Middle of a 32-team round
        else:
            self.pick = max(1, min(32, pick_num))  # Clamp pick between 1-32
            
        self.overall_pick = self._calculate_overall_pick()
    
    def _calculate_overall_pick(self):
        """Convert round and pick number to overall pick"""
        return (self.round - 1) * 32 + self.pick
    
    def calculate_value(self):
        """Get draft pick trade value with safety checks - NO MULTIPLIER"""
        # Get base value from chart
        base_value = DRAFT_PICK_VALUES.get(self.overall_pick, 5)  # Default minimum of 5
        
        # Adjust for future years (10% discount per year)
        years_out = self.year - 2025
        discount = max(0.1, 0.9 ** years_out)  # Never discount below 10%
        
        # Calculate final value (NO multiplier for picks)
        final_value = int(base_value * discount)
        
        # Ensure minimum value of 1
        return max(1, final_value)
    
    def get_details(self):
        """Get formatted draft pick details"""
        pick_desc = f"Pick {self.pick}" if self.pick != 16 else "Mid-Round Pick"
        return {
            'description': f"{self.year} Round {self.round} {pick_desc}",
            'overall': self.overall_pick,
            'value': self.calculate_value()
        }

def parse_player_input(player_string):
    """Parse player input string to extract attributes"""
    # Example formats:
    # "Patrick Mahomes, 99 OVR, 28 years, X-Factor, QB"
    # "Mahomes 99ovr 28yo xfactor qb"
    
    # Remove Discord emojis
    import re
    player_string = re.sub(r'<:[^:]+:[0-9]+>', '', player_string).strip()
    
    parts = player_string.replace(',', ' ').split()
    
    # Initialize defaults
    name_parts = []
    ovr = 80
    age = 26
    dev = 'normal'
    position = 'wr'
    
    for part in parts:
        part_lower = part.lower()
        
        # Check for OVR
        if 'ovr' in part_lower or 'ovl' in part_lower or (part.isdigit() and 50 <= int(part) <= 99):
            ovr = int(''.join(filter(str.isdigit, part)))
        
        # Check for age
        elif any(x in part_lower for x in ['year', 'yo', 'yrs', 'age']) or (part.isdigit() and 18 <= int(part) <= 45):
            age = int(''.join(filter(str.isdigit, part)))
        
        # Check for dev trait
        elif part_lower in ['x-factor', 'xfactor', 'xf', 'superstar', 'ss', 'star', 'normal']:
            if part_lower in ['xf', 'x-factor', 'xfactor']:
                dev = 'x-factor'
            elif part_lower in ['ss', 'superstar']:
                dev = 'superstar'
            else:
                dev = part_lower
        
        # Check for position
        elif part_lower in POSITION_OFFSETS or part_lower in ['hb', 'rg', 'lg']:
            position = part_lower
        
        # Otherwise, it's probably part of the name
        else:
            name_parts.append(part)
    
    name = ' '.join(name_parts) if name_parts else "Player"
    
    return Player(name, ovr, age, dev, position)

def parse_draft_pick_input(pick_string):
    """Parse draft pick input string"""
    # Example formats:
    # "2025 R1 P15" or "2025 1st round 15th pick" or "1.15" or "2nd round" or "Next 1st round"
    
    # Remove Discord emojis
    import re
    pick_string = re.sub(r'<:[^:]+:[0-9]+>', '', pick_string).strip()
    
    parts = pick_string.replace(',', ' ').replace('.', ' ').split()
    
    year = None
    round_num = 1
    pick_num = None
    is_next_year = False
    
    for i, part in enumerate(parts):
        # Check for "Next" year indicator
        if part.lower() in ['next', 'nexts']:
            is_next_year = True
        
        # Check for year
        elif part.isdigit() and 2025 <= int(part) <= 2030:
            year = int(part)
        
        # Check for round
        elif 'r' in part.lower() or 'round' in part.lower():
            try:
                round_num = int(''.join(filter(str.isdigit, part)))
            except:
                pass
        elif part.lower() in ['1st', 'first']:
            round_num = 1
        elif part.lower() in ['2nd', 'second']:
            round_num = 2
        elif part.lower() in ['3rd', 'third']:
            round_num = 3
        elif part.lower() in ['4th', 'fourth']:
            round_num = 4
        elif part.lower() in ['5th', 'fifth']:
            round_num = 5
        elif part.lower() in ['6th', 'sixth']:
            round_num = 6
        elif part.lower() in ['7th', 'seventh']:
            round_num = 7
        elif i > 0 and parts[i-1].isdigit() and 1 <= int(part) <= 7:
            round_num = int(part)
        
        # Check for pick
        elif 'p' in part.lower() or 'pick' in part.lower():
            try:
                pick_num = int(''.join(filter(str.isdigit, part)))
            except:
                pass
        elif part.isdigit() and 1 <= int(part) <= 32:
            if round_num is not None and pick_num is None:  # Assume it's the pick number
                pick_num = int(part)
    
    return DraftPick(round_num, pick_num, year, is_next_year)
