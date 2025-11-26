"""
Tests for Website Extraction Agent Nodes
"""
import pytest
from unittest.mock import patch, MagicMock
from agents.website_extraction.nodes import (
    parse_query_node,
    resolve_domain_node,
    brave_search_node,
    analyze_results_node,
    generate_answer_node,
    suggest_hr_ticket_node,
    format_response_node
)
from agents.website_extraction.state import WebsiteExtractionState
from db.models import Company


class TestParseQueryNode:
    """Test query parsing node"""
    
    def test_parse_basic_query(self, db_session):
        """Test parsing a basic query"""
        state: WebsiteExtractionState = {
            "user_email": "test@test.com",
            "company": "Test Corp",
            "user_message": "What are your business hours?",
            "original_query": None,
            "triggered_by": "direct",
            "search_topic": None,
            "search_keywords": [],
            "search_query": None,
            "info_type": None,
            "company_url": None,
            "company_domain": None,
            "domain_found": False,
            "brave_results": [],
            "search_successful": False,
            "search_error": None,
            "ranked_results": [],
            "best_match": None,
            "confidence_score": 0.0,
            "found_answer": False,
            "answer": None,
            "source_urls": [],
            "suggest_hr_ticket": False,
            "hr_ticket_suggestion": None,
            "agent_response": "",
            "search_time_ms": None,
            "error_message": None
        }
        
        result = parse_query_node(state, db_session)
        
        assert result["search_topic"] is not None
        assert isinstance(result["search_keywords"], list)
        assert result["search_query"] is not None
        assert result["info_type"] in ["contact", "hours", "services", "policies", "pricing", "locations", "general"]
    
    def test_parse_contact_query(self, db_session):
        """Test parsing contact-related query"""
        state: WebsiteExtractionState = {
            "user_email": "test@test.com",
            "company": "Test Corp",
            "user_message": "How can I contact your office?",
            "original_query": None,
            "triggered_by": "direct",
            "search_topic": None,
            "search_keywords": [],
            "search_query": None,
            "info_type": None,
            "company_url": None,
            "company_domain": None,
            "domain_found": False,
            "brave_results": [],
            "search_successful": False,
            "search_error": None,
            "ranked_results": [],
            "best_match": None,
            "confidence_score": 0.0,
            "found_answer": False,
            "answer": None,
            "source_urls": [],
            "suggest_hr_ticket": False,
            "hr_ticket_suggestion": None,
            "agent_response": "",
            "search_time_ms": None,
            "error_message": None
        }
        
        result = parse_query_node(state, db_session)
        
        assert "contact" in result["search_query"].lower() or result["info_type"] == "contact"
    
    def test_parse_fallback_on_llm_failure(self, db_session):
        """Test fallback when LLM fails"""
        with patch('agents.website_extraction.nodes.get_llm_client') as mock_llm:
            mock_llm.return_value.chat.side_effect = Exception("LLM error")
            
            state: WebsiteExtractionState = {
                "user_email": "test@test.com",
                "company": "Test Corp",
                "user_message": "What are your operating hours and contact information?",
                "original_query": None,
                "triggered_by": "direct",
                "search_topic": None,
                "search_keywords": [],
                "search_query": None,
                "info_type": None,
                "company_url": None,
                "company_domain": None,
                "domain_found": False,
                "brave_results": [],
                "search_successful": False,
                "search_error": None,
                "ranked_results": [],
                "best_match": None,
                "confidence_score": 0.0,
                "found_answer": False,
                "answer": None,
                "source_urls": [],
                "suggest_hr_ticket": False,
                "hr_ticket_suggestion": None,
                "agent_response": "",
                "search_time_ms": None,
                "error_message": None
            }
            
            result = parse_query_node(state, db_session)
            
            # Should still extract basic info
            assert result["search_topic"] is not None
            assert len(result["search_keywords"]) > 0


