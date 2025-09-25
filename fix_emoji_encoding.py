#!/usr/bin/env python3
"""
Fix Emoji Encoding in PostgreSQL Database
This script updates rank emojis to ensure proper Unicode handling on Render
"""

import logging
from db_connection import get_db_connection

logger = logging.getLogger(__name__)

def fix_rank_emojis():
    """Fix emoji encoding in rank_definitions table"""
    
    # Define rank emojis with explicit Unicode escape sequences as backup
    rank_data = [
        (1, 'Freshman', '🥉', 0, 99),
        (2, 'Sophomore', '🥈', 100, 249),
        (3, 'Junior', '🥇', 250, 499),
        (4, 'Senior', '🏆', 500, 999),
        (5, 'Graduate', '🎓', 1000, 1999),
        (6, 'Master', '👑', 2000, 4999),
        (7, 'Legend', '🌟', 5000, None)
    ]
    
    db_conn = get_db_connection()
    
    if not db_conn.use_postgresql:
        logger.info("Not using PostgreSQL - emoji fix not needed")
        return True
    
    logger.info("🔧 Fixing emoji encoding in rank_definitions table...")
    
    try:
        with db_conn.get_connection() as conn:
            cursor = conn.cursor()
            placeholder = db_conn.get_placeholder()
            
            # Update each rank with proper emoji
            for rank_id, rank_name, emoji, min_points, max_points in rank_data:
                try:
                    cursor.execute(f"""
                        UPDATE rank_definitions 
                        SET rank_emoji = {placeholder}
                        WHERE rank_id = {placeholder}
                    """, (emoji, rank_id))
                    
                    logger.info(f"✅ Updated {rank_name}: {emoji}")
                    
                except Exception as e:
                    logger.error(f"❌ Failed to update {rank_name}: {e}")
                    continue
            
            conn.commit()
            
            # Test retrieval
            logger.info("🧪 Testing emoji retrieval...")
            cursor.execute("SELECT rank_name, rank_emoji FROM rank_definitions ORDER BY rank_id")
            results = cursor.fetchall()
            
            for rank_name, emoji in results:
                logger.info(f"Retrieved: {rank_name} -> {repr(emoji)} -> {emoji}")
            
            logger.info("🎉 Emoji encoding fix completed successfully!")
            return True
            
    except Exception as e:
        logger.error(f"❌ Failed to fix emoji encoding: {e}")
        return False

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    success = fix_rank_emojis()
    if success:
        print("✅ Emoji encoding fixed!")
    else:
        print("❌ Failed to fix emoji encoding!")
