"""Website Extraction Agent LangGraph Nodes"""
import json
import logging
from sqlalchemy.orm import Session
from agents.website_extraction.state import WebsiteExtractionState
from agents.website_extraction.tools import (
    brave_search,
    get_company_domain,
    rank_results,
    CONFIDENCE_THRESHOLD
)
from agents.utils.llm_client import get_llm_client

logger = logging.getLogger(__name__)


def parse_query_node(state: WebsiteExtractionState, db: Session) -> WebsiteExtractionState:
    """Parse user query to extract search topic and keywords"""
    llm_client = get_llm_client()
    
    system_prompt = """Extract search information from the user's query. Respond with JSON only.
{
    "search_topic": "main topic user is asking about",
    "search_keywords": ["keyword1", "keyword2", "keyword3"],
    "info_type": "contact|hours|services|policies|pricing|locations|general",
    "search_query": "optimized search query string"
}"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": state["user_message"]}
    ]
    
    try:
        response = llm_client.chat(messages, json_mode=True, temperature=0.2)
        parsed = json.loads(response)
        
        state["search_topic"] = parsed.get("search_topic", state["user_message"][:50])
        state["search_keywords"] = parsed.get("search_keywords", state["user_message"].split()[:5])
        state["info_type"] = parsed.get("info_type", "general")
        state["search_query"] = parsed.get("search_query", state["user_message"])
        
    except Exception as e:
        logger.warning(f"LLM parsing failed: {e}, using fallback")
        words = state["user_message"].lower().split()
        state["search_topic"] = " ".join(words[:5])
        state["search_keywords"] = [w for w in words if len(w) > 3][:5]
        state["info_type"] = "general"
        state["search_query"] = state["user_message"]
    
    return state


def resolve_domain_node(state: WebsiteExtractionState, db: Session) -> WebsiteExtractionState:
    """Resolve company domain from database"""
    company_url, company_domain = get_company_domain(db, state["company"])
    
    state["company_url"] = company_url
    state["company_domain"] = company_domain
    state["domain_found"] = company_domain is not None
    
    if not company_domain:
        logger.warning(f"No domain found for company: {state['company']}")
    
    return state


def brave_search_node(state: WebsiteExtractionState, db: Session) -> WebsiteExtractionState:
    """Execute Brave Search API"""
    import time
    start_time = time.time()
    
    results, error = brave_search(
        query=state["search_query"],
        site_domain=state["company_domain"]
    )
    
    state["search_time_ms"] = (time.time() - start_time) * 1000
    
    if error:
        state["brave_results"] = []
        state["search_successful"] = False
        state["search_error"] = error
        logger.error(f"Brave search failed: {error}")
    else:
        state["brave_results"] = results
        state["search_successful"] = True
        state["search_error"] = None
    
    return state


def analyze_results_node(state: WebsiteExtractionState, db: Session) -> WebsiteExtractionState:
    """Analyze and rank search results"""
    if not state["brave_results"]:
        state["ranked_results"] = []
        state["best_match"] = None
        state["confidence_score"] = 0.0
        state["found_answer"] = False
        return state
    
    ranked = rank_results(
        results=state["brave_results"],
        keywords=state["search_keywords"],
        topic=state["search_topic"]
    )
    
    state["ranked_results"] = ranked
    state["best_match"] = ranked[0] if ranked else None
    state["confidence_score"] = ranked[0]["relevance_score"] if ranked else 0.0
    state["found_answer"] = state["confidence_score"] >= CONFIDENCE_THRESHOLD
    
    return state


def generate_answer_node(state: WebsiteExtractionState, db: Session) -> WebsiteExtractionState:
    """Generate answer from search results using LLM"""
    if not state["best_match"]:
        state["answer"] = None
        state["source_urls"] = []
        return state
    
    llm_client = get_llm_client()
    
    context_parts = []
    sources = []
    for r in state["ranked_results"][:3]:
        context_parts.append(f"Title: {r['title']}\nContent: {r['description']}")
        if r.get("extra_snippets"):
            context_parts.append("Additional: " + " | ".join(r["extra_snippets"]))
        sources.append(r["url"])
    
    context = "\n\n".join(context_parts)
    
    system_prompt = f"""You are answering a question using information found on {state['company']}'s website.
Use ONLY the provided search results. Be concise and direct.
If the information is incomplete, mention what you found and note any gaps."""

    user_prompt = f"""Question: {state['user_message']}

Search Results:
{context}

Provide a helpful answer based on these results."""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]
    
    try:
        answer = llm_client.chat(messages, temperature=0.5)
        state["answer"] = answer
    except Exception as e:
        logger.error(f"Answer generation failed: {e}")
        best = state["best_match"]
        state["answer"] = f"{best['title']}\n\n{best['description']}"
    
    state["source_urls"] = sources[:3]
    return state


def suggest_hr_ticket_node(state: WebsiteExtractionState, db: Session) -> WebsiteExtractionState:
    """Generate HR ticket suggestion when search fails"""
    topic = state["search_topic"] or state["user_message"][:50]
    company = state["company"]
    
    if state["search_error"]:
        suggestion = f"""I'm having trouble searching {company}'s website right now.

Would you like me to create an HR ticket instead? Someone from the HR team can get back to you with this information.

Reply **"yes"** or **"create ticket"** to proceed."""
    else:
        suggestion = f"""I searched {company}'s website but couldn't find specific information about "{topic}".

Would you like me to create an HR ticket so someone from {company}'s HR team can help you with this?

Reply **"yes"** or **"create ticket"** and I'll set that up for you."""
    
    state["suggest_hr_ticket"] = True
    state["hr_ticket_suggestion"] = suggestion
    state["answer"] = None
    state["source_urls"] = []
    
    return state


def format_response_node(state: WebsiteExtractionState, db: Session) -> WebsiteExtractionState:
    """Format final response"""
    if state["found_answer"] and state["answer"]:
        source_display = state["source_urls"][0] if state["source_urls"] else state["company_domain"]
        
        if state["confidence_score"] >= 0.7:
            response = f"""🔍 Found on {state['company']}'s website:

{state['answer']}

📎 Source: {source_display}"""
        else:
            response = f"""🔍 I found some related information on {state['company']}'s website:

{state['answer']}

📎 Source: {source_display}

⚠️ For the most accurate information, you may want to verify directly or create an HR ticket."""
    else:
        response = state["hr_ticket_suggestion"] or "I couldn't find that information. Would you like to create an HR ticket?"
    
    state["agent_response"] = response
    return state