class TestResolveDomainNode:
    """Test domain resolution node"""
    
    def test_resolve_domain_success(self, db_session):
        """Test successful domain resolution"""
        company = Company(
            name="Test Company",
            domain="Healthcare",
            email_domain="testcompany.com",
            url="https://testcompany.com/handbook.pdf"
        )
        db_session.add(company)
        db_session.commit()
        
        state: WebsiteExtractionState = {
            "user_email": "test@test.com",
            "company": "Test Company",
            "user_message": "test",
            "original_query": None,
            "triggered_by": "direct",
            "search_topic": None,
            "search_keywords": [],
            "search_query": None,
            "info_type": None,
            "company_url": None,
            "company_domain": None,
            "domain_found": False,
            "brave_results": [],
            "search_successful": False,
            "search_error": None,
            "ranked_results": [],
            "best_match": None,
            "confidence_score": 0.0,
            "found_answer": False,
            "answer": None,
            "source_urls": [],
            "suggest_hr_ticket": False,
            "hr_ticket_suggestion": None,
            "agent_response": "",
            "search_time_ms": None,
            "error_message": None
        }
        
        result = resolve_domain_node(state, db_session)
        
        assert result["domain_found"] is True
        assert result["company_domain"] == "testcompany.com"
        assert result["company_url"] == "https://testcompany.com/handbook.pdf"
    
    def test_resolve_domain_not_found(self, db_session):
        """Test domain resolution when company not found"""
        state: WebsiteExtractionState = {
            "user_email": "test@test.com",
            "company": "Nonexistent Company",
            "user_message": "test",
            "original_query": None,
            "triggered_by": "direct",
            "search_topic": None,
            "search_keywords": [],
            "search_query": None,
            "info_type": None,
            "company_url": None,
            "company_domain": None,
            "domain_found": False,
            "brave_results": [],
            "search_successful": False,
            "search_error": None,
            "ranked_results": [],
            "best_match": None,
            "confidence_score": 0.0,
            "found_answer": False,
            "answer": None,
            "source_urls": [],
            "suggest_hr_ticket": False,
            "hr_ticket_suggestion": None,
            "agent_response": "",
            "search_time_ms": None,
            "error_message": None
        }
        
        result = resolve_domain_node(state, db_session)
        
        assert result["domain_found"] is False
        assert result["company_domain"] is None


class TestBraveSearchNode:
    """Test Brave search execution node"""
    
    @patch('agents.website_extraction.nodes.brave_search')
    def test_brave_search_node_success(self, mock_search, db_session):
        """Test successful search execution"""
        mock_search.return_value = ([{"title": "Test"}], None)
        
        state: WebsiteExtractionState = {
            "user_email": "test@test.com",
            "company": "Test Corp",
            "user_message": "test",
            "original_query": None,
            "triggered_by": "direct",
            "search_topic": None,
            "search_keywords": [],
            "search_query": "test query",
            "info_type": None,
            "company_url": None,
            "company_domain": "test.com",
            "domain_found": True,
            "brave_results": [],
            "search_successful": False,
            "search_error": None,
            "ranked_results": [],
            "best_match": None,
            "confidence_score": 0.0,
            "found_answer": False,
            "answer": None,
            "source_urls": [],
            "suggest_hr_ticket": False,
            "hr_ticket_suggestion": None,
            "agent_response": "",
            "search_time_ms": None,
            "error_message": None
        }
        
        result = brave_search_node(state, db_session)
        
        assert result["search_successful"] is True
        assert len(result["brave_results"]) == 1
        assert result["search_error"] is None
        assert result["search_time_ms"] is not None
    
    @patch('agents.website_extraction.nodes.brave_search')
    def test_brave_search_node_failure(self, mock_search, db_session):
        """Test search failure handling"""
        mock_search.return_value = ([], "API error")
        
        state: WebsiteExtractionState = {
            "user_email": "test@test.com",
            "company": "Test Corp",
            "user_message": "test",
            "original_query": None,
            "triggered_by": "direct",
            "search_topic": None,
            "search_keywords": [],
            "search_query": "test query",
            "info_type": None,
            "company_url": None,
            "company_domain": "test.com",
            "domain_found": True,
            "brave_results": [],
            "search_successful": False,
            "search_error": None,
            "ranked_results": [],
            "best_match": None,
            "confidence_score": 0.0,
            "found_answer": False,
            "answer": None,
            "source_urls": [],
            "suggest_hr_ticket": False,
            "hr_ticket_suggestion": None,
            "agent_response": "",
            "search_time_ms": None,
            "error_message": None
        }
        
        result = brave_search_node(state, db_session)
        
        assert result["search_successful"] is False
        assert result["search_error"] == "API error"
        assert result["brave_results"] == []


