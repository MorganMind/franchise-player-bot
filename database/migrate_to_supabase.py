#!/usr/bin/env python3
"""
Migration script to move JSON data to Supabase
"""
import json
import os
import sys
import asyncio
from datetime import datetime
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables from the correct location
import os
env_path = os.path.join(os.path.dirname(__file__), '..', 'madden_discord_bot', '.env')
load_dotenv(env_path)

class SupabaseMigrator:
    def __init__(self):
        self.supabase_url = os.getenv('SUPABASE_URL')
        self.supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment variables")
        
        self.supabase: Client = create_client(self.supabase_url, self.supabase_key)
        self.data_dir = "madden_discord_bot/data"
    
    async def migrate_all(self):
        """Migrate all JSON data to Supabase"""
        print("🚀 Starting migration to Supabase...")
        
        try:
            # Apply database schema first
            await self.apply_schema()
            
            # Migrate each data type
            await self.migrate_users()
            await self.migrate_player_cards()
            await self.migrate_gotw()
            await self.migrate_nfl_schedule()
            await self.migrate_stream_links()
            await self.migrate_server_settings()
            
            print("✅ Migration completed successfully!")
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            raise
    
    async def apply_schema(self):
        """Apply the database schema"""
        print("📋 Applying database schema...")
        
        schema_file = "database/schema.sql"
        if os.path.exists(schema_file):
            with open(schema_file, 'r') as f:
                schema_sql = f.read()
            
            # Split by semicolon and execute each statement
            statements = [stmt.strip() for stmt in schema_sql.split(';') if stmt.strip()]
            
            for statement in statements:
                try:
                    result = self.supabase.rpc('exec_sql', {'sql': statement}).execute()
                    print(f"✅ Executed: {statement[:50]}...")
                except Exception as e:
                    print(f"⚠️ Warning executing statement: {e}")
        else:
            print("⚠️ Schema file not found, skipping schema application")
    
    async def migrate_users(self):
        """Migrate users and points data"""
        print("👥 Migrating users and points...")
        
        points_file = os.path.join(self.data_dir, "points.json")
        if not os.path.exists(points_file):
            print("⚠️ Points file not found, skipping users migration")
            return
        
        with open(points_file, 'r') as f:
            points_data = json.load(f)
        
        users_data = points_data.get("users", {})
        users_to_insert = []
        
        for user_id, user_data in users_data.items():
            if isinstance(user_data, dict):
                # New format
                users_to_insert.append({
                    "id": int(user_id),
                    "total_points": user_data.get("total", 0),
                    "stream_points": user_data.get("stream_points", 0),
                    "other_points": user_data.get("other_points", 0)
                })
            else:
                # Old format (just a number)
                users_to_insert.append({
                    "id": int(user_id),
                    "total_points": user_data,
                    "stream_points": 0,
                    "other_points": 0
                })
        
        if users_to_insert:
            # Insert users in batches
            batch_size = 100
            for i in range(0, len(users_to_insert), batch_size):
                batch = users_to_insert[i:i + batch_size]
                try:
                    result = self.supabase.table("users").upsert(batch).execute()
                    print(f"✅ Inserted {len(batch)} users (batch {i//batch_size + 1})")
                except Exception as e:
                    print(f"❌ Error inserting users batch: {e}")
        
        print(f"✅ Migrated {len(users_to_insert)} users")
    
    async def migrate_player_cards(self):
        """Migrate player cards data"""
        print("🃏 Migrating player cards...")
        
        cards_file = os.path.join(self.data_dir, "player_cards.json")
        if not os.path.exists(cards_file):
            print("⚠️ Player cards file not found, skipping cards migration")
            return
        
        with open(cards_file, 'r') as f:
            cards_data = json.load(f)
        
        users_data = cards_data.get("users", {})
        cards_to_insert = []
        
        for user_id, user_cards in users_data.items():
            if isinstance(user_cards, dict):
                for position, attributes in user_cards.items():
                    if isinstance(attributes, dict):
                        cards_to_insert.append({
                            "user_id": int(user_id),
                            "position": position,
                            "attributes": attributes
                        })
        
        if cards_to_insert:
            try:
                result = self.supabase.table("player_cards").upsert(cards_to_insert).execute()
                print(f"✅ Migrated {len(cards_to_insert)} player cards")
            except Exception as e:
                print(f"❌ Error inserting player cards: {e}")
        else:
            print("ℹ️ No player cards to migrate")
    
    async def migrate_gotw(self):
        """Migrate Game of the Week data"""
        print("🏈 Migrating Game of the Week data...")
        
        gotw_file = os.path.join(self.data_dir, "gotw.json")
        if not os.path.exists(gotw_file):
            print("⚠️ GOTW file not found, skipping GOTW migration")
            return
        
        with open(gotw_file, 'r') as f:
            gotw_data = json.load(f)
        
        gotw_to_insert = []
        
        # Handle different GOTW data structures
        if isinstance(gotw_data, dict):
            for key, value in gotw_data.items():
                if isinstance(value, dict):
                    gotw_to_insert.append({
                        "week": value.get("week", 1),
                        "season": value.get("season", 2024),
                        "home_team": value.get("home_team", ""),
                        "away_team": value.get("away_team", ""),
                        "home_score": value.get("home_score", 0),
                        "away_score": value.get("away_score", 0),
                        "is_completed": value.get("is_completed", False)
                    })
        
        if gotw_to_insert:
            try:
                result = self.supabase.table("gotw").upsert(gotw_to_insert).execute()
                print(f"✅ Migrated {len(gotw_to_insert)} GOTW entries")
            except Exception as e:
                print(f"❌ Error inserting GOTW data: {e}")
        else:
            print("ℹ️ No GOTW data to migrate")
    
    async def migrate_nfl_schedule(self):
        """Migrate NFL schedule data"""
        print("📅 Migrating NFL schedule...")
        
        schedule_file = os.path.join(self.data_dir, "nfl_schedule.json")
        if not os.path.exists(schedule_file):
            print("⚠️ NFL schedule file not found, skipping schedule migration")
            return
        
        with open(schedule_file, 'r') as f:
            schedule_data = json.load(f)
        
        schedule_to_insert = []
        
        if isinstance(schedule_data, list):
            for game in schedule_data:
                if isinstance(game, dict):
                    schedule_to_insert.append({
                        "week": game.get("week", 1),
                        "season": game.get("season", 2024),
                        "home_team": game.get("home_team", ""),
                        "away_team": game.get("away_team", ""),
                        "game_time": game.get("game_time"),
                        "is_completed": game.get("is_completed", False),
                        "home_score": game.get("home_score", 0),
                        "away_score": game.get("away_score", 0)
                    })
        
        if schedule_to_insert:
            try:
                result = self.supabase.table("nfl_schedule").upsert(schedule_to_insert).execute()
                print(f"✅ Migrated {len(schedule_to_insert)} NFL schedule entries")
            except Exception as e:
                print(f"❌ Error inserting NFL schedule: {e}")
        else:
            print("ℹ️ No NFL schedule data to migrate")
    
    async def migrate_stream_links(self):
        """Migrate stream links data"""
        print("📺 Migrating stream links...")
        
        streams_file = os.path.join(self.data_dir, "stream_links.json")
        if not os.path.exists(streams_file):
            print("⚠️ Stream links file not found, skipping stream links migration")
            return
        
        with open(streams_file, 'r') as f:
            streams_data = json.load(f)
        
        streams_to_insert = []
        
        if isinstance(streams_data, list):
            for stream in streams_data:
                if isinstance(stream, dict):
                    streams_to_insert.append({
                        "name": stream.get("name", ""),
                        "url": stream.get("url", ""),
                        "is_active": stream.get("is_active", True)
                    })
        
        if streams_to_insert:
            try:
                result = self.supabase.table("stream_links").upsert(streams_to_insert).execute()
                print(f"✅ Migrated {len(streams_to_insert)} stream links")
            except Exception as e:
                print(f"❌ Error inserting stream links: {e}")
        else:
            print("ℹ️ No stream links to migrate")
    
    async def migrate_server_settings(self):
        """Migrate server settings data"""
        print("⚙️ Migrating server settings...")
        
        points_file = os.path.join(self.data_dir, "points.json")
        if not os.path.exists(points_file):
            print("⚠️ Points file not found, skipping server settings migration")
            return
        
        with open(points_file, 'r') as f:
            points_data = json.load(f)
        
        server_settings = points_data.get("server_settings", {})
        settings_to_insert = []
        
        for guild_id, settings in server_settings.items():
            for setting_key, setting_value in settings.items():
                settings_to_insert.append({
                    "guild_id": int(guild_id),
                    "setting_key": setting_key,
                    "setting_value": setting_value
                })
        
        if settings_to_insert:
            try:
                result = self.supabase.table("server_settings").upsert(settings_to_insert).execute()
                print(f"✅ Migrated {len(settings_to_insert)} server settings")
            except Exception as e:
                print(f"❌ Error inserting server settings: {e}")
        else:
            print("ℹ️ No server settings to migrate")

async def main():
    """Main migration function"""
    try:
        migrator = SupabaseMigrator()
        await migrator.migrate_all()
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
