import discord
from discord.ext import commands
import asyncio
import logging
from config.settings import DISCORD_TOKEN

# Set up more detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Bot setup with intents
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True   # Required to see guild information
intents.presences = True  # Required to see user activities (streaming, playing games, etc.)
# Note: members and presences intents require special permissions in Discord Developer Portal

class MaddenBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix='!',
            intents=intents,
            description='Madden NFL Companion Bot'
        )
    
    async def setup_hook(self):
        """This is called when the bot starts up"""
        print("Setting up bot...")
        
        # Load our trade calculator cog
        try:
            await self.load_extension('cogs.trade_calculator')
            print("✅ Trade calculator cog loaded")
        except Exception as e:
            print(f"❌ Failed to load trade calculator cog: {e}")
            return
        
        # Load our points system cog (Supabase version)
        try:
            await self.load_extension('cogs.points_system_supabase')
            print("✅ Points system cog (Supabase) loaded")
        except Exception as e:
            print(f"❌ Failed to load points system cog: {e}")
            return
        
        # Load our spending system cog (Supabase version)
        try:
            await self.load_extension('cogs.spending_system_supabase')
            print("✅ Spending system cog (Supabase) loaded")
        except Exception as e:
            print(f"❌ Failed to load spending system cog: {e}")
            return
        
        # Load our stream manager cog
        try:
            await self.load_extension('cogs.stream_manager')
            print("✅ Stream manager cog loaded")
        except Exception as e:
            print(f"❌ Failed to load stream manager cog: {e}")
            return
        
        # Load our GOTW system cog
        try:
            await self.load_extension('cogs.gotw_system')
            print("✅ GOTW system cog loaded")
        except Exception as e:
            print(f"❌ Failed to load GOTW system cog: {e}")
            return
        
        # Load our NFL Schedule cog
        try:
            await self.load_extension('cogs.nfl_schedule')
            print("✅ NFL Schedule cog loaded")
        except Exception as e:
            print(f"❌ Failed to load NFL Schedule cog: {e}")
            return
        
        # Load our Team Claim System cog
        try:
            await self.load_extension('cogs.team_claim_system')
            print("✅ Team Claim System cog loaded successfully")
        except Exception as e:
            print(f"❌ Failed to load Team Claim System cog: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # Sync slash commands
        try:
            print("🔄 Starting command sync...")
            # Force sync commands to Discord
            synced = await self.tree.sync()
            print(f"✅ Synced {len(synced)} command(s)")
            for cmd in synced:
                print(f"  - {cmd.name}")
            print("✅ Command sync completed successfully!")
        except Exception as e:
            print(f"❌ Failed to sync commands: {e}")
            import traceback
            traceback.print_exc()
    
    async def on_ready(self):
        print(f'✅ {self.user} has connected to Discord!')
        print(f'✅ Bot is in {len(self.guilds)} guilds')
        print(f'🚀 Bot version: 2025-10-03-v2 (Team Claim System Enabled)')
        for guild in self.guilds:
            print(f"  - {guild.name} (ID: {guild.id})")
        
        # Perform per-guild sync so new/updated slash commands appear instantly
        try:
            for guild in self.guilds:
                print(f"🔄 Syncing commands for guild: {guild.name} ({guild.id})")
                # Copy global commands to this guild and sync (instant availability)
                self.tree.copy_global_to(guild=guild)
                guild_synced = await self.tree.sync(guild=guild)
                print(f"✅ Guild sync complete: {len(guild_synced)} command(s) for {guild.name}")
        except Exception as e:
            print(f"❌ Failed per-guild sync: {e}")
            import traceback
            traceback.print_exc()

        # List all available commands
        print(f"📋 Available commands: {len(self.tree.get_commands())}")
        for cmd in self.tree.get_commands():
            print(f"  - /{cmd.name}")
    
    async def on_error(self, event, *args, **kwargs):
        print(f"❌ An error occurred in {event}")
        import traceback
        traceback.print_exc()

# Create bot instance
bot = MaddenBot()

if __name__ == '__main__':
    if not DISCORD_TOKEN:
        print("❌ DISCORD_TOKEN not found in .env file!")
    else:
        print("🚀 Starting bot...")
        bot.run(DISCORD_TOKEN)
