"""
BhashaBridge — Database Initialization & Migration Script
Initializes all database tables (PostgreSQL or SQLite) and seeds
the curated educational corpus, vocabulary bank, milestones, and learner profiles.
"""

import sys
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.models.database import Base, engine, SessionLocal
from app.models.entities import (
    User, LanguageProfile, Milestone, Progress,
    VocabularyWord, GrammarConcept, LearningExample, PracticeQuestion
)
from app.models.seed import seed_database

def init_db():
    print("=" * 60)
    print(" BhashaBridge — Database Initialization & Migration")
    print(f" Target Database: {engine.url}")
    print("=" * 60)

    print("[1/3] Creating schema and tables...")
    Base.metadata.create_all(bind=engine)
    print("  -> Tables created successfully.")

    print("[2/3] Seeding initial data, vocabulary, and learning corpus...")
    db = SessionLocal()
    try:
        seed_database(db)
        print("  -> Seeding completed.")

        print("[3/3] Verifying database records:")
        users_count = db.query(User).count()
        profiles_count = db.query(LanguageProfile).count()
        milestones_count = db.query(Milestone).count()
        vocab_count = db.query(VocabularyWord).count()
        examples_count = db.query(LearningExample).count()
        concepts_count = db.query(GrammarConcept).count()

        print(f"  • Users:             {users_count}")
        print(f"  • Language Profiles: {profiles_count}")
        print(f"  • Milestones:        {milestones_count}")
        print(f"  • Vocabulary Words:  {vocab_count}")
        print(f"  • Learning Examples: {examples_count}")
        print(f"  • Grammar Concepts:  {concepts_count}")
        print("=" * 60)
        print(" Database is ready for high-accuracy learning and translation!")
        print("=" * 60)
    except Exception as e:
        print(f"[!] Error during database seeding: {e}")
        db.rollback()
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
