import os
from dotenv import load_dotenv

load_dotenv()

# Discord Configuration
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GUILD_ID = None  # We'll set this later, or leave None for global commands

# OpenAI Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Trade Calculator Settings (we'll expand this)
TRADE_CALC_WEIGHTS = {
    'age': 0.15,
    'overall': 0.30,
    'speed': 0.20,
    'dev_trait': 0.15,
    'position': 0.10,
    'contract': 0.10
}

# System prompt for OpenAI
SYSTEM_PROMPT = """You are a Madden NFL trade calculator assistant. You help users evaluate player trades based on player ratings, age, development traits, contracts, and draft pick values. Provide fair, analytical responses about trade values."""

# Trade Calculator Constants
BASE_CONSTANT = 0.0
OVR_COEFFICIENT = 0.1
AGE_COEFFICIENT = 0.138
AGE_BASELINE = 26

# Development trait offsets
DEV_OFFSETS = {
    'normal': -0.400,
    'star': 0.0,
    'superstar': 0.400,
    'x-factor': 0.800
}

# Position offsets
POSITION_OFFSETS = {
    'qb': 1.0,
    'hb': 0.5,
    'wr': 0.3,
    'te': 0.2,
    'lt': 0.4,
    'lg': 0.2,
    'c': 0.2,
    'rg': 0.2,
    'rt': 0.4,
    'le': 0.3,
    're': 0.3,
    'dt': 0.2,
    'lolb': 0.3,
    'mlb': 0.3,
    'rolb': 0.3,
    'cb': 0.4,
    'fs': 0.3,
    'ss': 0.3,
    'k': -0.5,
    'p': -0.5
}

# Draft pick values (approximate)
DRAFT_PICK_VALUES = {
    1: 100, 2: 80, 3: 70, 4: 60, 5: 55, 6: 50, 7: 45, 8: 40, 9: 35, 10: 30,
    11: 28, 12: 26, 13: 24, 14: 22, 15: 20, 16: 18, 17: 16, 18: 14, 19: 12, 20: 10,
    21: 9, 22: 8, 23: 7, 24: 6, 25: 5, 26: 4, 27: 3, 28: 2, 29: 1, 30: 1,
    31: 1, 32: 1
}

PLAYER_VALUE_MULTIPLIER = 1.0

# Position mapping for validation
POSITION_MAPPING = {
    'qb': 'qb', 'quarterback': 'qb',
    'hb': 'hb', 'running back': 'hb', 'rb': 'hb',
    'wr': 'wr', 'wide receiver': 'wr',
    'te': 'te', 'tight end': 'te',
    'lt': 'lt', 'left tackle': 'lt',
    'lg': 'lg', 'left guard': 'lg',
    'c': 'c', 'center': 'c',
    'rg': 'rg', 'right guard': 'rg',
    'rt': 'rt', 'right tackle': 'rt',
    'le': 'le', 'left end': 'le',
    're': 're', 'right end': 're',
    'dt': 'dt', 'defensive tackle': 'dt',
    'lolb': 'lolb', 'left outside linebacker': 'lolb',
    'mlb': 'mlb', 'middle linebacker': 'mlb',
    'rolb': 'rolb', 'right outside linebacker': 'rolb',
    'cb': 'cb', 'cornerback': 'cb',
    'fs': 'fs', 'free safety': 'fs',
    'ss': 'ss', 'strong safety': 'ss',
    'k': 'k', 'kicker': 'k',
    'p': 'p', 'punter': 'p'
}

# Default values for validation
DEFAULT_PLAYER_VALUES = {
    'ovr': 70,
    'age': 25,
    'dev_trait': 'normal',
    'position': 'hb',
    'years_left': 3,
    'cap_hit': 0
}

DEFAULT_PICK_VALUES = {
    'round': 1,
    'pick': 1,
    'year': 2024
}
