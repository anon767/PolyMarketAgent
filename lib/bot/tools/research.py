"""Research and information gathering tools."""
import os
from typing import Dict, Any
from .base import BaseTool


class SearchNewsTool(BaseTool):
    """Search for recent news."""
    
    @property
    def name(self) -> str:
        return "search_news"
    
    @property
    def description(self) -> str:
        return "Search for recent news headlines using Google News RSS (no API key required). Useful for understanding current events that might affect prediction markets (politics, sports, crypto, etc.). Returns recent news articles with titles, sources, and publish dates."
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (e.g., 'Trump election', 'Bitcoin price', 'NFL playoffs', 'Federal Reserve')"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of results to return (default: 5)",
                    "default": 5
                }
            },
            "required": ["query"]
        }
    
    def execute(self, bot, query: str, max_results: int = 5, **kwargs) -> Dict[str, Any]:
        """Search for recent news."""
        print(f"  [Searching news for: {query}...]")
        try:
            from pygooglenews import GoogleNews
            gn = GoogleNews(lang='en', country='US')
            search = gn.search(query, when='7d')
            articles = [
                {
                    'title': e.title,
                    'source': e.source.get('title', 'Unknown'),
                    'published': e.published,
                    'url': e.link
                }
                for e in search['entries'][:max_results]
            ]
            return {"query": query, "results_count": len(articles), "articles": articles}
        except Exception as e:
            return {"query": query, "error": str(e), "note": "News unavailable"}


class ReadKnowledgeBaseTool(BaseTool):
    """Read the trading knowledge base."""
    
    @property
    def name(self) -> str:
        return "read_knowledge_base"
    
    @property
    def description(self) -> str:
        return "Read the trading knowledge base (kb.txt) which contains 14 proven Polymarket trading strategies and insights from successful traders. Use this to learn advanced strategies like 'Nothing Ever Happens', 'News Scalping', 'Fed Signal Trading', etc."
    
    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "required": []
        }
    
    def execute(self, bot, **kwargs) -> Dict[str, Any]:
        """Read the trading knowledge base."""
        print(f"  [Reading knowledge base...]")
        
        kb_path = "kb.txt"
        
        try:
            if os.path.exists(kb_path):
                with open(kb_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                return {
                    "available": True,
                    "content": content,
                    "note": "Knowledge base contains 14 proven Polymarket trading strategies"
                }
            else:
                return {
                    "available": False,
                    "error": "Knowledge base file (kb.txt) not found"
                }
        except Exception as e:
            return {"available": False, "error": str(e)}
