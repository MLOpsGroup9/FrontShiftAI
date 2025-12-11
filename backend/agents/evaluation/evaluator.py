"""
Main agent evaluator
Runs evaluation tests and calculates metrics
"""
import asyncio
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# ===== ADD THESE LINES =====
import os
from dotenv import load_dotenv

# Load environment variables
backend_dir = Path(__file__).resolve().parent.parent.parent
env_path = backend_dir / '.env'
load_dotenv(env_path)

# Verify critical env vars
if not os.getenv('GROQ_API_KEY'):
    print("⚠️  WARNING: GROQ_API_KEY not found in .env")
    print(f"   Looking in: {env_path}")
else:
    print("✓ GROQ_API_KEY loaded")
# ===== END ADD =====

# Import agents (AFTER loading env)
from agents.pto.agent import PTOAgent
from agents.hr_ticket.agent import get_hr_ticket_agent
from agents.website_extraction.agent import WebsiteExtractionAgent

# Import database models
from db.models import Base, User, Company, PTOBalance
from db.models import UserRole

# Import evaluation components
from .metrics import EvaluationMetrics, generate_summary_report
from .wandb_logger import WandbLogger, create_alert


class AgentEvaluator:
    """Evaluate all agents against test datasets"""
    
    def __init__(self, use_wandb: bool = True):
        """
        Initialize evaluator
        
        Args:
            use_wandb: Whether to log to W&B
        """
        self.test_data_dir = Path(__file__).parent / "test_data"
        self.results_dir = Path(__file__).parent / "results"
        self.results_dir.mkdir(exist_ok=True)
        
        self.metrics_calc = EvaluationMetrics()
        self.use_wandb = use_wandb
        self.wandb_logger = None
        
        # Setup test database with thread-safe settings
        # CHANGE THIS LINE:
        self.engine = create_engine(
            "sqlite:///./eval_test.db",
            connect_args={"check_same_thread": False}  # ADD THIS
        )
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        print("✓ Evaluator initialized")
    
    def _setup_test_db(self):
        """Create test company and user"""
        db = self.SessionLocal()
        
        try:
            # Check if already exists
            existing_company = db.query(Company).filter_by(name="Test Company").first()
            if not existing_company:
                company = Company(
                    name="Test Company",
                    domain="Technology",
                    email_domain="testcompany.com",
                    url="https://testcompany.com"
                )
                db.add(company)
                db.commit()
            
            existing_user = db.query(User).filter_by(email="test@testcompany.com").first()
            if not existing_user:
                user = User(
                    email="test@testcompany.com",
                    password="test123",
                    name="Test User",
                    role=UserRole.USER,
                    company="Test Company"
                )
                db.add(user)
                db.commit()
            
            existing_balance = db.query(PTOBalance).filter_by(
                email="test@testcompany.com"
            ).first()
            if not existing_balance:
                balance = PTOBalance(
                    email="test@testcompany.com",
                    company="Test Company",
                    year=2025,
                    total_days=15.0,
                    used_days=0.0,
                    pending_days=0.0
                )
                db.add(balance)
                db.commit()
            
            print("✓ Test database setup complete")
            
        finally:
            db.close()
    
    def load_test_data(self, filename: str) -> List[Dict]:
        """Load test cases from JSON file"""
        file_path = self.test_data_dir / filename
        with open(file_path, 'r') as f:
            data = json.load(f)
        return data.get('test_cases', [])
    
    async def evaluate_intent_classification(self) -> Dict[str, Any]:
        """Evaluate intent classification accuracy"""
        print("\n" + "="*60)
        print("EVALUATING INTENT CLASSIFICATION")
        print("="*60)
        
        test_cases = self.load_test_data("intent_classification.json")
        predictions = []
        
        for i, test_case in enumerate(test_cases, 1):
            message = test_case['input']
            expected = test_case['expected_agent']
            
            # Simple intent detection (copy from your test file)
            predicted = self._detect_intent(message)
            correct = (predicted == expected)
            
            predictions.append({
                'id': test_case['id'],
                'input': message,
                'expected': expected,
                'predicted': predicted,
                'correct': correct
            })
            
            status = "✓" if correct else "✗"
            print(f"  [{i}/{len(test_cases)}] {status} {test_case['id']}: {message[:50]}...")
        
        metrics = self.metrics_calc.calculate_intent_accuracy(predictions)
        
        print(f"\n  Accuracy: {metrics['accuracy']:.1%} ({metrics['correct']}/{metrics['total']})")
        
        return {
            'metrics': metrics,
            'predictions': predictions
        }
    
    def _detect_intent(self, message: str) -> str:
        """Simple intent detection (matches your test logic)"""
        message_lower = message.lower()
        
        # PTO keywords
        pto_keywords = [
            'pto', 'time off', 'leave', 'vacation', 'days off', 'balance',
            'request pto', 'book pto', 'need time', 'take leave'
        ]
        
        # HR Ticket keywords
        hr_keywords = [
            'meeting with hr', 'hr meeting', 'schedule', 'ticket', 'payroll',
            'benefits', 'insurance', 'help with', 'question about', 'urgent'
        ]
        
        # Website keywords
        web_keywords = [
            'business hours', 'contact', 'phone', 'email', 'address',
            'location', 'services', 'where', 'how can i', 'what is your'
        ]
        
        # RAG keywords
        rag_keywords = [
            'policy', 'what is the', 'tell me about', 'how does', 'explain',
            'company', 'dress code', 'remote work', 'performance review'
        ]
        
        # Check in priority order
        for keyword in pto_keywords:
            if keyword in message_lower:
                return 'pto'
        
        for keyword in hr_keywords:
            if keyword in message_lower:
                return 'hr_ticket'
        
        for keyword in web_keywords:
            if keyword in message_lower:
                return 'website_extraction'
        
        for keyword in rag_keywords:
            if keyword in message_lower:
                return 'rag'
        
        # Default to RAG for general questions
        return 'rag'
    
    async def evaluate_pto_agent(self) -> Dict[str, Any]:
        """Evaluate PTO agent"""
        print("\n" + "="*60)
        print("EVALUATING PTO AGENT")
        print("="*60)
        
        test_cases = self.load_test_data("pto_agent.json")
        results = []
        
        db = self.SessionLocal()
        agent = PTOAgent(db)
        
        try:
            for i, test_case in enumerate(test_cases, 1):
                # Reset PTO balance before each test to avoid depletion
                from db.models import PTOBalance, PTORequest
                balance = db.query(PTOBalance).filter_by(
                    email="test@testcompany.com"
                ).first()
                if balance:
                    balance.used_days = 0.0
                    balance.pending_days = 0.0
                    db.commit()
                
                # Also clean up any test PTO requests
                db.query(PTORequest).filter_by(
                    email="test@testcompany.com"
                ).delete()
                db.commit()
                
                start_time = time.time()
                
                try:
                    # Execute agent
                    result = await agent.execute(
                        user_email=test_case['user_email'],
                        company=test_case['company'],
                        message=test_case['input']
                    )
                    
                    latency_ms = (time.time() - start_time) * 1000
                    
                    # Check expectations
                    expected = test_case.get('expected', {})
                    response = result.get('response', '')
                    
                    # Check if expected terms are in response
                    expected_terms = expected.get('response_contains', [])
                    terms_found = [term for term in expected_terms if term.lower() in response.lower()]
                    
                    success = len(terms_found) >= len(expected_terms) * 0.7  # 70% threshold
                    
                    results.append({
                        'id': test_case['id'],
                        'input': test_case['input'],
                        'response': response,
                        'expected_contains': expected_terms,
                        'terms_found': len(terms_found),
                        'success': success,
                        'latency_ms': latency_ms,
                        'request_created': result.get('request_created', False)
                    })
                    
                    status = "✓" if success else "✗"
                    print(f"  [{i}/{len(test_cases)}] {status} {test_case['id']} ({latency_ms:.0f}ms)")
                    
                except Exception as e:
                    print(f"  [{i}/{len(test_cases)}] ✗ {test_case['id']} - Error: {e}")
                    results.append({
                        'id': test_case['id'],
                        'input': test_case['input'],
                        'response': '',
                        'expected_contains': [],
                        'terms_found': 0,
                        'success': False,
                        'latency_ms': 0,
                        'error': str(e)
                    })
            
            metrics = self.metrics_calc.calculate_agent_metrics(results)
            print(f"\n  Success Rate: {metrics['success']['success_rate']:.1%}")
            print(f"  Avg Latency: {metrics['latency']['avg_ms']:.0f}ms")
            
            return {
                'metrics': metrics,
                'results': results
            }
            
        finally:
            db.close()
    
    async def evaluate_hr_ticket_agent(self) -> Dict[str, Any]:
        """Evaluate HR Ticket agent"""
        print("\n" + "="*60)
        print("EVALUATING HR TICKET AGENT")
        print("="*60)
        
        test_cases = self.load_test_data("hr_ticket_agent.json")
        results = []
        
        db = self.SessionLocal()
        agent = get_hr_ticket_agent()
        
        try:
            for i, test_case in enumerate(test_cases, 1):
                # Clean up test tickets before each test
                from db.models import HRTicket
                db.query(HRTicket).filter_by(
                    email="test@testcompany.com"
                ).delete()
                db.commit()
                
                start_time = time.time()
                
                try:
                    result = await agent.process_message(
                        user_email=test_case['user_email'],
                        company=test_case['company'],
                        message=test_case['input'],
                        db=db
                    )
                    
                    latency_ms = (time.time() - start_time) * 1000
                    
                    expected = test_case.get('expected', {})
                    response = result.get('response', '')
                    
                    expected_terms = expected.get('response_contains', [])
                    terms_found = [term for term in expected_terms if term.lower() in response.lower()]
                    
                    success = len(terms_found) >= len(expected_terms) * 0.7
                    
                    results.append({
                        'id': test_case['id'],
                        'input': test_case['input'],
                        'response': response,
                        'expected_contains': expected_terms,
                        'terms_found': len(terms_found),
                        'success': success,
                        'latency_ms': latency_ms,
                        'ticket_created': result.get('ticket_created', False)
                    })
                    
                    status = "✓" if success else "✗"
                    print(f"  [{i}/{len(test_cases)}] {status} {test_case['id']} ({latency_ms:.0f}ms)")
                    
                except Exception as e:
                    print(f"  [{i}/{len(test_cases)}] ✗ {test_case['id']} - Error: {e}")
                    results.append({
                        'id': test_case['id'],
                        'input': test_case['input'],
                        'response': '',
                        'expected_contains': [],
                        'terms_found': 0,
                        'success': False,
                        'latency_ms': 0,
                        'error': str(e)
                    })
            
            metrics = self.metrics_calc.calculate_agent_metrics(results)
            print(f"\n  Success Rate: {metrics['success']['success_rate']:.1%}")
            print(f"  Avg Latency: {metrics['latency']['avg_ms']:.0f}ms")
            
            return {
                'metrics': metrics,
                'results': results
            }
            
        finally:
            db.close()
    
    async def evaluate_website_extraction_agent(self) -> Dict[str, Any]:
        """Evaluate Website Extraction agent"""
        print("\n" + "="*60)
        print("EVALUATING WEBSITE EXTRACTION AGENT")
        print("="*60)
        
        test_cases = self.load_test_data("website_extraction.json")
        results = []
        
        db = self.SessionLocal()
        agent = WebsiteExtractionAgent(db)
        
        try:
            for i, test_case in enumerate(test_cases, 1):
                start_time = time.time()
                
                try:
                    result = await agent.execute(
                        user_email=test_case['user_email'],
                        company=test_case['company'],
                        message=test_case['input']
                    )
                    
                    latency_ms = (time.time() - start_time) * 1000
                    
                    expected = test_case.get('expected', {})
                    response = result.get('response', '')
                    
                    expected_terms = expected.get('response_contains', [])
                    terms_found = [term for term in expected_terms if term.lower() in response.lower()]
                    
                    success = len(terms_found) >= len(expected_terms) * 0.7
                    
                    results.append({
                        'id': test_case['id'],
                        'input': test_case['input'],
                        'response': response,
                        'expected_contains': expected_terms,
                        'terms_found': len(terms_found),
                        'success': success,
                        'latency_ms': latency_ms,
                        'found_answer': result.get('found_answer', False)
                    })
                    
                    status = "✓" if success else "✗"
                    print(f"  [{i}/{len(test_cases)}] {status} {test_case['id']} ({latency_ms:.0f}ms)")
                    
                except Exception as e:
                    print(f"  [{i}/{len(test_cases)}] ✗ {test_case['id']} - Error: {e}")
                    results.append({
                        'id': test_case['id'],
                        'input': test_case['input'],
                        'response': '',
                        'expected_contains': [],
                        'terms_found': 0,
                        'success': False,
                        'latency_ms': 0,
                        'error': str(e)
                    })
            
            metrics = self.metrics_calc.calculate_agent_metrics(results)
            print(f"\n  Success Rate: {metrics['success']['success_rate']:.1%}")
            print(f"  Avg Latency: {metrics['latency']['avg_ms']:.0f}ms")
            
            return {
                'metrics': metrics,
                'results': results
            }
            
        finally:
            db.close()
    
    async def run_full_evaluation(self):
        """Run complete evaluation suite"""
        start_time = time.time()
        
        print("\n" + "="*60)
        print(f"STARTING FULL EVALUATION - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        # Setup test database
        self._setup_test_db()
        
        # Initialize W&B if enabled
        if self.use_wandb:
            self.wandb_logger = WandbLogger()
            self.wandb_logger.start_run(
                config={
                    'evaluation_date': datetime.now().isoformat(),
                    'test_counts': {
                        'intent': len(self.load_test_data("intent_classification.json")),
                        'pto': len(self.load_test_data("pto_agent.json")),
                        'hr_ticket': len(self.load_test_data("hr_ticket_agent.json")),
                        'website': len(self.load_test_data("website_extraction.json"))
                    }
                },
                tags=["full_evaluation"]
            )
        
        # Run evaluations
        intent_results = await self.evaluate_intent_classification()
        pto_results = await self.evaluate_pto_agent()
        hr_results = await self.evaluate_hr_ticket_agent()
        web_results = await self.evaluate_website_extraction_agent()
        
        # Compile all metrics
        all_metrics = {
            'intent_classification': intent_results['metrics'],
            'pto_agent': pto_results['metrics'],
            'hr_ticket_agent': hr_results['metrics'],
            'website_extraction_agent': web_results['metrics']
        }
        
        # Generate summary
        summary = generate_summary_report(all_metrics)
        print("\n" + summary)
        
        # Log to W&B
        if self.wandb_logger:
            self.wandb_logger.log_intent_classification(
                intent_results['metrics'],
                intent_results['predictions']
            )
            self.wandb_logger.log_agent_metrics('pto_agent', pto_results['metrics'])
            self.wandb_logger.log_agent_results('pto_agent', pto_results['results'])
            
            self.wandb_logger.log_agent_metrics('hr_ticket_agent', hr_results['metrics'])
            self.wandb_logger.log_agent_results('hr_ticket_agent', hr_results['results'])
            
            self.wandb_logger.log_agent_metrics('website_extraction_agent', web_results['metrics'])
            self.wandb_logger.log_agent_results('website_extraction_agent', web_results['results'])
            
            self.wandb_logger.log_summary(summary)
            
            # Check performance targets and create alerts
            targets = {
                'intent_accuracy_85': intent_results['metrics']['accuracy'] >= 0.85,
                'pto_p95_latency_5s': pto_results['metrics']['latency']['p95_ms'] < 5000,
                'hr_p95_latency_5s': hr_results['metrics']['latency']['p95_ms'] < 5000,
                'web_p95_latency_5s': web_results['metrics']['latency']['p95_ms'] < 5000
            }
            
            self.wandb_logger.log_performance_targets(targets)
            
            # Create alerts for failures
            if intent_results['metrics']['accuracy'] < 0.85:
                create_alert(
                    "Intent Accuracy Below Target",
                    f"Accuracy: {intent_results['metrics']['accuracy']:.1%} (target: 85%)",
                    "WARN"
                )
            
            self.wandb_logger.finish()
        
        # Save results locally
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = self.results_dir / f"evaluation_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'duration_seconds': time.time() - start_time,
                'metrics': all_metrics,
                'summary': summary
            }, f, indent=2)
        
        print(f"\n✓ Results saved to: {results_file}")
        print(f"✓ Total evaluation time: {time.time() - start_time:.1f}s")