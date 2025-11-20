"""Test database connection and setup"""
import pytest
from db.connection import get_db, init_db, Base

def test_get_db():
    """Test database session creation"""
    db_gen = get_db()
    db = next(db_gen)
    assert db is not None
    db.close()

def test_init_db():
    """Test database initialization"""
    # Should not raise any errors
    init_db()