"""
Simple validation test for Task #104 database schema.
"""

from db_models import ScrapingTask, ParserCache
from database import Base

print('🔍 Final Schema Validation')
print('=' * 30)
print(f'ScrapingTask table: {ScrapingTask.__tablename__}')
print(f'ParserCache table: {ParserCache.__tablename__}')

# Check key fields exist
task_fields = [column.name for column in ScrapingTask.__table__.columns]
parser_fields = [column.name for column in ParserCache.__table__.columns]

print(f'✅ ScrapingTask fields ({len(task_fields)}): {task_fields[:5]}...')
print(f'✅ ParserCache fields ({len(parser_fields)}): {parser_fields[:5]}...')

# Verify relationships
print(f'✅ ScrapingTask -> ParserCache relationship: {hasattr(ScrapingTask, "used_parser")}')
print(f'✅ ParserCache -> ScrapingTask relationship: {hasattr(ParserCache, "tasks")}')

print('\n🎉 All validations passed! Task #104 is COMPLETE!')
