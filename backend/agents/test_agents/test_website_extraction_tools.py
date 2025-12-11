"""
Tests for Website Extraction Agent Tools
"""
import pytest
from unittest.mock import patch, MagicMock
from agents.website_extraction.tools import (
    brave_search,
    get_company_domain,
    score_result_relevance,
    rank_results,
    extract_domain_from_url,
    CONFIDENCE_THRESHOLD
)
from agents.website_extraction.state import WebsiteExtractionState  # Import state for coverage
from db.models import Company


class TestBraveSearch:
    """Test Brave Search API integration"""
    
    @patch('agents.website_extraction.tools.BRAVE_API_KEY', 'test_key')
    @patch('agents.website_extraction.tools.requests.get')
    def test_brave_search_success(self, mock_get):
        """Test successful Brave search"""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "web": {
                "results": [
                    {
                        "title": "Test Result",
                        "url": "https://test.com/page",
                        "description": "Test description",
                        "extra_snippets": ["snippet1"],
                        "age": "2023-01-01"
                    }
                ]
            }
        }
        mock_get.return_value = mock_response
        
        results, error = brave_search("test query", "test.com")
        
        assert error is None
        assert len(results) == 1
        assert results[0]["title"] == "Test Result"
        assert results[0]["url"] == "https://test.com/page"
    
    @patch('agents.website_extraction.tools.BRAVE_API_KEY', None)
    def test_brave_search_no_api_key(self):
        """Test Brave search without API key"""
        results, error = brave_search("test query")
        
        assert results == []
        assert error == "BRAVE_API_KEY not configured"
    
    @patch('agents.website_extraction.tools.BRAVE_API_KEY', 'test_key')
    @patch('agents.website_extraction.tools.requests.get')
    def test_brave_search_timeout(self, mock_get):
        """Test Brave search timeout"""
        import requests
        mock_get.side_effect = requests.Timeout()
        
        results, error = brave_search("test query")
        
        assert results == []
        assert error == "Search timeout"
    
    @patch('agents.website_extraction.tools.BRAVE_API_KEY', 'test_key')
    @patch('agents.website_extraction.tools.requests.get')
    def test_brave_search_with_site_domain(self, mock_get):
        """Test Brave search with site domain filter"""
        mock_response = MagicMock()
        mock_response.json.return_value = {"web": {"results": []}}
        mock_get.return_value = mock_response
        
        brave_search("contact info", "example.com")
        
        call_args = mock_get.call_args
        assert "site:example.com" in call_args[1]["params"]["q"]
    
    @patch('agents.website_extraction.tools.BRAVE_API_KEY', 'test_key')
    @patch('agents.website_extraction.tools.requests.get')
    def test_brave_search_request_exception(self, mock_get):
        """Test Brave search with request exception"""
        import requests
        mock_get.side_effect = requests.RequestException("Network error")
        
        results, error = brave_search("test query")
        
        assert results == []
        assert "Network error" in error


class TestGetCompanyDomain:
    """Test company domain extraction from database"""
    
    def test_get_company_domain_success(self, db_session):
        """Test successful domain extraction"""
        company = Company(
            name="Test Corp",
            domain="Technology",
            email_domain="testcorp.com",
            url="https://www.testcorp.com/handbook.pdf"
        )
        db_session.add(company)
        db_session.commit()
        
        url, domain = get_company_domain(db_session, "Test Corp")
        
        assert url == "https://www.testcorp.com/handbook.pdf"
        assert domain == "testcorp.com"
    
    def test_get_company_domain_strips_www(self, db_session):
        """Test that www is stripped from domain"""
        company = Company(
            name="WWW Corp",
            domain="Technology",
            email_domain="wwwcorp.com",
            url="https://www.example.com/page"
        )
        db_session.add(company)
        db_session.commit()
        
        url, domain = get_company_domain(db_session, "WWW Corp")
        
        assert domain == "example.com"
        assert "www." not in domain
    
    def test_get_company_domain_not_found(self, db_session):
        """Test company not found in database"""
        url, domain = get_company_domain(db_session, "Nonexistent Company")
        
        assert url is None
        assert domain is None
    
    def test_get_company_domain_no_url(self, db_session):
        """Test company exists but has no URL"""
        company = Company(
            name="No URL Corp",
            domain="Technology",
            email_domain="nourl.com",
            url=None
        )
        db_session.add(company)
        db_session.commit()
        
        url, domain = get_company_domain(db_session, "No URL Corp")
        
        assert url is None
        assert domain is None