class TestAnalyzeResultsNode:
    """Test result analysis node"""
    
    def test_analyze_with_results(self, db_session):
        """Test analyzing search results"""
        state: WebsiteExtractionState = {
            "user_email": "test@test.com",
            "company": "Test Corp",
            "user_message": "contact info",
            "original_query": None,
            "triggered_by": "direct",
            "search_topic": "contact information",
            "search_keywords": ["contact", "phone", "hours"],
            "search_query": "contact info",
            "info_type": "contact",
            "company_url": None,
            "company_domain": "test.com",
            "domain_found": True,
            "brave_results": [
                {
                    "title": "Contact Us",
                    "url": "https://test.com/contact",
                    "description": "Phone: 555-1234. Hours: 9-5",
                    "extra_snippets": []
                }
            ],
            "search_successful": True,
            "search_error": None,
            "ranked_results": [],
            "best_match": None,
            "confidence_score": 0.0,
            "found_answer": False,
            "answer": None,
            "source_urls": [],
            "suggest_hr_ticket": False,
            "hr_ticket_suggestion": None,
            "agent_response": "",
            "search_time_ms": None,
            "error_message": None
        }
        
        result = analyze_results_node(state, db_session)
        
        assert len(result["ranked_results"]) == 1
        assert result["best_match"] is not None
        assert result["confidence_score"] > 0.0
    
    def test_analyze_no_results(self, db_session):
        """Test analysis with no results"""
        state: WebsiteExtractionState = {
            "user_email": "test@test.com",
            "company": "Test Corp",
            "user_message": "test",
            "original_query": None,
            "triggered_by": "direct",
            "search_topic": "test",
            "search_keywords": ["test"],
            "search_query": "test",
            "info_type": "general",
            "company_url": None,
            "company_domain": "test.com",
            "domain_found": True,
            "brave_results": [],
            "search_successful": True,
            "search_error": None,
            "ranked_results": [],
            "best_match": None,
            "confidence_score": 0.0,
            "found_answer": False,
            "answer": None,
            "source_urls": [],
            "suggest_hr_ticket": False,
            "hr_ticket_suggestion": None,
            "agent_response": "",
            "search_time_ms": None,
            "error_message": None
        }
        
        result = analyze_results_node(state, db_session)
        
        assert result["ranked_results"] == []
        assert result["best_match"] is None
        assert result["confidence_score"] == 0.0
        assert result["found_answer"] is False


