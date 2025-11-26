"""Test RAG endpoints"""
import pytest
from unittest.mock import Mock, patch

def test_rag_query_without_auth(client):
    """Test RAG query without authentication"""
    response = client.post(
        "/api/rag/query",
        json={"query": "What is the PTO policy?", "top_k": 3}
    )
    
    assert response.status_code == 403      

@patch('api.rag.pipeline')
def test_rag_query_with_auth(mock_pipeline, client, auth_headers):
    """Test RAG query with authentication"""
    # Mock the pipeline response
    mock_result = Mock()
    mock_result.answer = "PTO policy answer"
    mock_result.metadata = [
        {
            "company": "Crouse Medical Practice",
            "filename": "handbook.pdf",
            "chunk_id": "1",
            "text": "Sample text",
            "doc_title": "Employee Handbook",
            "section_title": "PTO"
        }
    ]
    mock_pipeline.run.return_value = mock_result
    
    response = client.post(
        "/api/rag/query",
        headers=auth_headers,
        json={"query": "What is the PTO policy?", "top_k": 3}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "answer" in data
    assert "sources" in data
    assert "company" in data

@patch('api.rag.pipeline')
def test_rag_query_filters_by_company(mock_pipeline, client, auth_headers):
    """Test that RAG queries are filtered by user's company"""
    mock_result = Mock()
    mock_result.answer = "Answer"
    mock_result.metadata = []
    mock_pipeline.run.return_value = mock_result
    
    response = client.post(
        "/api/rag/query",
        headers=auth_headers,
        json={"query": "Test query", "top_k": 3}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["company"] == "Crouse Medical Practice"