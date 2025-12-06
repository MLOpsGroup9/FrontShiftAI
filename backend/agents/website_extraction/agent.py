"""Website Extraction Agent - LangGraph Workflow"""
import logging
from typing import Dict, Any
from langgraph.graph import StateGraph, END
from sqlalchemy.orm import Session
from agents.website_extraction.state import WebsiteExtractionState
from agents.website_extraction.nodes import (
    parse_query_node,
    resolve_domain_node,
    brave_search_node,
    analyze_results_node,
    generate_answer_node,
    suggest_hr_ticket_node,
    format_response_node
)

logger = logging.getLogger(__name__)


class WebsiteExtractionAgent:
    """Agent that searches company websites via Brave Search API"""
    
    def __init__(self, db: Session):
        self.db = db
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(WebsiteExtractionState)
        
        workflow.add_node("parse_query", lambda s: parse_query_node(s, self.db))
        workflow.add_node("resolve_domain", lambda s: resolve_domain_node(s, self.db))
        workflow.add_node("brave_search", lambda s: brave_search_node(s, self.db))
        workflow.add_node("analyze_results", lambda s: analyze_results_node(s, self.db))
        workflow.add_node("generate_answer", lambda s: generate_answer_node(s, self.db))
        workflow.add_node("suggest_hr_ticket", lambda s: suggest_hr_ticket_node(s, self.db))
        workflow.add_node("format_response", lambda s: format_response_node(s, self.db))
        
        workflow.set_entry_point("parse_query")
        workflow.add_edge("parse_query", "resolve_domain")
        workflow.add_edge("resolve_domain", "brave_search")
        workflow.add_edge("brave_search", "analyze_results")
        
        workflow.add_conditional_edges(
            "analyze_results",
            self._route_after_analysis,
            {
                "generate": "generate_answer",
                "suggest_hr": "suggest_hr_ticket"
            }
        )
        
        workflow.add_edge("generate_answer", "format_response")
        workflow.add_edge("suggest_hr_ticket", "format_response")
        workflow.add_edge("format_response", END)
        
        return workflow.compile()
    
    def _route_after_analysis(self, state: WebsiteExtractionState) -> str:
        if state.get("found_answer", False):
            return "generate"
        return "suggest_hr"
    
    async def execute(
        self,
        user_email: str,
        company: str,
        message: str,
        triggered_by: str = "direct",
        original_query: str = None
    ) -> Dict[str, Any]:
        """Execute the website extraction workflow"""
        logger.info(f"Website extraction for {company}: {message[:50]}...")
        
        initial_state: WebsiteExtractionState = {
            "user_email": user_email,
            "company": company,
            "user_message": message,
            "original_query": original_query or message,
            "triggered_by": triggered_by,
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
        
        try:
            final_state = await self.graph.ainvoke(initial_state)
            
            return {
                "response": final_state["agent_response"],
                "found_answer": final_state.get("found_answer", False),
                "answer": final_state.get("answer"),
                "source_urls": final_state.get("source_urls", []),
                "confidence": final_state.get("confidence_score", 0.0),
                "suggest_hr_ticket": final_state.get("suggest_hr_ticket", False),
                "hr_ticket_suggestion": final_state.get("hr_ticket_suggestion"),
                "search_time_ms": final_state.get("search_time_ms"),
                "triggered_by": triggered_by
            }
            
        except Exception as e:
            logger.error(f"Website extraction error: {e}")
            return {
                "response": f"I encountered an error searching {company}'s website. Would you like to create an HR ticket instead?",
                "found_answer": False,
                "answer": None,
                "source_urls": [],
                "confidence": 0.0,
                "suggest_hr_ticket": True,
                "hr_ticket_suggestion": None,
                "search_time_ms": None,
                "triggered_by": triggered_by,
                "error": str(e)
            }


_agent_instance = None


def get_website_extraction_agent(db: Session) -> WebsiteExtractionAgent:
    """Get Website Extraction Agent instance"""
    return WebsiteExtractionAgent(db)