class TestGenerateAnswerNode:
    """Test answer generation node"""
    
    def test_generate_answer_with_match(self, db_session):
        """Test answer generation with good match"""
        state: WebsiteExtractionState = {
            "user_email": "test@test.com",
            "company": "Test Corp",
            "user_message": "What are your hours?",
            "original_query": None,
            "triggered_by": "direct",
            "search_topic": "hours",
            "search_keywords": ["hours"],
            "search_query": "hours",
            "info_type": "hours",
            "company_url": None,
            "company_domain": "test.com",
            "domain_found": True,
            "brave_results": [],
            "search_successful": True,
            "search_error": None,
            "ranked_results": [
                {
                    "title": "Hours",
                    "url": "https://test.com/hours",
                    "description": "We're open Mon-Fri 9am-5pm",
                    "extra_snippets": [],
                    "relevance_score": 0.8
                }
            ],
            "best_match": {
                "title": "Hours",
                "url": "https://test.com/hours",
                "description": "We're open Mon-Fri 9am-5pm",
                "extra_snippets": [],
                "relevance_score": 0.8
            },
            "confidence_score": 0.8,
            "found_answer": True,
            "answer": None,
            "source_urls": [],
            "suggest_hr_ticket": False,
            "hr_ticket_suggestion": None,
            "agent_response": "",
            "search_time_ms": None,
            "error_message": None
        }
        
        result = generate_answer_node(state, db_session)
        
        assert result["answer"] is not None
        assert len(result["source_urls"]) > 0
    
    def test_generate_answer_no_match(self, db_session):
        """Test answer generation with no match"""
        state: WebsiteExtractionState = {
            "user_email": "test@test.com",
            "company": "Test Corp",
            "user_message": "test",
            "original_query": None,
            "triggered_by": "direct",
            "search_topic": None,
            "search_keywords": [],
            "search_query": None,
            "info_type": None,
            "company_url": None,
            "company_domain": None,
            "domain_found": False,
            "brave_results": [],
            "search_successful": False,
            "search_error": None,
            "ranked_results": [],
            "best_match": None,
            "confidence_score": 0.0,
            "found_answer": False,
            "answer": None,
            "source_urls": [],
            "suggest_hr_ticket": False,
            "hr_ticket_suggestion": None,
            "agent_response": "",
            "search_time_ms": None,
            "error_message": None
        }
        
        result = generate_answer_node(state, db_session)
        
        assert result["answer"] is None
        assert result["source_urls"] == []
    
    def test_generate_answer_llm_failure_fallback(self, db_session):
        """Test fallback when LLM fails during answer generation"""
        with patch('agents.website_extraction.nodes.get_llm_client') as mock_llm:
            mock_llm.return_value.chat.side_effect = Exception("LLM error")
            
            state: WebsiteExtractionState = {
                "user_email": "test@test.com",
                "company": "Test Corp",
                "user_message": "hours",
                "original_query": None,
                "triggered_by": "direct",
                "search_topic": "hours",
                "search_keywords": ["hours"],
                "search_query": "hours",
                "info_type": "hours",
                "company_url": None,
                "company_domain": "test.com",
                "domain_found": True,
                "brave_results": [],
                "search_successful": True,
                "search_error": None,
                "ranked_results": [
                    {
                        "title": "Hours",
                        "url": "https://test.com/hours",
                        "description": "Mon-Fri 9-5",
                        "extra_snippets": [],
                        "relevance_score": 0.7
                    }
                ],
                "best_match": {
                    "title": "Hours",
                    "url": "https://test.com/hours",
                    "description": "Mon-Fri 9-5",
                    "extra_snippets": [],
                    "relevance_score": 0.7
                },
                "confidence_score": 0.7,
                "found_answer": True,
                "answer": None,
                "source_urls": [],
                "suggest_hr_ticket": False,
                "hr_ticket_suggestion": None,
                "agent_response": "",
                "search_time_ms": None,
                "error_message": None
            }
            
            result = generate_answer_node(state, db_session)
            
            # Should fallback to title + description
            assert result["answer"] is not None
            assert "Hours" in result["answer"]


class TestSuggestHRTicketNode:
    """Test HR ticket suggestion node"""
    
    def test_suggest_on_search_error(self, db_session):
        """Test HR ticket suggestion when search fails"""
        state: WebsiteExtractionState = {
            "user_email": "test@test.com",
            "company": "Test Corp",
            "user_message": "contact info",
            "original_query": None,
            "triggered_by": "direct",
            "search_topic": "contact",
            "search_keywords": ["contact"],
            "search_query": "contact",
            "info_type": "contact",
            "company_url": None,
            "company_domain": "test.com",
            "domain_found": True,
            "brave_results": [],
            "search_successful": False,
            "search_error": "API timeout",
            "ranked_results": [],
            "best_match": None,
            "confidence_score": 0.0,
            "found_answer": False,
            "answer": None,
            "source_urls": [],
            "suggest_hr_ticket": False,
            "hr_ticket_suggestion": None,
            "agent_response": "",
            "search_time_ms": None,
            "error_message": None
        }
        
        result = suggest_hr_ticket_node(state, db_session)
        
        assert result["suggest_hr_ticket"] is True
        assert result["hr_ticket_suggestion"] is not None
        assert "trouble searching" in result["hr_ticket_suggestion"]
    
    def test_suggest_on_no_results(self, db_session):
        """Test HR ticket suggestion when no results found"""
        state: WebsiteExtractionState = {
            "user_email": "test@test.com",
            "company": "Test Corp",
            "user_message": "obscure policy",
            "original_query": None,
            "triggered_by": "direct",
            "search_topic": "obscure policy",
            "search_keywords": ["policy"],
            "search_query": "policy",
            "info_type": "policies",
            "company_url": None,
            "company_domain": "test.com",
            "domain_found": True,
            "brave_results": [],
            "search_successful": True,
            "search_error": None,
            "ranked_results": [],
            "best_match": None,
            "confidence_score": 0.0,
            "found_answer": False,
            "answer": None,
            "source_urls": [],
            "suggest_hr_ticket": False,
            "hr_ticket_suggestion": None,
            "agent_response": "",
            "search_time_ms": None,
            "error_message": None
        }
        
        result = suggest_hr_ticket_node(state, db_session)
        
        assert result["suggest_hr_ticket"] is True
        assert "couldn't find" in result["hr_ticket_suggestion"]


