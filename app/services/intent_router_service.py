import json
import re
import requests
from typing import Optional, Dict, Any

from app.core.config import settings
from app.utils.helpers import logger, ExternalApiTimer
from app.providers.provider_manager import provider_manager


class IntentRouterService:
    """Classify chat queries and route accordingly.

    Attempts to use LangChain when available; falls back to direct OpenAI call.
    """

    def __init__(self) -> None:
        try:
            # Optional LangChain import
            from langchain_core.prompts import ChatPromptTemplate  # type: ignore
            from langchain_openai import ChatOpenAI  # type: ignore
            self._lc_available = True
            self._lc_prompt_cls = ChatPromptTemplate
            self._lc_chat_cls = ChatOpenAI
        except Exception:
            self._lc_available = False
            self._lc_prompt_cls = None
            self._lc_chat_cls = None

    def classify_intent(self, query: str) -> Dict[str, Any]:
        """Return { intent: 'general'|'peptide', peptide_name?: str }

        Rules:
        - Use a quick rule-based heuristic for greetings → general
        - If LangChain is available, use it to classify
        - If LangChain is not available, default to 'peptide' (safer routing) without any LLM fallback
        """
        # Quick heuristic for very common greetings
        if self._looks_like_greeting(query):
            return {"intent": "general"}

        if self._lc_available:
            try:
                return self._classify_with_langchain(query)
            except Exception as e:
                logger.warning(f"LangChain classification failed; defaulting to 'peptide': {str(e)}")

        # No LLM fallback; default to peptide flow to avoid hallucination-prone classification
        return {"intent": "peptide", "peptide_name": None}

    def answer_general_query(self, query: str) -> str:
        """Answer general queries directly via LLM, bypassing peptide flow."""
        try:
            system_prompt = (
                "You are a concise helpful assistant. If the user greets, reply briefly. "
                "Avoid mentioning peptides unless asked. Plain text only."
            )
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ]

            response = provider_manager.openai.generate_chat_completion(
                messages=messages,
                model="gpt-4o",
                temperature=0.3,
                max_tokens=150,
                timeout=20
            )
            
            return response.strip()
            
        except Exception as e:
            logger.warning(f"General query failed: {str(e)}")
            return "Hello! How can I help you today?"

    # ----------------------------
    # Internal helpers
    # ----------------------------
    def _looks_like_greeting(self, query: str) -> bool:
        q = (query or "").strip().lower()
        if not q:
            return True
        greeting_words = [
            "hi", "hello", "hey", "hey there", "good morning", "good evening", "good afternoon",
            "how are you", "what's up", "sup", "yo"
        ]
        if any(w in q for w in greeting_words) and not re.search(r"pept|chemical|mechanism|research|dose|sequence", q):
            return True
        return False

    def _classify_with_langchain(self, query: str) -> Dict[str, Any]:
        # Minimal LC chain: prompt -> LLM -> JSON output
        ChatPromptTemplate = self._lc_prompt_cls  # type: ignore
        ChatOpenAI = self._lc_chat_cls  # type: ignore

        prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "Classify the user query. Output strict JSON with keys: intent ('general'|'peptide'), "
                "and peptide_name (string or null). Classify as 'general' if the query is not about peptides "
                "or chemicals (e.g., greetings)."
            )),
            ("user", "{query}")
        ])
        llm = ChatOpenAI(model="gpt-4o", temperature=0.0, openai_api_key=provider_manager.openai.api_key)
        chain = prompt | llm
        res = chain.invoke({"query": query})
        text = getattr(res, "content", "{}")
        try:
            data = json.loads(text)
        except Exception:
            data = {"intent": "general", "peptide_name": None}
        intent = str(data.get("intent", "general")).lower()
        peptide_name = data.get("peptide_name")
        if intent not in ("general", "peptide"):
            intent = "general"
        return {"intent": intent, "peptide_name": peptide_name}

    # Removed non-LangChain LLM fallback by request to avoid hallucinations


