import sqlite3

conn = sqlite3.connect('confessions.db')
cursor = conn.cursor()

# Check if comments table exists
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='comments'")
print('Comments table exists:', cursor.fetchone() is not None)

# Check comments table structure
cursor.execute('PRAGMA table_info(comments)')
print('Comments table structure:')
for row in cursor.fetchall():
    print(row)

# Count total comments
cursor.execute('SELECT COUNT(*) FROM comments')
print('Total comments:', cursor.fetchone()[0])

# Show recent comments if any
cursor.execute('SELECT comment_id, post_id, content, user_id, timestamp FROM comments ORDER BY comment_id DESC LIMIT 5')
print('Recent comments:')
for row in cursor.fetchall():
    print(row)

# Check recent posts
cursor.execute('SELECT post_id, content, approved FROM posts ORDER BY post_id DESC LIMIT 3')
print('\nRecent posts:')
for row in cursor.fetchall():
    print(f"Post {row[0]}: {row[1][:50]}... (approved: {row[2]})")

conn.close()
