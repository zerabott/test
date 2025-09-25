import os
import psycopg2
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
print(f"Testing PostgreSQL connection...")
print(f"Database URL: {DATABASE_URL[:50]}...")

def test_connection_with_retry(max_attempts=5, delay=5):
    """Test PostgreSQL connection with retry logic"""
    for attempt in range(max_attempts):
        try:
            print(f"\n🔄 Attempt {attempt + 1}/{max_attempts}")
            
            # Try with different SSL modes
            connection_params = [
                DATABASE_URL,  # Original URL
                DATABASE_URL.replace('sslmode=require', 'sslmode=prefer'),
                DATABASE_URL.replace('sslmode=require', 'sslmode=allow'),
            ]
            
            for i, url in enumerate(connection_params):
                try:
                    print(f"  Testing connection variant {i + 1}...")
                    conn = psycopg2.connect(url)
                    
                    cursor = conn.cursor()
                    cursor.execute("SELECT version();")
                    version = cursor.fetchone()[0]
                    print(f"  ✅ Connected successfully!")
                    print(f"  PostgreSQL version: {version[:100]}...")
                    
                    # Test tables
                    cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
                    tables = [row[0] for row in cursor.fetchall()]
                    print(f"  Available tables: {tables}")
                    
                    # Check comments table specifically
                    if 'comments' in tables:
                        cursor.execute("SELECT COUNT(*) FROM comments;")
                        comment_count = cursor.fetchone()[0]
                        print(f"  Comments in database: {comment_count}")
                        
                        # Show recent comments
                        cursor.execute("SELECT comment_id, post_id, content, user_id FROM comments ORDER BY comment_id DESC LIMIT 3;")
                        comments = cursor.fetchall()
                        print("  Recent comments:")
                        for comment in comments:
                            print(f"    {comment}")
                    else:
                        print("  ⚠️ Comments table not found!")
                    
                    cursor.close()
                    conn.close()
                    return True
                    
                except psycopg2.OperationalError as e:
                    print(f"  ❌ Connection variant {i + 1} failed: {str(e)[:100]}...")
                    continue
                    
        except Exception as e:
            print(f"  ❌ Attempt {attempt + 1} failed: {e}")
            
        if attempt < max_attempts - 1:
            print(f"  ⏳ Waiting {delay} seconds before retry...")
            time.sleep(delay)
    
    print(f"\n❌ All connection attempts failed!")
    return False

def suggest_fixes():
    """Suggest potential fixes for connection issues"""
    print("\n🔧 POTENTIAL FIXES:")
    print("1. Check if your PostgreSQL server is running and accessible")
    print("2. Verify the DATABASE_URL credentials are correct")
    print("3. Check if there are connection limits on your database")
    print("4. Ensure your IP is whitelisted (if applicable)")
    print("5. Try restarting your database service")
    print("6. Check database server logs for errors")
    
    print("\n⚡ IMMEDIATE WORKAROUND:")
    print("We can temporarily modify the bot to:")
    print("- Force use SQLite for now")
    print("- Or provide a backup connection method")

if __name__ == "__main__":
    success = test_connection_with_retry()
    if not success:
        suggest_fixes()
