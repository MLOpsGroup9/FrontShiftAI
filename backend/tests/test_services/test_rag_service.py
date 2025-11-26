"""Test RAG service"""
import pytest
from services.rag_service import normalize_metadata_company_name

def test_normalize_metadata_company_name_exact_match():
    """Test exact company name matching"""
    assert normalize_metadata_company_name(
        "Crouse Medical Practice",
        "Crouse Medical Practice"
    ) is True

def test_normalize_metadata_company_name_case_insensitive():
    """Test case-insensitive matching"""
    assert normalize_metadata_company_name(
        "crouse medical practice",
        "Crouse Medical Practice"
    ) is True

def test_normalize_metadata_company_name_substring():
    """Test substring matching"""
    assert normalize_metadata_company_name(
        "Healthcare Crouse Medical Practice",
        "Crouse Medical Practice"
    ) is True

def test_normalize_metadata_company_name_mapping():
    """Test company name mapping"""
    assert normalize_metadata_company_name(
        "healthcare crouse medical practice",
        "Crouse Medical Practice"
    ) is True

def test_normalize_metadata_company_name_no_match():
    """Test non-matching companies"""
    assert normalize_metadata_company_name(
        "Different Company",
        "Crouse Medical Practice"
    ) is False

def test_normalize_metadata_company_name_empty():
    """Test with empty strings"""
    assert normalize_metadata_company_name("", "Crouse Medical Practice") is False
    assert normalize_metadata_company_name("Crouse Medical Practice", "") is False
    assert normalize_metadata_company_name("", "") is False