class TestScoreResultRelevance:
    """Test search result scoring algorithm"""
    
    def test_score_high_relevance(self):
        """Test scoring for highly relevant result"""
        result = {
            "title": "Contact Us - Hours and Location",
            "url": "https://example.com/contact",
            "description": "Find our contact information, business hours, phone number, and address. We're open Monday-Friday 9am-5pm.",
            "extra_snippets": ["Call us at 555-1234", "Located at 123 Main St"]
        }
        
        score = score_result_relevance(
            result,
            keywords=["contact", "hours", "phone"],
            topic="contact information"
        )
        
        assert score > 0.7
        assert score <= 1.0
    
    def test_score_medium_relevance(self):
        """Test scoring for moderately relevant result"""
        result = {
            "title": "About Our Company",
            "url": "https://example.com/about",
            "description": "Learn about our history and mission.",
            "extra_snippets": []
        }
        
        score = score_result_relevance(
            result,
            keywords=["contact", "hours"],
            topic="contact information"
        )
        
        assert 0.0 <= score < 0.5
    
    def test_score_low_relevance(self):
        """Test scoring for irrelevant result"""
        result = {
            "title": "Blog Post Archive",
            "url": "https://example.com/blog/2023/post",
            "description": "Read our latest blog posts.",
            "extra_snippets": []
        }
        
        score = score_result_relevance(
            result,
            keywords=["contact", "hours"],
            topic="contact information"
        )
        
        assert score < 0.4
    
    def test_score_contact_page_boost(self):
        """Test that contact pages get boosted score"""
        result_contact = {
            "title": "Contact",
            "url": "https://example.com/contact",
            "description": "Get in touch",
            "extra_snippets": []
        }
        
        result_other = {
            "title": "Contact",
            "url": "https://example.com/other",
            "description": "Get in touch",
            "extra_snippets": []
        }
        
        score_contact = score_result_relevance(result_contact, ["contact"], "contact")
        score_other = score_result_relevance(result_other, ["contact"], "contact")
        
        assert score_contact > score_other
    
    def test_score_with_rich_snippets(self):
        """Test that extra snippets increase score"""
        result_rich = {
            "title": "Info",
            "url": "https://example.com/info",
            "description": "Information page with lots of detail here for context",
            "extra_snippets": ["Additional info 1", "Additional info 2"]
        }
        
        result_basic = {
            "title": "Info",
            "url": "https://example.com/info",
            "description": "Short",
            "extra_snippets": []
        }
        
        score_rich = score_result_relevance(result_rich, ["info"], "information")
        score_basic = score_result_relevance(result_basic, ["info"], "information")
        
        assert score_rich > score_basic


class TestRankResults:
    """Test result ranking"""
    
    def test_rank_results_by_relevance(self):
        """Test that results are ranked by relevance score"""
        results = [
            {
                "title": "Blog Post",
                "url": "https://example.com/blog/post",
                "description": "Some blog content",
                "extra_snippets": []
            },
            {
                "title": "Contact Us - Phone and Hours",
                "url": "https://example.com/contact",
                "description": "Call us at 555-1234. Hours: 9am-5pm",
                "extra_snippets": ["Located at 123 Main St"]
            },
            {
                "title": "About",
                "url": "https://example.com/about",
                "description": "Company info",
                "extra_snippets": []
            }
        ]
        
        ranked = rank_results(results, ["contact", "hours", "phone"], "contact information")
        
        assert len(ranked) == 3
        assert ranked[0]["title"] == "Contact Us - Phone and Hours"
        assert "relevance_score" in ranked[0]
        assert ranked[0]["relevance_score"] > ranked[1]["relevance_score"]
    
    def test_rank_empty_results(self):
        """Test ranking with empty results"""
        ranked = rank_results([], ["keyword"], "topic")
        
        assert ranked == []
    
    def test_rank_preserves_original_data(self):
        """Test that ranking adds score without losing original data"""
        results = [
            {
                "title": "Test",
                "url": "https://test.com",
                "description": "Test description",
                "extra_snippets": ["snippet"],
                "age": "2024-01-01"
            }
        ]
        
        ranked = rank_results(results, ["test"], "test")
        
        assert ranked[0]["title"] == "Test"
        assert ranked[0]["url"] == "https://test.com"
        assert ranked[0]["age"] == "2024-01-01"
        assert "relevance_score" in ranked[0]


class TestExtractDomainFromUrl:
    """Test domain extraction utility"""
    
    def test_extract_domain_https(self):
        """Test extracting domain from HTTPS URL"""
        domain = extract_domain_from_url("https://www.example.com/path/to/page")
        assert domain == "example.com"
    
    def test_extract_domain_http(self):
        """Test extracting domain from HTTP URL"""
        domain = extract_domain_from_url("http://test.com/page")
        assert domain == "test.com"
    
    def test_extract_domain_with_www(self):
        """Test that www is stripped"""
        domain = extract_domain_from_url("https://www.company.org")
        assert domain == "company.org"
        assert "www." not in domain
    
    def test_extract_domain_subdomain(self):
        """Test domain with subdomain"""
        domain = extract_domain_from_url("https://blog.example.com/post")
        assert domain == "blog.example.com"
    
    def test_extract_domain_invalid_url(self):
        """Test extracting from invalid URL"""
        domain = extract_domain_from_url("not-a-valid-url")
        assert domain == "not-a-valid-url"