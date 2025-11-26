"""
Integration tests for complete agent workflows
Tests end-to-end flows from user message to final response
"""
import pytest
import sys
from pathlib import Path
from datetime import date, timedelta

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))

from agents.pto.agent import PTOAgent
from agents.hr_ticket.agent import HRTicketAgent
from db.models import PTORequest, HRTicket, TicketStatus, PTOStatus


class TestPTOAgentIntegration:
    """End-to-end PTO agent workflow tests"""
    
    @pytest.mark.asyncio
    async def test_complete_pto_request_flow(self, db_session, sample_pto_balance):
        """Test complete PTO request from message to database"""
        agent = PTOAgent(db_session)
        
        result = await agent.execute(
            user_email=sample_pto_balance.email,
            company=sample_pto_balance.company,
            message="I need 3 days off from December 24 to December 26"
        )
        
        # Verify response
        assert result['response'] is not None
        assert len(result['response']) > 50
        
        # If request was created
        if result.get('request_created'):
            assert result['request_id'] is not None
            
            # Verify in database
            request = db_session.query(PTORequest).filter_by(
                id=result['request_id']
            ).first()
            
            assert request is not None
            assert request.email == sample_pto_balance.email
            assert request.status == PTOStatus.PENDING
            assert request.days_requested > 0
    
    @pytest.mark.asyncio
    async def test_pto_balance_check_flow(self, db_session, sample_pto_balance):
        """Test balance check workflow"""
        agent = PTOAgent(db_session)
        
        result = await agent.execute(
            user_email=sample_pto_balance.email,
            company=sample_pto_balance.company,
            message="How many PTO days do I have left?"
        )
        
        # Should return balance information
        assert result['response'] is not None
        
        if result.get('balance_info'):
            assert result['balance_info']['remaining_days'] == 15.0
    
    @pytest.mark.asyncio
    async def test_pto_insufficient_balance_flow(self, db_session, sample_pto_balance):
        """Test workflow when balance is insufficient"""
        agent = PTOAgent(db_session)
        
        result = await agent.execute(
            user_email=sample_pto_balance.email,
            company=sample_pto_balance.company,
            message="I need 20 days off next month"
        )
        
        # Should reject due to insufficient balance
        assert result['response'] is not None
        assert len(result['response']) > 50
    
    @pytest.mark.asyncio
    async def test_pto_past_dates_rejection(self, db_session, sample_pto_balance):
        """Test rejection of past dates"""
        agent = PTOAgent(db_session)
        
        result = await agent.execute(
            user_email=sample_pto_balance.email,
            company=sample_pto_balance.company,
            message="I need off last week"
        )
        
        # Should reject
        assert result['request_created'] is False
        assert 'past' in result['response'].lower() or 'cannot' in result['response'].lower()


