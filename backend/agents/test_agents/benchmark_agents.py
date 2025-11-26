"""
Performance benchmarking for agent workflows
Measures latency, throughput, and resource usage
"""
import sys
from pathlib import Path
import time
import statistics
import asyncio

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from db.models import Base, User, Company, PTOBalance
from db.connection import init_db
from agents.pto.agent import PTOAgent
from agents.hr_ticket.agent import HRTicketAgent


# Test database
TEST_DB = "sqlite:///./benchmark_test.db"


def setup_benchmark_db():
    """Setup database for benchmarking"""
    engine = create_engine(TEST_DB)
    Base.metadata.create_all(bind=engine)
    
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    
    # Create test company
    company = Company(
        name="Benchmark Company",
        domain="Technology",
        email_domain="benchmark.com",
        url="https://benchmark.com"
    )
    session.add(company)
    
    # Create test user
    user = User(
        email="bench@benchmark.com",
        password="test",
        name="Benchmark User",
        role="user",
        company="Benchmark Company"
    )
    session.add(user)
    
    # Create PTO balance
    balance = PTOBalance(
        email="bench@benchmark.com",
        company="Benchmark Company",
        year=2025,
        total_days=15.0,
        used_days=0.0,
        pending_days=0.0
    )
    session.add(balance)
    
    session.commit()
    return session


async def benchmark_pto_agent(session, iterations=100):
    """Benchmark PTO agent performance"""
    print(f"\n{'='*60}")
    print(f"PTO Agent Benchmark ({iterations} iterations)")
    print(f"{'='*60}\n")
    
    agent = PTOAgent(session)
    times = []
    
    for i in range(iterations):
        start = time.time()
        
        result = await agent.execute(
            user_email="bench@benchmark.com",
            company="Benchmark Company",
            message="I need 3 days off next week"
        )
        
        elapsed = time.time() - start
        times.append(elapsed)
        
        if (i + 1) % 20 == 0:
            print(f"Progress: {i + 1}/{iterations} requests completed")
    
    # Calculate statistics
    sorted_times = sorted(times)
    
    print(f"\nResults:")
    print(f"  Total requests: {iterations}")
    print(f"  Average: {statistics.mean(times):.3f}s")
    print(f"  Median (P50): {statistics.median(times):.3f}s")
    print(f"  P95: {sorted_times[int(len(sorted_times) * 0.95)]:.3f}s")
    print(f"  P99: {sorted_times[int(len(sorted_times) * 0.99)]:.3f}s")
    print(f"  Min: {min(times):.3f}s")
    print(f"  Max: {max(times):.3f}s")
    print(f"  Std Dev: {statistics.stdev(times):.3f}s")
    
    # Performance assertions
    avg_time = statistics.mean(times)
    p95_time = sorted_times[int(len(sorted_times) * 0.95)]
    
    print(f"\nPerformance Targets:")
    print(f"  Average < 3.0s: {'✓ PASS' if avg_time < 3.0 else '✗ FAIL'}")
    print(f"  P95 < 5.0s: {'✓ PASS' if p95_time < 5.0 else '✗ FAIL'}")
    
    return times


