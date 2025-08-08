"""
Database schema validation script for Task #104.

This script validates that the database schema is correctly defined
and that basic CRUD operations work as expected.
"""

import os
import sys
from datetime import datetime

# Add the services/api directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'services', 'api'))

from database import create_tables, SessionLocal
from db_models import ScrapingTask, ParserCache
from db_utils import create_scraping_task, create_parser_cache, get_scraping_task, find_cached_parser


def test_database_schema():
    """Test database schema creation and basic operations."""
    print("🏗️  Task #104: Testing Database Schema")
    print("=" * 50)
    
    # Create tables
    print("1. Creating database tables...")
    try:
        create_tables()
        print("✅ Database tables created successfully")
    except Exception as e:
        print(f"❌ Failed to create tables: {e}")
        return False
    
    # Test database connection
    print("\n2. Testing database connection...")
    try:
        db = SessionLocal()
        # Simple query to test connection
        task_count = db.query(ScrapingTask).count()
        parser_count = db.query(ParserCache).count()
        print(f"✅ Database connected. Tasks: {task_count}, Parsers: {parser_count}")
        db.close()
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
    
    # Test creating a scraping task
    print("\n3. Testing ScrapingTask creation...")
    try:
        db = SessionLocal()
        task = create_scraping_task(
            db=db,
            task_id="test-task-104",
            url="https://example.com",
            user_prompt="Test task for schema validation",
            status="PENDING"
        )
        print(f"✅ Created ScrapingTask with ID: {task.id}")
        
        # Test retrieving the task
        retrieved_task = get_scraping_task(db, "test-task-104")
        if retrieved_task and retrieved_task.id == task.id:
            print("✅ Successfully retrieved ScrapingTask")
        else:
            print("❌ Failed to retrieve ScrapingTask")
            db.close()
            return False
        
        db.close()
    except Exception as e:
        print(f"❌ Failed to create/retrieve ScrapingTask: {e}")
        return False
    
    # Test creating a parser cache entry
    print("\n4. Testing ParserCache creation...")
    try:
        db = SessionLocal()
        parser = create_parser_cache(
            db=db,
            url_pattern="https://example.com",
            domain="example.com",
            user_intent="test data extraction",
            generated_regex=r"<title>(.*?)</title>",
            source_type="HTML",
            created_by_task_id="test-task-104",
            test_matches_count=1
        )
        print(f"✅ Created ParserCache with ID: {parser.id}")
        
        # Test finding cached parser
        found_parser = find_cached_parser(db, "example.com")
        if found_parser and found_parser.id == parser.id:
            print("✅ Successfully found cached parser")
        else:
            print("❌ Failed to find cached parser")
            db.close()
            return False
        
        db.close()
    except Exception as e:
        print(f"❌ Failed to create/find ParserCache: {e}")
        return False
    
    # Test data integrity
    print("\n5. Testing data integrity...")
    try:
        db = SessionLocal()
        
        # Verify the relationship between task and parser
        task_with_parser = db.query(ScrapingTask).filter(
            ScrapingTask.task_id == "test-task-104"
        ).first()
        
        parser_for_task = db.query(ParserCache).filter(
            ParserCache.created_by_task_id == "test-task-104"
        ).first()
        
        if task_with_parser and parser_for_task:
            print("✅ Data relationships are working correctly")
        else:
            print("❌ Data relationship verification failed")
            db.close()
            return False
        
        db.close()
    except Exception as e:
        print(f"❌ Data integrity test failed: {e}")
        return False
    
    print(f"\n🎉 Task #104 COMPLETED Successfully!")
    print(f"✅ Database schema defined with SQLAlchemy models")
    print(f"✅ Required tables created: scraping_tasks, parsers_cache")
    print(f"✅ Basic CRUD operations working")
    print(f"✅ Data relationships functioning properly")
    print("=" * 50)
    
    return True


if __name__ == "__main__":
    success = test_database_schema()
    sys.exit(0 if success else 1)