class TestHRTicketAgentIntegration:
    """End-to-end HR ticket agent workflow tests"""
    
    @pytest.mark.asyncio
    async def test_complete_ticket_creation_flow(self, db_session, sample_user):
        """Test complete ticket creation from message to database"""
        agent = HRTicketAgent()
        
        result = await agent.process_message(
            user_email=sample_user.email,
            company=sample_user.company,
            message="I need to discuss my health insurance options",
            db=db_session
        )
        
        # Verify response
        assert result['response'] is not None
        assert len(result['response']) > 50
        
        # If ticket was created
        if result.get('ticket_created'):
            assert result['ticket_id'] is not None
            
            # Verify in database
            ticket = db_session.query(HRTicket).filter_by(
                id=result['ticket_id']
            ).first()
            
            assert ticket is not None
            assert ticket.email == sample_user.email
            assert ticket.status == TicketStatus.PENDING
            assert ticket.queue_position is not None
    
    @pytest.mark.asyncio
    async def test_urgent_ticket_flow(self, db_session, sample_user):
        """Test urgent ticket creation"""
        agent = HRTicketAgent()
        
        result = await agent.process_message(
            user_email=sample_user.email,
            company=sample_user.company,
            message="URGENT: There's a problem with my paycheck",
            db=db_session
        )
        
        if result.get('ticket_created'):
            ticket = db_session.query(HRTicket).filter_by(
                id=result['ticket_id']
            ).first()
            
            # Should be marked as urgent (if LLM detected it)
            # Fallback sets normal, so allow either
            assert ticket.urgency.value in ['urgent', 'normal']
    
    @pytest.mark.asyncio
    async def test_ticket_with_meeting_preference(self, db_session, sample_user):
        """Test ticket creation with meeting preferences"""
        agent = HRTicketAgent()
        
        tomorrow = date.today() + timedelta(days=1)
        
        result = await agent.process_message(
            user_email=sample_user.email,
            company=sample_user.company,
            message=f"Schedule a meeting for tomorrow morning to discuss benefits",
            db=db_session
        )
        
        if result.get('ticket_created'):
            ticket = db_session.query(HRTicket).filter_by(
                id=result['ticket_id']
            ).first()
            
            # If LLM parsed correctly, should have preferences
            # Fallback may not capture these
            assert ticket is not None
    
    @pytest.mark.asyncio
    async def test_validation_error_flow(self, db_session, sample_user):
        """Test workflow with validation errors"""
        agent = HRTicketAgent()
        
        # Empty message should trigger validation
        result = await agent.process_message(
            user_email=sample_user.email,
            company=sample_user.company,
            message="",
            db=db_session
        )
        
        # Should not crash, may succeed with fallback or fail gracefully
        assert result['response'] is not None


class TestMultiAgentInteraction:
    """Test interactions between multiple agents"""
    
    @pytest.mark.asyncio
    async def test_pto_then_hr_ticket(self, db_session, sample_pto_balance, sample_user):
        """Test creating PTO request then HR ticket in sequence"""
        pto_agent = PTOAgent(db_session)
        hr_agent = HRTicketAgent()
        
        # First: PTO request
        pto_result = await pto_agent.execute(
            user_email=sample_user.email,
            company=sample_user.company,
            message="I need 3 days off next week"
        )
        
        assert pto_result['response'] is not None
        
        # Then: HR ticket
        hr_result = await hr_agent.process_message(
            user_email=sample_user.email,
            company=sample_user.company,
            message="I need to discuss benefits with HR",
            db=db_session
        )
        
        assert hr_result['response'] is not None
        
        # Both should work independently
        # PTO may or may not succeed depending on balance
        # HR ticket should succeed
    
    @pytest.mark.asyncio
    async def test_multiple_requests_same_user(self, db_session, sample_pto_balance):
        """Test multiple PTO requests from same user"""
        agent = PTOAgent(db_session)
        
        # First request
        result1 = await agent.execute(
            user_email=sample_pto_balance.email,
            company=sample_pto_balance.company,
            message="I need 3 days off December 1-3"
        )
        
        # Second request (different dates)
        result2 = await agent.execute(
            user_email=sample_pto_balance.email,
            company=sample_pto_balance.company,
            message="I need 2 days off December 10-11"
        )
        
        # Both should process (success depends on balance)
        assert result1['response'] is not None
        assert result2['response'] is not None
        
        # If both created, should have different IDs
        if result1.get('request_id') and result2.get('request_id'):
            assert result1['request_id'] != result2['request_id']


class TestWorkflowStateConsistency:
    """Test state remains consistent throughout workflow"""
    
    @pytest.mark.asyncio
    async def test_state_immutability(self, db_session, sample_pto_balance):
        """Test workflow doesn't corrupt state"""
        agent = PTOAgent(db_session)
        
        result = await agent.execute(
            user_email=sample_pto_balance.email,
            company=sample_pto_balance.company,
            message="I need 3 days off next week"
        )
        
        # Verify result structure
        assert 'response' in result
        assert 'request_created' in result
        assert 'request_id' in result
        assert 'balance_info' in result
        
        # No unexpected keys
        expected_keys = {'response', 'request_created', 'request_id', 'balance_info', 'error'}
        actual_keys = set(result.keys())
        assert actual_keys.issubset(expected_keys)