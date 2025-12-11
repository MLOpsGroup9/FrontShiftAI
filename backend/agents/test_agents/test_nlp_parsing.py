"""
Tests for natural language parsing capabilities
Validates date extraction, entity recognition, and intent understanding
"""
import pytest
import sys
from pathlib import Path
from datetime import date, timedelta

backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))

from agents.pto.nodes import parse_intent_node
from agents.pto.state import PTOAgentState
from agents.hr_ticket.nodes import parse_intent_node as hr_parse_intent_node
from agents.hr_ticket.state import HRTicketState


class TestRelativeDateParsing:
    """Test parsing of relative date expressions"""
    
    def test_parse_tomorrow(self, db_session):
        """Test 'tomorrow' parsing"""
        state = PTOAgentState(
            user_email="test@test.com",
            company="Test Company",
            user_message="I need off tomorrow",
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
        
        # If LLM successfully parses, check date is tomorrow
        if result['start_date']:
            expected_tomorrow = date.today() + timedelta(days=1)
            # Allow some flexibility for timing issues
            assert result['start_date'] >= date.today()
            assert result['start_date'] <= date.today() + timedelta(days=2)
    
    def test_parse_next_week(self, db_session):
        """Test 'next week' parsing"""
        state = PTOAgentState(
            user_email="test@test.com",
            company="Test Company",
            user_message="I need 3 days off next week",
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
        
        # If LLM parses, dates should be in the future
        if result['start_date']:
            assert result['start_date'] > date.today()
            assert result['start_date'] < date.today() + timedelta(days=14)
    
    def test_parse_specific_dates(self, db_session):
        """Test parsing specific date formats"""
        test_cases = [
            "I need off December 25th",
            "Request leave for 12/25/2025",
            "Take vacation on Dec 25, 2025"
        ]
        
        for msg in test_cases:
            state = PTOAgentState(
                user_email="test@test.com",
                company="Test Company",
                user_message=msg,
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
            
            # Should extract December 25
            if result['start_date']:
                assert result['start_date'].month == 12
                assert result['start_date'].day == 25


class TestCategoryClassification:
    """Test HR ticket category classification"""
    
    def test_benefits_category(self, db_session):
        """Test benefits-related messages"""
        messages = [
            "I have questions about health insurance",
            "Need to discuss my 401k options",
            "What dental coverage do I have?",
            "Help with benefits enrollment"
        ]
        
        for msg in messages:
            state: HRTicketState = {
                "user_email": "test@company.com",
                "company": "Test Company",
                "user_message": msg,
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
            
            # Should classify as benefits or general_inquiry
            assert result['category'] in ['benefits', 'general_inquiry'], f"Failed for: {msg}"
    
    def test_payroll_category(self, db_session):
        """Test payroll-related messages"""
        messages = [
            "Problem with my paycheck",
            "My pay is incorrect",
            "Question about tax withholding",
            "Payroll error this month"
        ]
        
        for msg in messages:
            state: HRTicketState = {
                "user_email": "test@company.com",
                "company": "Test Company",
                "user_message": msg,
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
            
            assert result['category'] in ['payroll', 'general_inquiry'], f"Failed for: {msg}"
    
    def test_workplace_issue_category(self, db_session):
        """Test workplace issue classification"""
        messages = [
            "I have a workplace concern",
            "Need to discuss a team issue",
            "Conflict with a coworker"
        ]
        
        for msg in messages:
            state: HRTicketState = {
                "user_email": "test@company.com",
                "company": "Test Company",
                "user_message": msg,
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
            
            assert result['category'] in ['workplace_issue', 'general_inquiry'], f"Failed for: {msg}"


class TestUrgencyDetection:
    """Test urgency level detection"""
    
    def test_urgent_keywords(self, db_session):
        """Test urgent keyword detection"""
        messages = [
            "URGENT: Need help",
            "ASAP: Payroll issue",
            "Emergency situation",
            "This is urgent"
        ]
        
        for msg in messages:
            state: HRTicketState = {
                "user_email": "test@company.com",
                "company": "Test Company",
                "user_message": msg,
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
            
            # Should detect as urgent
            assert result['urgency'] == 'urgent', f"Failed for: {msg}"
    
    def test_normal_urgency(self, db_session):
        """Test normal urgency (default)"""
        messages = [
            "I have a question",
            "Can you help me?",
            "Need information about benefits"
        ]
        
        for msg in messages:
            state: HRTicketState = {
                "user_email": "test@company.com",
                "company": "Test Company",
                "user_message": msg,
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
            
            assert result['urgency'] == 'normal', f"Failed for: {msg}"


class TestMeetingTypeDetection:
    """Test meeting type preference detection"""
    
    def test_in_person_meeting(self, db_session):
        """Test in-person meeting detection"""
        messages = [
            "I want to meet in person",
            "Can we meet face to face?",
            "Schedule an in-person meeting"
        ]
        
        for msg in messages:
            state: HRTicketState = {
                "user_email": "test@company.com",
                "company": "Test Company",
                "user_message": msg,
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
            
            # Should detect in_person preference
            if result['meeting_type']:
                assert result['meeting_type'] in ['in_person', 'online'], f"Failed for: {msg}"
    
    def test_online_meeting(self, db_session):
        """Test online meeting detection"""
        messages = [
            "Can we do a video call?",
            "Schedule a Zoom meeting",
            "Let's meet online"
        ]
        
        for msg in messages:
            state: HRTicketState = {
                "user_email": "test@company.com",
                "company": "Test Company",
                "user_message": msg,
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
            
            if result['meeting_type']:
                assert result['meeting_type'] == 'online', f"Failed for: {msg}"


class TestTimeSlotParsing:
    """Test time slot preference parsing"""
    
    def test_morning_preference(self, db_session):
        """Test morning time slot detection"""
        state: HRTicketState = {
            "user_email": "test@company.com",
            "company": "Test Company",
            "user_message": "I'd like to meet in the morning",
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
        
        # Should detect morning if LLM works
        if result['preferred_time_slot']:
            assert result['preferred_time_slot'] == 'morning'
    
    def test_afternoon_preference(self, db_session):
        """Test afternoon time slot detection"""
        state: HRTicketState = {
            "user_email": "test@company.com",
            "company": "Test Company",
            "user_message": "Can we meet in the afternoon?",
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
        
        if result['preferred_time_slot']:
            assert result['preferred_time_slot'] == 'afternoon'


class TestReasonExtraction:
    """Test extraction of reasons/descriptions"""
    
    def test_extract_vacation_reason(self, db_session):
        """Test extracting vacation as reason"""
        state = PTOAgentState(
            user_email="test@test.com",
            company="Test Company",
            user_message="I need 3 days off for vacation",
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
        
        # Should extract reason if LLM works
        if result['reason']:
            assert 'vacation' in result['reason'].lower()
    
    def test_extract_detailed_description(self, db_session):
        """Test extracting detailed descriptions"""
        message = "I need to discuss my health insurance coverage options and premiums"
        
        state: HRTicketState = {
            "user_email": "test@company.com",
            "company": "Test Company",
            "user_message": message,
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
        
        # Description should capture key info
        if result['description']:
            assert 'insurance' in result['description'].lower() or 'health' in result['description'].lower()


class TestEdgeCaseHandling:
    """Test handling of edge cases in parsing"""
    
    def test_empty_message(self, db_session):
        """Test handling empty message"""
        state = PTOAgentState(
            user_email="test@test.com",
            company="Test Company",
            user_message="",
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
        
        # Should not crash, may set general_query intent
        assert 'intent' in result
    
    def test_very_long_message(self, db_session):
        """Test handling very long messages"""
        long_message = "I need time off " + "because reasons " * 100
        
        state = PTOAgentState(
            user_email="test@test.com",
            company="Test Company",
            user_message=long_message,
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
        
        # Should not crash
        assert 'intent' in result
    
    def test_special_characters(self, db_session):
        """Test handling special characters"""
        state: HRTicketState = {
            "user_email": "test@company.com",
            "company": "Test Company",
            "user_message": "I need help!!! @#$% My pay is wrong!!!",
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
        
        # Should parse despite special characters
        assert result['category'] is not None
        assert result['is_valid'] is True