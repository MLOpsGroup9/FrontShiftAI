"""
Simple script to run agent evaluation
Usage: python -m agents.evaluation.run_evaluation
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(backend_dir))

from agents.evaluation.evaluator import AgentEvaluator


async def main():
    """Run full evaluation"""
    print("🚀 Starting Agent Evaluation System")
    print("-" * 60)
    
    evaluator = AgentEvaluator(use_wandb=True)
    await evaluator.run_full_evaluation()
    
    print("\n✅ Evaluation complete!")


if __name__ == "__main__":
    asyncio.run(main())