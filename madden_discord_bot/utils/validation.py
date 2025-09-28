from config.settings import (
    POSITION_MAPPING, DEV_OFFSETS, DEFAULT_PLAYER_VALUES, DEFAULT_PICK_VALUES
)
import logging

logger = logging.getLogger(__name__)

class DataValidator:
    """Validates and cleans player and pick data"""
    
    @staticmethod
    def validate_player_data(player_data):
        """Validate and clean player data with defaults"""
        validated = {}
        
        # Name validation
        name = player_data.get('name', '').strip()
        if not name:
            logger.warning("Missing player name, using 'Unknown Player'")
            name = "Unknown Player"
        validated['name'] = name
        
        # OVR validation (50-99)
        ovr = player_data.get('ovr')
        if ovr is None:
            logger.info(f"Missing OVR for {name}, using default {DEFAULT_PLAYER_VALUES['ovr']}")
            ovr = DEFAULT_PLAYER_VALUES['ovr']
        else:
            ovr = max(50, min(99, int(ovr)))  # Clamp between 50-99
            if ovr != player_data.get('ovr'):
                logger.warning(f"Adjusted OVR for {name} from {player_data.get('ovr')} to {ovr}")
        validated['ovr'] = ovr
        
        # Age validation (18-45)
        age = player_data.get('age')
        if age is None:
            logger.info(f"Missing age for {name}, using default {DEFAULT_PLAYER_VALUES['age']}")
            age = DEFAULT_PLAYER_VALUES['age']
        else:
            age = max(18, min(45, int(age)))  # Clamp between 18-45
            if age != player_data.get('age'):
                logger.warning(f"Adjusted age for {name} from {player_data.get('age')} to {age}")
        validated['age'] = age
        
        # Dev trait validation
        dev = player_data.get('dev', '').lower()
        if dev not in DEV_OFFSETS:
            logger.info(f"Invalid dev trait '{dev}' for {name}, using default '{DEFAULT_PLAYER_VALUES['dev']}'")
            dev = DEFAULT_PLAYER_VALUES['dev']
        validated['dev'] = dev
        
        # Position validation with mapping
        position = player_data.get('position', '').lower()
        mapped_position = POSITION_MAPPING.get(position)
        
        if not mapped_position:
            logger.warning(f"Unknown position '{position}' for {name}, using default '{DEFAULT_PLAYER_VALUES['position']}'")
            mapped_position = DEFAULT_PLAYER_VALUES['position']
        elif mapped_position != position:
            logger.info(f"Mapped position '{position}' to '{mapped_position}' for {name}")
        
        validated['position'] = mapped_position
        
        # Additional fields with defaults
        validated['years_left'] = player_data.get('years_left', DEFAULT_PLAYER_VALUES['years_left'])
        validated['cap_hit'] = player_data.get('cap_hit', DEFAULT_PLAYER_VALUES['cap_hit'])
        
        return validated
    
    @staticmethod
    def validate_pick_data(pick_data):
        """Validate and clean draft pick data with defaults"""
        validated = {}
        
        # Round validation (1-7)
        round_num = pick_data.get('round')
        if round_num is None:
            logger.info(f"Missing round number, using default {DEFAULT_PICK_VALUES['round']}")
            round_num = DEFAULT_PICK_VALUES['round']
        else:
            round_num = max(1, min(7, int(round_num)))  # Clamp between 1-7
            if round_num != pick_data.get('round'):
                logger.warning(f"Adjusted round from {pick_data.get('round')} to {round_num}")
        validated['round'] = round_num
        
        # Pick validation (1-32)
        pick_num = pick_data.get('pick')
        if pick_num is None:
            logger.info(f"Missing pick number, using default {DEFAULT_PICK_VALUES['pick']}")
            pick_num = DEFAULT_PICK_VALUES['pick']
        else:
            pick_num = max(1, min(32, int(pick_num)))  # Clamp between 1-32
            if pick_num != pick_data.get('pick'):
                logger.warning(f"Adjusted pick from {pick_data.get('pick')} to {pick_num}")
        validated['pick'] = pick_num
        
        # Year validation (2025-2030)
        year = pick_data.get('year')
        if year is None:
            logger.info(f"Missing year, using default {DEFAULT_PICK_VALUES['year']}")
            year = DEFAULT_PICK_VALUES['year']
        else:
            year = max(2025, min(2030, int(year)))  # Clamp between 2025-2030
            if year != pick_data.get('year'):
                logger.warning(f"Adjusted year from {pick_data.get('year')} to {year}")
        validated['year'] = year
        
        return validated
    
    @staticmethod
    def parse_position_context(text, position_guess):
        """Use context clues to disambiguate position abbreviations"""
        text_lower = text.lower()
        
        # SS could be Strong Safety or Superstar
        if position_guess == 'ss':
            # Look for defensive context
            if any(word in text_lower for word in ['safety', 'defense', 'db', 'secondary']):
                return 'safety'
            # Look for dev trait context
            elif any(word in text_lower for word in ['dev', 'trait', 'superstar']):
                return None  # Not a position
            # Default to safety if ambiguous
            else:
                return 'safety'
        
        # S could be Safety or Star
        elif position_guess == 's':
            if any(word in text_lower for word in ['safety', 'defense', 'fs', 'ss']):
                return 'safety'
            else:
                return None  # Probably star dev trait
        
        return position_guess

# Create global validator instance
validator = DataValidator()
