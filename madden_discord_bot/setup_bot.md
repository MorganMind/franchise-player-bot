# 🤖 Bot Setup Guide

## Adding the Bot to Your Discord Server

1. **Go to Discord Developer Portal**
   - Visit: https://discord.com/developers/applications
   - Find your bot application

2. **Get the Bot Invite Link**
   - Go to "OAuth2" → "URL Generator"
   - Select scopes: `bot` and `applications.commands`
   - Select permissions:
     - Send Messages
     - Use Slash Commands
     - Add Reactions
     - Embed Links
     - Read Message History
     - Manage Messages (for updating vote cards)
   - Copy the generated URL and open it in your browser

3. **Invite the Bot**
   - Select your Discord server
   - Authorize the bot

## Creating Channels for GOTW

Once the bot is in your server, you can create dedicated channels:

### Option 1: Manual Channel Creation
1. Create a new channel called `#game-of-the-week` or `#gotw`
2. Set appropriate permissions for who can view/vote
3. Use `/gotw create DAL PHI` in that channel to start

### Option 2: Bot-Assisted Setup
The bot can help create channels if you give it the right permissions. You would need to:
1. Give the bot "Manage Channels" permission
2. Use a command like `/setup-gotw` (we can add this feature)

## Testing the GOTW System

Once the bot is in your server:

1. **List Teams**: `/gotw list`
2. **Create a Matchup**: `/gotw create DAL PHI`
3. **Vote**: Click the buttons on the card
4. **Check Results**: `/gotw results`

## Required Bot Permissions

Make sure your bot has these permissions:
- ✅ Send Messages
- ✅ Use Slash Commands  
- ✅ Add Reactions
- ✅ Embed Links
- ✅ Read Message History
- ✅ Manage Messages (for updating vote cards)

## Troubleshooting

**"Bot is in 0 guilds"**: The bot hasn't been invited to any servers yet.

**"Missing Access" errors**: The bot needs "Manage Messages" permission to update vote cards.

**Privileged Intents error**: The bot now uses only default intents, so this should be resolved.

## Next Steps

1. Invite the bot to your Discord server using the OAuth2 URL
2. Create a channel for GOTW discussions
3. Test the system with `/gotw create DAL PHI`
4. Have users vote using the interactive buttons!

The GOTW system is fully functional and ready to use once the bot is properly invited to your server.










