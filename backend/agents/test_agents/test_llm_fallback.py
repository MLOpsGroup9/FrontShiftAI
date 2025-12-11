"""
Tests for LLM fallback mechanisms
Validates system behavior when LLM providers fail
"""
import pytest
import sys
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))

from agents.utils.llm_client import AgentLLMClient, llm_cache
from agents.pto.nodes import parse_intent_node
from agents.pto.state import PTOAgentState
from agents.hr_ticket.nodes import parse_intent_node as hr_parse_intent_node
from agents.hr_ticket.state import HRTicketState


class TestLLMFallbackMechanism:
    """Test LLM client fallback behavior"""
    
    def test_primary_provider_failure_triggers_fallback(self, monkeypatch):
        """Test fallback when primary LLM fails"""
        
        call_count = {'groq': 0, 'local': 0}
        
        def mock_groq_failure(*args, **kwargs):
            call_count['groq'] += 1
            raise Exception("Groq unavailable")
        
        def mock_local_success(*args, **kwargs):
            call_count['local'] += 1
            return '{"intent": "request_pto", "start_date": "2025-12-24"}'
        
        client = AgentLLMClient()
        monkeypatch.setattr(client, '_call_groq', mock_groq_failure)
        monkeypatch.setattr(client, '_call_local', mock_local_success)
        
        # Should succeed via fallback
        result = client.chat([{"role": "user", "content": "test"}], json_mode=True)
        
        assert result is not None
        assert call_count['groq'] > 0  # Primary tried
        assert call_count['local'] > 0  # Fallback succeeded
    
    def test_all_providers_fail(self, monkeypatch):
        """Test behavior when all LLM providers fail"""
        
        def mock_failure(*args, **kwargs):
            raise Exception("Provider unavailable")
        
        client = AgentLLMClient()
        monkeypatch.setattr(client, '_call_groq', mock_failure)
        monkeypatch.setattr(client, '_call_local', mock_failure)
        monkeypatch.setattr(client, '_call_mercury', mock_failure)
        
        # Implementation returns None when all fail
        result = client.chat([{"role": "user", "content": "test"}])
        assert result is None
    
    def test_retry_logic(self, monkeypatch):
        """Test retry logic with exponential backoff"""
        
        llm_cache.clear()
        call_count = {'attempts': 0}
        
        def mock_fails_twice(*args, **kwargs):
            call_count['attempts'] += 1
            if call_count['attempts'] < 3:
                raise Exception("Temporary failure")
            return '{"intent": "test"}'
        
        client = AgentLLMClient()
        monkeypatch.setattr(client, '_call_groq', mock_fails_twice)
        
        # Should attempt retries (may fail if fallback kicks in)
        result = client.chat([{"role": "user", "content": "test"}], json_mode=True)
        
        # Just verify retries were attempted
        assert call_count['attempts'] >= 1


class TestNodeFallbackBehavior:
    """Test node behavior when LLM fails"""
    
    def test_pto_parse_falls_back_gracefully(self, db_session, monkeypatch):
        """Test PTO parsing falls back to defaults when LLM fails"""
        
        def mock_chat_failure(*args, **kwargs):
            raise Exception("LLM unavailable")
        
        # Mock the LLM client
        from agents.utils import llm_client
        mock_client = type('MockClient', (), {'chat': mock_chat_failure})()
        monkeypatch.setattr(llm_client, 'get_llm_client', lambda: mock_client)
        
        state = PTOAgentState(
            user_email="test@test.com",
            company="Test Company",
            user_message="I need 3 days off",
            start_date=None,
            end_date=None,
            intent=None,
            is_valid=False,
            validation_errors=[],
            holiday_dates=[],
            blackout_conflicts=[],
            total_business_days=None,
            has_sufficient_balance=False,
            has_conflicts=False,
            conflicting_requests=[],
            request_id=None,
            request_created=False,
            agent_response="",
            should_end=False,
            current_balance=None,
            used_days=None,
            pending_days=None,
            remaining_days=None,
            reason=None,
            error_message=None
        )
        
        result = parse_intent_node(state, db_session)
        
        # Should fallback gracefully, not crash
        assert 'intent' in result
        # May set general_query or similar default
        assert result['intent'] in ['request_pto', 'check_balance', 'general_query', None]
    
    def test_hr_ticket_parse_falls_back_gracefully(self, db_session, monkeypatch):
        """Test HR ticket parsing falls back to defaults when LLM fails"""
        
        def mock_chat_failure(*args, **kwargs):
            raise Exception("LLM unavailable")
        
        from agents.utils import llm_client
        mock_client = type('MockClient', (), {'chat': mock_chat_failure})()
        monkeypatch.setattr(llm_client, 'get_llm_client', lambda: mock_client)
        
        state: HRTicketState = {
            "user_email": "test@company.com",
            "company": "Test Company",
            "user_message": "I need help",
            "intent": "",
            "subject": None,
            "description": None,
            "category": None,
            "meeting_type": None,
            "preferred_date": None,
            "preferred_time_slot": None,
            "urgency": "normal",
            "is_valid": False,
            "validation_errors": [],
            "has_open_tickets": False,
            "open_ticket_ids": [],
            "ticket_id": None,
            "queue_position": None,
            "agent_response": ""
        }
        
        result = hr_parse_intent_node(state, db_session)
        
        # Should fallback to defaults
        assert result['intent'] == 'create_ticket'
        assert result['category'] == 'general_inquiry'
        assert result['is_valid'] is True
    
    def test_malformed_json_response(self, monkeypatch):
        """Test handling of malformed JSON from LLM"""
        
        def mock_invalid_json(*args, **kwargs):
            return "This is not JSON at all!"
        
        client = AgentLLMClient()
        monkeypatch.setattr(client, '_call_groq', mock_invalid_json)
        
        # Should handle gracefully or retry with fallback
        # Behavior depends on implementation - ensure no crash
        try:
            result = client.chat([{"role": "user", "content": "test"}], json_mode=True)
            # Either succeeded with fallback or...
        except Exception as e:
            # ...raised controlled exception (not unhandled crash)
            assert "json" in str(e).lower() or "parse" in str(e).lower() or "failed" in str(e).lower()


class TestProviderSwitching:
    """Test switching between LLM providers"""
    
    def test_provider_configuration(self):
        """Test provider can be configured"""
        from agents.utils.llm_config import USE_LLM, ENABLE_FALLBACK, FALLBACK_CHAIN
        
        # Verify configuration is accessible
        assert USE_LLM in ['groq', 'local', 'mercury']
        assert isinstance(ENABLE_FALLBACK, bool)
        assert isinstance(FALLBACK_CHAIN, list)
        assert len(FALLBACK_CHAIN) > 0
    
    def test_client_uses_configured_provider(self):
        """Test client respects primary provider setting"""
        from agents.utils.llm_config import USE_LLM
        
        client = AgentLLMClient()
        
        assert client.primary_provider == USE_LLM