async def benchmark_hr_ticket_agent(session, iterations=100):
    """Benchmark HR ticket agent performance"""
    print(f"\n{'='*60}")
    print(f"HR Ticket Agent Benchmark ({iterations} iterations)")
    print(f"{'='*60}\n")
    
    agent = HRTicketAgent()
    times = []
    
    for i in range(iterations):
        start = time.time()
        
        result = await agent.process_message(
            user_email="bench@benchmark.com",
            company="Benchmark Company",
            message="I need to discuss my health insurance",
            db=session
        )
        
        elapsed = time.time() - start
        times.append(elapsed)
        
        if (i + 1) % 20 == 0:
            print(f"Progress: {i + 1}/{iterations} requests completed")
    
    # Calculate statistics
    sorted_times = sorted(times)
    
    print(f"\nResults:")
    print(f"  Total requests: {iterations}")
    print(f"  Average: {statistics.mean(times):.3f}s")
    print(f"  Median (P50): {statistics.median(times):.3f}s")
    print(f"  P95: {sorted_times[int(len(sorted_times) * 0.95)]:.3f}s")
    print(f"  P99: {sorted_times[int(len(sorted_times) * 0.99)]:.3f}s")
    print(f"  Min: {min(times):.3f}s")
    print(f"  Max: {max(times):.3f}s")
    print(f"  Std Dev: {statistics.stdev(times):.3f}s")
    
    # Performance assertions
    avg_time = statistics.mean(times)
    p95_time = sorted_times[int(len(sorted_times) * 0.95)]
    
    print(f"\nPerformance Targets:")
    print(f"  Average < 3.0s: {'✓ PASS' if avg_time < 3.0 else '✗ FAIL'}")
    print(f"  P95 < 5.0s: {'✓ PASS' if p95_time < 5.0 else '✗ FAIL'}")
    
    return times


async def benchmark_concurrent_load(session, concurrent_users=10):
    """Test performance under concurrent load"""
    print(f"\n{'='*60}")
    print(f"Concurrent Load Test ({concurrent_users} simultaneous users)")
    print(f"{'='*60}\n")
    
    pto_agent = PTOAgent(session)
    hr_agent = HRTicketAgent()
    
    async def user_simulation(user_id):
        """Simulate a single user's requests"""
        times = []
        
        # PTO request
        start = time.time()
        pto_result = await pto_agent.execute(
            user_email=f"user{user_id}@benchmark.com",
            company="Benchmark Company",
            message="I need time off next week"
        )
        times.append(time.time() - start)
        
        # HR ticket
        start = time.time()
        hr_result = await hr_agent.process_message(
            user_email=f"user{user_id}@benchmark.com",
            company="Benchmark Company",
            message="I have a question",
            db=session
        )
        times.append(time.time() - start)
        
        return times
    
    # Run concurrent simulations
    start_all = time.time()
    
    tasks = [user_simulation(i) for i in range(concurrent_users)]
    results = await asyncio.gather(*tasks)
    
    total_time = time.time() - start_all
    
    # Flatten results
    all_times = [t for user_times in results for t in user_times]
    
    print(f"Results:")
    print(f"  Total time: {total_time:.3f}s")
    print(f"  Total requests: {len(all_times)}")
    print(f"  Requests/second: {len(all_times) / total_time:.2f}")
    print(f"  Average latency: {statistics.mean(all_times):.3f}s")
    print(f"  Max latency: {max(all_times):.3f}s")
    
    # Check if performance degrades under load
    avg_latency = statistics.mean(all_times)
    print(f"\nLoad Test Targets:")
    print(f"  Average latency < 5.0s: {'✓ PASS' if avg_latency < 5.0 else '✗ FAIL'}")
    print(f"  Max latency < 10.0s: {'✓ PASS' if max(all_times) < 10.0 else '✗ FAIL'}")


def cleanup_benchmark_db():
    """Clean up benchmark database"""
    import os
    db_file = "./benchmark_test.db"
    if os.path.exists(db_file):
        os.remove(db_file)
        print(f"\nCleaned up benchmark database")


async def main():
    """Run all benchmarks"""
    print("\n" + "="*60)
    print("FrontShiftAI Agent Performance Benchmarks")
    print("="*60)
    
    # Setup
    session = setup_benchmark_db()
    
    try:
        # Run benchmarks
        await benchmark_pto_agent(session, iterations=50)
        await benchmark_hr_ticket_agent(session, iterations=50)
        await benchmark_concurrent_load(session, concurrent_users=5)
        
        print("\n" + "="*60)
        print("Benchmark Complete!")
        print("="*60 + "\n")
        
    finally:
        session.close()
        cleanup_benchmark_db()


if __name__ == "__main__":
    asyncio.run(main())