from sqlalchemy.orm import Session
from app.models.peptide_info_session import PeptideInfoSession, PeptideInfoMessage
from app.services.search_service import SearchService
from app.core.config import settings
from app.utils.helpers import logger, ExternalApiTimer
from typing import Dict, Any, List, Optional
import requests
import json
from datetime import datetime

class PeptideInfoService:
    def __init__(self):
        """Initialize the peptide info service"""
        self.search_service = SearchService()
        self.tavily_api_key = settings.TAVILY_API_KEY
        self.openai_api_key = settings.OPENAI_API_KEY
        self.accuracy_threshold = 0.75  # Threshold for Tavily accuracy

    def generate_peptide_info(self, peptide_name: str, requirements: str = "", db: Session = None) -> Dict[str, Any]:
        """
        Generate peptide information using Tavily-first approach with domain filtering and LLM judge,
        with SerpAPI fallback when no allowed domain matches.
        
        Flow:
        1. Tavily search and collect all source URLs (always log all URLs)
        2. If allowed-urls contains global '*' → take top 5 by Tavily score
           Else → filter Tavily results by allowed domains
        3. If we have selected Tavily items → run LLM Judge; if Yes, tune and return
        4. If Judge = No or no domain match (and no '*') → fallback to SerpAPI approach
        5. Save all data to database
        """
        try:
            logger.info(f"Starting peptide info generation for: {peptide_name}")

            # Step 1: Tavily search with domain-aware selection
            tavily_result = self._search_with_tavily(peptide_name, requirements, db)

            # Print all Tavily source URLs gathered for the query
            all_urls = (tavily_result or {}).get("all_urls", [])
            if all_urls:
                logger.info("Tavily gathered source URLs:")
                for i, u in enumerate(all_urls, start=1):
                    logger.info(f"  [{i}] {u}")

            # If we have selected Tavily items, run LLM judge on the filtered content
            if tavily_result and tavily_result.get("urls"):
                joined_content = "\n\n".join(tavily_result["content"])[:4000]
                judge_accepted = self._judge_relevance_yes_no(
                    user_query=requirements or peptide_name,
                    candidate_content=joined_content,
                    peptide_name=peptide_name
                )
                logger.info(f"LLM Judge decision on Tavily content: {'YES' if judge_accepted else 'NO'}")

                if judge_accepted:
                    tuned_response = self._tune_with_llm(peptide_name, requirements, tavily_result["content"]) 
                    return {
                        "peptide_name": peptide_name,
                        "requirements": requirements,
                        "generated_response": tuned_response,
                        "source": "tavily+tuned",
                        "accuracy_score": tavily_result.get("accuracy_score", 0),
                        "source_content": tavily_result.get("content", []),
                        "source_urls": tavily_result.get("urls", []),
                        "metadata": {
                            "tavily_scores": tavily_result.get("scores", []),
                            "tavily_all_urls": all_urls,
                            "tavily_filter_mode": tavily_result.get("filter_mode"),
                            "judge": "yes",
                            "search_timestamp": datetime.utcnow().isoformat()
                        }
                    }

                # Judge said no → fall through to SerpAPI
                logger.info("Judge said NO for Tavily content; falling back to SerpAPI")

            else:
                # No Tavily domain match or no results
                logger.info("No Tavily domain match or no Tavily results available; falling back to SerpAPI")

            # Fallback to SerpAPI approach
            serpapi_result = self._search_with_serpapi(peptide_name, requirements, db)

            return {
                "peptide_name": peptide_name,
                "requirements": requirements,
                "generated_response": serpapi_result["generated_response"],
                "source": "serpapi+tuned",
                "accuracy_score": serpapi_result.get("similarity_score", 0),
                "source_content": serpapi_result.get("source_content", ""),
                "source_urls": serpapi_result.get("source_sites", []),
                "metadata": {
                    "serpapi_search_results": len(serpapi_result.get("source_sites", [])),
                    "tavily_all_urls": all_urls,
                    "judge": "no",
                    "search_timestamp": datetime.utcnow().isoformat()
                }
            }

        except Exception as e:
            logger.error(f"Error generating peptide info: {str(e)}")
            raise

    def _search_with_tavily(self, peptide_name: str, requirements: str, db: Session) -> Optional[Dict[str, Any]]:
        """Search using Tavily API with domain-based filtering and wildcard handling"""
        try:
            query = f"{peptide_name} peptide"
            if requirements:
                query += f" {requirements}"

            logger.info(f"Searching Tavily with query: {query}")

            headers = {
                "Authorization": f"Bearer {self.tavily_api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "query": query,
                "search_depth": "advanced",
                "include_answer": True,
                "include_raw_content": True,
                "max_results": 10
            }

            with ExternalApiTimer("tavily", operation="search", metadata={"q": query}) as t:
                response = requests.post(
                    "https://api.tavily.com/search",
                    headers=headers,
                    json=payload,
                    timeout=30
                )
                t.set_status(status_code=response.status_code, success=(response.status_code == 200))

            if response.status_code != 200:
                logger.error(f"Tavily API error: {response.status_code} - {response.text}")
                return None

            data = response.json()
            results = data.get("results", []) or []
            logger.info(f"Tavily response received: {len(results)} results")

            # Build raw lists
            raw_items = []
            all_urls = []
            for result in results:
                url = result.get("url", "")
                score = result.get("score", 0)
                content = result.get("content", "")
                raw_items.append({"url": url, "score": score, "content": content})
                if url:
                    all_urls.append(url)

            # Log all URLs for visibility
            if all_urls:
                logger.info("All Tavily URLs (unfiltered):")
                for i, u in enumerate(all_urls, start=1):
                    logger.info(f"  [{i}] {u}")

            # Load allowed urls from DB
            try:
                from app.services.allowed_url_service import AllowedUrlService
                from urllib.parse import urlparse
                allowed_service = AllowedUrlService(db)
                allowed_urls = allowed_service.get_all_allowed_urls()
            except Exception as e:
                logger.warning(f"Failed to load allowed URLs, proceeding without domain filter: {e}")
                allowed_urls = []

            def normalize_domain(u: str) -> str:
                try:
                    host = urlparse(u).netloc.lower()
                    return host[4:] if host.startswith('www.') else host
                except Exception:
                    return ""

            def is_domain_allowed(u: str) -> bool:
                domain = normalize_domain(u)
                for allowed in allowed_urls:
                    allowed_str = allowed.url
                    if not allowed_str or '*' in allowed_str:
                        continue
                    allowed_domain = normalize_domain(allowed_str)
                    if not allowed_domain:
                        continue
                    if domain == allowed_domain or domain.endswith('.' + allowed_domain):
                        return True
                # Check global wildcard
                for allowed in allowed_urls:
                    if allowed.url == '*':
                        return True
                return False

            has_global_wildcard = any((a.url == '*') for a in allowed_urls)

            # Select items according to domain policy
            selected_items = []
            filter_mode = 'wildcard' if has_global_wildcard else 'domain'
            if has_global_wildcard:
                # Take top 5 by score
                selected_items = sorted(raw_items, key=lambda x: x.get("score", 0), reverse=True)[:5]
            else:
                # Filter by allowed domains
                selected_items = [it for it in raw_items if is_domain_allowed(it.get("url", ""))]

            if not selected_items and not has_global_wildcard:
                logger.info("No Tavily results matched allowed domains and no global wildcard present")
                return {
                    "content": [],
                    "urls": [],
                    "scores": [],
                    "accuracy_score": 0.0,
                    "answer": data.get("answer", ""),
                    "all_urls": all_urls,
                    "filter_mode": filter_mode
                }

            # Deduplicate selected items by normalized URL (domain + path, ignore query/fragment)
            def normalize_for_dedupe(u: str) -> str:
                try:
                    from urllib.parse import urlparse
                    p = urlparse(u)
                    host = p.netloc.lower()
                    host = host[4:] if host.startswith('www.') else host
                    path = (p.path or '/').rstrip('/') or '/'
                    return f"{host}{path}"
                except Exception:
                    return u or ""

            seen_keys = set()
            unique_items = []
            for it in selected_items:
                key = normalize_for_dedupe(it.get("url", ""))
                if key and key in seen_keys:
                    continue
                seen_keys.add(key)
                unique_items.append(it)

            # Prepare return payload from unique items only
            content = [it.get("content", "") for it in unique_items]
            urls = [it.get("url", "") for it in unique_items]
            scores = [it.get("score", 0.0) for it in unique_items]
            avg_score = sum(scores) / len(scores) if scores else 0.0

            logger.info(f"Selected {len(urls)} Tavily URLs using filter mode '{filter_mode}' (deduped)")
            for i, u in enumerate(urls, start=1):
                logger.info(f"  [selected {i}] {u}")

            return {
                "content": content,
                "urls": urls,
                "scores": scores,
                "accuracy_score": avg_score,
                "answer": data.get("answer", ""),
                "all_urls": all_urls,
                "filter_mode": filter_mode
            }

        except Exception as e:
            logger.error(f"Error with Tavily search: {str(e)}")
            return None

    def _tune_with_llm(self, peptide_name: str, requirements: str, content: List[str]) -> str:
        """Tune the content with LLM to generate a comprehensive response"""
        try:
            logger.info(f"Tuning content with LLM for peptide: {peptide_name}")
            
            # Combine content
            combined_content = "\n\n".join(content)
            
            # Create prompt (using same format as SerpAPI)
            prompt = f"""
Based on the following information about {peptide_name}, 
please provide a focused response specifically addressing: {requirements if requirements else "General information about the peptide"}

Information sources:
{combined_content}

IMPORTANT FORMATTING REQUIREMENTS:
- Write in plain text only, NO markdown formatting (no **, #, -, etc.)
- Use normal paragraphs with proper spacing
- Keep response under 1000 characters
- Make it easy to read and understand
- Focus only on what was asked for - do not include extra information unless directly relevant
- Keep the response focused and to the point
"""
            
            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "You are a peptide research expert providing accurate, scientific information."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 2000,
                "temperature": 0.3
            }
            
            with ExternalApiTimer("openai", operation="chat.completions") as t:
                response = requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=60
                )
                t.set_status(status_code=response.status_code, success=(response.status_code == 200))
            
            if response.status_code == 200:
                data = response.json()
                response_text = data["choices"][0]["message"]["content"]
                
                # Ensure response is ≤ 1000 characters
                if len(response_text) > 1000:
                    logger.info(f"Response was {len(response_text)} characters, truncating to 1000 characters")
                    response_text = response_text[:1000] + "..."
                
                return response_text
            else:
                logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
                return "Error generating response with LLM."
                
        except Exception as e:
            logger.error(f"Error tuning with LLM: {str(e)}")
            return "Error generating response with LLM."

    def _judge_relevance_yes_no(self, user_query: str, candidate_content: str, peptide_name: Optional[str]) -> bool:
        """Binary LLM judge: returns True if content is relevant to the query/topic, else False"""
        try:
            if not self.openai_api_key:
                raise ValueError("OpenAI API key not configured")

            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }

            name_hint = peptide_name or "the peptide"
            system_prompt = (
                "You are a strict binary relevance judge. "
                "Given a user query and candidate content, respond with exactly one word: Yes or No. "
                "Say Yes only if the content directly helps answer the query about the specified peptide/topic."
            )
            user_prompt = (
                f"Query about {name_hint}: {user_query}\n\n"
                f"Candidate Content:\n{candidate_content}\n\n"
                "Answer with only one word: Yes or No"
            )

            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.0,
                "max_tokens": 2
            }

            with ExternalApiTimer("openai", operation="chat.completions") as t:
                response = requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=30
                )
                t.set_status(status_code=response.status_code, success=(response.status_code == 200))

            if response.status_code == 200:
                data = response.json()
                answer = data["choices"][0]["message"]["content"].strip().lower()
                return answer.startswith("y")  # yes
            else:
                logger.error(f"OpenAI Judge API error: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error in LLM judge: {str(e)}")
            return False

    def _search_with_serpapi(self, peptide_name: str, requirements: str, db: Session) -> Dict[str, Any]:
        """Fallback to SerpAPI search approach"""
        try:
            logger.info(f"Using SerpAPI fallback for peptide: {peptide_name}")
            
            from app.models.search import SearchRequest
            
            search_request = SearchRequest(
                peptide_name=peptide_name,
                requirements=requirements
            )
            
            # Use existing search service
            search_response = self.search_service.search_peptide(search_request, db)
            
            # Extract source content (no per-site content available; include title, URL, and length if present)
            source_content = []
            for site in search_response.source_sites:
                title = getattr(site, "title", "") or ""
                url = getattr(site, "url", "") or ""
                length = getattr(site, "content_length", None)
                length_part = f" (content length: {length})" if length is not None else ""
                source_content.append(f"Source: {title} - {url}{length_part}")
            
            return {
                "generated_response": search_response.generated_response,
                "similarity_score": max((site.similarity_score or 0) for site in search_response.source_sites) if search_response.source_sites else 0,
                "source_content": "\n\n".join(source_content),
                "source_sites": [{"url": site.url, "title": site.title, "similarity_score": site.similarity_score} for site in search_response.source_sites]
            }
            
        except Exception as e:
            logger.error(f"Error with SerpAPI search: {str(e)}")
            return {
                "generated_response": f"Error generating information for {peptide_name}: {str(e)}",
                "similarity_score": 0,
                "source_content": "",
                "source_sites": []
            }

    def create_session(self, peptide_name: str, requirements: str = "", user_id: str = None, db: Session = None) -> PeptideInfoSession:
        """Create a new peptide info session"""
        try:
            session = PeptideInfoSession(
                peptide_name=peptide_name,
                requirements=requirements,
                user_id=user_id,
                title=f"Peptide Info: {peptide_name}"
            )
            
            db.add(session)
            db.commit()
            db.refresh(session)
            
            logger.info(f"Created peptide info session: {session.session_id}")
            return session
            
        except Exception as e:
            logger.error(f"Error creating peptide info session: {str(e)}")
            db.rollback()
            raise

    def add_message(self, session_id: str, role: str, content: str, query: str = None, 
                   response: str = None, source: str = None, accuracy_score: float = None,
                   source_content: str = None, source_urls: List[str] = None, 
                   meta: Dict[str, Any] = None, db: Session = None) -> PeptideInfoMessage:
        """Add a message to a peptide info session"""
        try:
            message = PeptideInfoMessage(
                session_id=session_id,
                role=role,
                content=content,
                query=query,
                response=response,
                source=source,
                accuracy_score=accuracy_score,
                source_content=source_content,
                source_urls=source_urls or [],
                meta=meta or {}
            )
            
            db.add(message)
            db.commit()
            db.refresh(message)
            
            logger.info(f"Added message to peptide info session: {session_id}")
            return message
            
        except Exception as e:
            logger.error(f"Error adding message to peptide info session: {str(e)}")
            db.rollback()
            raise

    def get_session(self, session_id: str, db: Session) -> Optional[PeptideInfoSession]:
        """Get a peptide info session by ID"""
        try:
            return db.query(PeptideInfoSession).filter(PeptideInfoSession.session_id == session_id).first()
        except Exception as e:
            logger.error(f"Error getting peptide info session: {str(e)}")
            return None

    def get_or_create_session(self, peptide_name: str, requirements: str = "", 
                            user_id: str = None, session_id: str = None, db: Session = None) -> PeptideInfoSession:
        """Get existing session or create new one"""
        try:
            if session_id:
                session = self.get_session(session_id, db)
                if session:
                    return session
            
            # Create new session
            return self.create_session(peptide_name, requirements, user_id, db)
            
        except Exception as e:
            logger.error(f"Error getting or creating peptide info session: {str(e)}")
            raise