class TestFormatResponseNode:
    """Test response formatting node"""
    
    def test_format_high_confidence_answer(self, db_session):
        """Test formatting high confidence answer"""
        state: WebsiteExtractionState = {
            "user_email": "test@test.com",
            "company": "Test Corp",
            "user_message": "hours",
            "original_query": None,
            "triggered_by": "direct",
            "search_topic": "hours",
            "search_keywords": ["hours"],
            "search_query": "hours",
            "info_type": "hours",
            "company_url": None,
            "company_domain": "test.com",
            "domain_found": True,
            "brave_results": [],
            "search_successful": True,
            "search_error": None,
            "ranked_results": [],
            "best_match": None,
            "confidence_score": 0.8,
            "found_answer": True,
            "answer": "We're open Mon-Fri 9am-5pm",
            "source_urls": ["https://test.com/hours"],
            "suggest_hr_ticket": False,
            "hr_ticket_suggestion": None,
            "agent_response": "",
            "search_time_ms": None,
            "error_message": None
        }
        
        result = format_response_node(state, db_session)
        
        assert result["agent_response"] is not None
        assert "Found on" in result["agent_response"]
        assert "We're open Mon-Fri 9am-5pm" in result["agent_response"]
    
    def test_format_low_confidence_answer(self, db_session):
        """Test formatting low confidence answer with warning"""
        state: WebsiteExtractionState = {
            "user_email": "test@test.com",
            "company": "Test Corp",
            "user_message": "hours",
            "original_query": None,
            "triggered_by": "direct",
            "search_topic": "hours",
            "search_keywords": ["hours"],
            "search_query": "hours",
            "info_type": "hours",
            "company_url": None,
            "company_domain": "test.com",
            "domain_found": True,
            "brave_results": [],
            "search_successful": True,
            "search_error": None,
            "ranked_results": [],
            "best_match": None,
            "confidence_score": 0.5,
            "found_answer": True,
            "answer": "Might be 9-5",
            "source_urls": ["https://test.com/page"],
            "suggest_hr_ticket": False,
            "hr_ticket_suggestion": None,
            "agent_response": "",
            "search_time_ms": None,
            "error_message": None
        }
        
        result = format_response_node(state, db_session)
        
        assert "verify" in result["agent_response"] or "HR ticket" in result["agent_response"]
    
    def test_format_hr_suggestion(self, db_session):
        """Test formatting HR ticket suggestion"""
        state: WebsiteExtractionState = {
            "user_email": "test@test.com",
            "company": "Test Corp",
            "user_message": "test",
            "original_query": None,
            "triggered_by": "direct",
            "search_topic": None,
            "search_keywords": [],
            "search_query": None,
            "info_type": None,
            "company_url": None,
            "company_domain": None,
            "domain_found": False,
            "brave_results": [],
            "search_successful": False,
            "search_error": None,
            "ranked_results": [],
            "best_match": None,
            "confidence_score": 0.0,
            "found_answer": False,
            "answer": None,
            "source_urls": [],
            "suggest_hr_ticket": True,
            "hr_ticket_suggestion": "Would you like to create an HR ticket?",
            "agent_response": "",
            "search_time_ms": None,
            "error_message": None
        }
        
        result = format_response_node(state, db_session)
        
        assert "HR ticket" in result["agent_response"]