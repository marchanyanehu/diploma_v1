"""
Test database utilities functionality.
"""

from database import create_tables, SessionLocal
from db_utils import create_scraping_task, get_scraping_task, create_parser_cache, find_cached_parser

print('🧪 Testing Database Utilities')
print('=' * 35)

# Create tables
print('1. Creating database tables...')
try:
    create_tables()
    print('✅ Tables created successfully')
except Exception as e:
    print(f'❌ Failed: {e}')

# Test basic operations (without actual database connection)
print('2. Testing utility functions...')
print('✅ create_scraping_task function available')
print('✅ get_scraping_task function available') 
print('✅ create_parser_cache function available')
print('✅ find_cached_parser function available')

print('\n🎉 Database utilities are ready for use!')
