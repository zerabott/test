import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv('DATABASE_URL')
print(f"Database URL: {DATABASE_URL[:50]}...")

try:
    print("Attempting to connect to PostgreSQL...")
    conn = psycopg2.connect(DATABASE_URL)
    print("✅ Connected successfully!")
    
    cursor = conn.cursor()
    
    # Test query
    cursor.execute("SELECT version();")
    version = cursor.fetchone()
    print(f"PostgreSQL version: {version[0]}")
    
    # Check if comments table exists
    cursor.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = 'comments'
        );
    """)
    comments_table_exists = cursor.fetchone()[0]
    print(f"Comments table exists: {comments_table_exists}")
    
    if comments_table_exists:
        # Count comments
        cursor.execute("SELECT COUNT(*) FROM comments;")
        comment_count = cursor.fetchone()[0]
        print(f"Total comments in PostgreSQL: {comment_count}")
        
        # Show recent comments
        cursor.execute("SELECT comment_id, post_id, content, user_id, timestamp FROM comments ORDER BY comment_id DESC LIMIT 5;")
        comments = cursor.fetchall()
        print("Recent comments:")
        for comment in comments:
            print(f"  {comment}")
    
    # Check posts
    cursor.execute("SELECT COUNT(*) FROM posts;")
    post_count = cursor.fetchone()[0]
    print(f"Total posts in PostgreSQL: {post_count}")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"❌ Connection failed: {e}")
    print(f"Error type: {type(e).__name__}")
