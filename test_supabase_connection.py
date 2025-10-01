#!/usr/bin/env python3
"""
Test script to verify Supabase connection and basic operations
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables from the correct location
load_dotenv('madden_discord_bot/.env')

def test_supabase_connection():
    """Test basic Supabase connection and operations"""
    try:
        from supabase import create_client, Client
        
        # Get credentials
        supabase_url = os.getenv('SUPABASE_URL')
        supabase_key = os.getenv('SUPABASE_ANON_KEY')
        
        if not supabase_url or not supabase_key:
            print("❌ SUPABASE_URL and SUPABASE_ANON_KEY must be set in environment variables")
            return False
        
        print(f"🔗 Connecting to Supabase: {supabase_url}")
        
        # Create client
        supabase: Client = create_client(supabase_url, supabase_key)
        
        # Test basic connection by querying a table
        print("📊 Testing database connection...")
        
        # Try to query users table
        try:
            result = supabase.table("users").select("id").limit(1).execute()
            print("✅ Successfully connected to Supabase!")
            print(f"📋 Users table accessible: {len(result.data)} users found")
            return True
        except Exception as e:
            print(f"⚠️ Users table query failed: {e}")
            print("💡 This might be normal if the table doesn't exist yet")
            
            # Try to create a test table to verify permissions
            try:
                test_data = {"id": 999999999, "total_points": 0}
                result = supabase.table("users").insert(test_data).execute()
                print("✅ Successfully created test user - connection working!")
                
                # Clean up test data
                supabase.table("users").delete().eq("id", 999999999).execute()
                print("🧹 Cleaned up test data")
                return True
            except Exception as create_error:
                print(f"❌ Failed to create test data: {create_error}")
                return False
        
    except ImportError:
        print("❌ Supabase library not installed. Run: pip install supabase")
        return False
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False

def test_environment_variables():
    """Test that all required environment variables are set"""
    print("🔍 Checking environment variables...")
    
    required_vars = [
        'DISCORD_TOKEN',
        'SUPABASE_URL', 
        'SUPABASE_ANON_KEY'
    ]
    
    optional_vars = [
        'OPENAI_API_KEY',
        'SUPABASE_SERVICE_ROLE_KEY'
    ]
    
    all_good = True
    
    for var in required_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: Set")
        else:
            print(f"❌ {var}: Missing (REQUIRED)")
            all_good = False
    
    for var in optional_vars:
        value = os.getenv(var)
        if value:
            print(f"✅ {var}: Set")
        else:
            print(f"⚠️ {var}: Not set (optional)")
    
    return all_good

def main():
    """Main test function"""
    print("🚀 Supabase Connection Test")
    print("=" * 40)
    
    # Test environment variables
    env_ok = test_environment_variables()
    print()
    
    if not env_ok:
        print("❌ Environment variables not properly configured")
        print("💡 Please check your .env file and ensure all required variables are set")
        return False
    
    # Test Supabase connection
    connection_ok = test_supabase_connection()
    print()
    
    if connection_ok:
        print("🎉 All tests passed! Supabase is ready to use.")
        print("💡 You can now run the migration script: python3 database/migrate_to_supabase.py")
    else:
        print("❌ Connection test failed")
        print("💡 Please check your Supabase credentials and project settings")
    
    return connection_ok

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
