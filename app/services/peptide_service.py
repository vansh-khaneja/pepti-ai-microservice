import requests
import logging
import hashlib
from typing import List, Dict, Any
from app.models.peptide import PeptideCreate, PeptidePayload, PeptideChemicalInfo
from app.services.chat_restriction_service import ChatRestrictionService
from app.core.config import settings
from app.core.database import get_db
from app.utils.helpers import logger, ExternalApiTimer
from app.providers.provider_manager import provider_manager
from app.repositories import repository_manager

class PeptideService:
    def __init__(self):
        """Initialize peptide service with repository pattern"""
        pass

    def create_peptide(self, peptide_data: PeptideCreate) -> Dict[str, Any]:
        """Create a new peptide entry using vector store repository"""
        try:
            logger.info(f"Creating peptide: {peptide_data.name}")
            
            # Convert to payload model
            peptide_payload = PeptidePayload(
                name=peptide_data.name,
                overview=peptide_data.overview,
                mechanism_of_actions=peptide_data.mechanism_of_actions,
                potential_research_fields=peptide_data.potential_research_fields
            )
            
            # Generate embedding for the peptide text
            embedding = self._generate_embedding(peptide_payload.to_text())
            
            # Store using vector store repository
            vector_repo = repository_manager.vector_store
            entity = {
                "name": peptide_payload.name,
                "overview": peptide_payload.overview,
                "mechanism_of_actions": peptide_payload.mechanism_of_actions,
                "potential_research_fields": peptide_payload.potential_research_fields,
                "created_at": peptide_payload.created_at.isoformat(),
                "text_content": peptide_payload.to_text(),
                "vector": embedding
            }
            
            result = vector_repo.create(entity)
            point_id = result["id"]
            
            logger.info(f"Peptide '{peptide_data.name}' created successfully with ID: {point_id}")
            
            return {
                "name": peptide_data.name,
                "message": "Peptide stored successfully in vector database"
            }
            
        except Exception as e:
            logger.error(f"Error creating peptide: {str(e)}")
            raise

    def update_peptide(self, original_name: str, peptide_data: PeptideCreate) -> Dict[str, Any]:
        """Update an existing peptide using vector store repository"""
        try:
            logger.info(f"Updating peptide '{original_name}' -> '{peptide_data.name}'")

            vector_repo = repository_manager.vector_store
            
            # Delete old entry if it exists
            try:
                deleted = vector_repo.delete_by_name(original_name)
                if deleted:
                    logger.info(f"Deleted old peptide entry: {original_name}")
                else:
                    logger.warning(f"Old peptide '{original_name}' not found; proceeding to create new entry")
            except Exception as e:
                logger.warning(f"Delete during update failed for '{original_name}': {str(e)}")

            # Create payload from updated data
            peptide_payload = PeptidePayload(
                name=peptide_data.name,
                overview=peptide_data.overview,
                mechanism_of_actions=peptide_data.mechanism_of_actions,
                potential_research_fields=peptide_data.potential_research_fields
            )

            # Generate fresh embedding and store
            embedding = self._generate_embedding(peptide_payload.to_text())
            entity = {
                "name": peptide_payload.name,
                "overview": peptide_payload.overview,
                "mechanism_of_actions": peptide_payload.mechanism_of_actions,
                "potential_research_fields": peptide_payload.potential_research_fields,
                "created_at": peptide_payload.created_at.isoformat(),
                "text_content": peptide_payload.to_text(),
                "vector": embedding
            }
            
            result = vector_repo.create(entity)
            point_id = result["id"]

            logger.info(f"Peptide updated. New name='{peptide_data.name}', point_id='{point_id}'")
            return {
                "name": peptide_data.name,
                "message": "Peptide updated successfully in vector database"
            }
        except Exception as e:
            logger.error(f"Error updating peptide '{original_name}': {str(e)}")
            raise

    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using OpenAI API via provider, with caching"""
        try:
            cache_repo = None
            embedding_cache_key = None
            
            # Check cache for embedding first (only if cache is available)
            try:
                cache_repo = repository_manager.cache
                if cache_repo and cache_repo.redis_client:
                    normalized_text = text.lower().strip()
                    embedding_cache_key = f"embedding:{hashlib.md5(normalized_text.encode()).hexdigest()}"
                    
                    cached_data = cache_repo.get_by_id(embedding_cache_key)
                    if cached_data:
                        embedding = cached_data.get("embedding") or cached_data.get("data", {}).get("embedding")
                        if embedding:
                            logger.debug(f"Embedding cache HIT for text length: {len(text)}")
                            return embedding
            except Exception as cache_error:
                logger.debug(f"Embedding cache check failed (non-critical): {str(cache_error)}")
            
            # Generate new embedding
            logger.debug(f"Embedding cache MISS, generating new embedding for text length: {len(text)}")
            embedding = provider_manager.openai.generate_embedding(text)
            
            # Cache the embedding (longer TTL since embeddings don't change)
            if cache_repo and embedding_cache_key:
                try:
                    if cache_repo.redis_client:
                        cache_repo.create({
                            "key": embedding_cache_key,
                            "data": {"embedding": embedding, "text_length": len(text)},
                            "ttl": 86400 * 7  # Cache for 7 days
                        })
                except Exception as cache_error:
                    logger.debug(f"Embedding cache write failed (non-critical): {str(cache_error)}")
            
            return embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise

    def _generate_llm_response(self, peptide_data: Dict[str, Any], user_query: str, peptide_name: str) -> str:
        """Generate LLM response using embedding_text from payload"""
        try:
            # Get embedding_text from payload, fallback to text_content if not available
            embedding_text = peptide_data.get("embedding_text")
            text_content = peptide_data.get("text_content")
            
            if embedding_text:
                context = embedding_text
                context_source = "embedding_text"
                logger.debug(f"Using embedding_text for LLM context (length: {len(context)})")
            elif text_content:
                context = text_content
                context_source = "text_content"
                logger.debug(f"Using text_content for LLM context (length: {len(context)})")
            else:
                context = ""
                context_source = "empty"
                logger.warning(f"No embedding_text or text_content found in payload for {peptide_name}. Available keys: {list(peptide_data.keys())}")
            
            logger.info(f"Generating LLM response for peptide '{peptide_name}' using context source: {context_source}, context length: {len(context)}")
            
            # Get chat restrictions
            restrictions_text = self._get_chat_restrictions()
            has_restrictions = bool(restrictions_text)
            logger.debug(f"Chat restrictions {'found' if has_restrictions else 'not found'}")
            
            # Short and crisp prompt
            system_prompt = f"""You are a peptide research assistant. Answer based on the provided context. Keep responses short, clear, and under 1000 characters. Plain text only, no markdown.{restrictions_text}"""
            
            # Simple format: query and context
            user_prompt = f"""Query: {user_query}

Context:
{context}

Provide a concise answer based on the context above."""
            
            # Combine system and user prompts for Responses API
            full_input = f"{system_prompt}\n\n{user_prompt}"
            total_input_length = len(full_input)
            logger.debug(f"LLM input length: {total_input_length} characters")
            
            response = provider_manager.openai.generate_response(
                input_text=full_input,
                model="gpt-4o",
                temperature=0.3,
                max_output_tokens=400
            )
            
            logger.debug(f"Raw LLM response length: {len(response)} characters")
            
            # Clean up the response to ensure it's plain text and under 1000 characters
            cleaned_response = self._clean_llm_response(response)
            final_length = len(cleaned_response)
            logger.info(f"Generated LLM response successfully for peptide: {peptide_name}, final length: {final_length} chars, context source: {context_source}")
            return cleaned_response
                
        except Exception as e:
            logger.error(f"Error generating LLM response for peptide '{peptide_name}': {str(e)}", exc_info=True)
            raise

    def _clean_llm_response(self, response: str) -> str:
        """Clean LLM response to ensure plain text format and character limit"""
        # Remove markdown formatting
        import re
        
        # Remove markdown headers, bold, italic, code blocks, etc.
        cleaned = re.sub(r'#+\s*', '', response)  # Remove headers
        cleaned = re.sub(r'\*\*(.*?)\*\*', r'\1', cleaned)  # Remove bold
        cleaned = re.sub(r'\*(.*?)\*', r'\1', cleaned)  # Remove italic
        cleaned = re.sub(r'`(.*?)`', r'\1', cleaned)  # Remove inline code
        cleaned = re.sub(r'```.*?```', '', cleaned, flags=re.DOTALL)  # Remove code blocks
        cleaned = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', cleaned)  # Remove links, keep text
        
        # Clean up extra whitespace and ensure proper paragraph formatting
        cleaned = re.sub(r'\n\s*\n', '\n\n', cleaned)  # Normalize paragraph breaks
        cleaned = cleaned.strip()
        
        # Ensure it's under 1000 characters
        if len(cleaned) > 1000:
            # Truncate at word boundary
            truncated = cleaned[:997] + "..."
            # Find last complete word
            last_space = truncated.rfind(' ')
            if last_space > 900:  # If we can find a good break point
                truncated = truncated[:last_space] + "..."
            cleaned = truncated
        
        return cleaned


    def query_peptide(self, peptide_name: str, user_query: str) -> Dict[str, Any]:
        """Query a peptide using LLM with the peptide data as context, with LLM judge and Tavily fallback"""
        try:
            logger.info(f"Querying peptide: '{peptide_name}' with question: '{user_query[:100]}...' (query length: {len(user_query)})")
            
            # Get peptide data from vector store repository
            vector_repo = repository_manager.vector_store
            logger.debug(f"Fetching peptide data from Qdrant for: {peptide_name}")
            peptide_data = vector_repo.get_by_name(peptide_name)
            
            if not peptide_data:
                # Peptide not found in DB; use Tavily fallback
                logger.warning(f"Peptide '{peptide_name}' not found in Qdrant database; invoking Tavily fallback")
                tavily_content, tavily_score = self._tavily_fetch_content(f"{peptide_name} {user_query}")
                logger.info(f"Tavily search returned {len(tavily_content)} content chunks with score: {tavily_score}")
                answer = self._generate_final_answer_from_content(user_query, tavily_content, peptide_name_hint=peptide_name)
                return {
                    "llm_response": answer,
                    "peptide_name": peptide_name,
                    "similarity_score": tavily_score,
                    "peptide_context": "\n\n".join(tavily_content) if tavily_content else None,
                    "source": "tavily"
                }
            
            available_keys = list(peptide_data.keys())
            logger.debug(f"Peptide data retrieved. Available keys: {available_keys}")
            
            # Extract context for judge (embedding_text, text_content, or construct from fields)
            embedding_text = peptide_data.get("embedding_text")
            text_content_field = peptide_data.get("text_content")
            
            if embedding_text:
                text_content = embedding_text
                context_source = "embedding_text"
                logger.debug(f"Using embedding_text for judge (length: {len(text_content)})")
            elif text_content_field:
                text_content = text_content_field
                context_source = "text_content"
                logger.debug(f"Using text_content for judge (length: {len(text_content)})")
            else:
                # Construct from individual fields
                overview = peptide_data.get('overview', '')
                mechanism = peptide_data.get('mechanism_of_actions', '')
                research_fields = peptide_data.get('potential_research_fields', '')
                text_content = f"name: {peptide_name} overview: {overview} mechanism of actions: {mechanism} potential research fields: {research_fields}"
                context_source = "constructed_from_fields"
                logger.warning(f"No embedding_text or text_content found. Constructed context from individual fields. Available keys: {list(peptide_data.keys())}")
            
            logger.info(f"Querying peptide '{peptide_name}': user_query='{user_query[:100]}...', context_source={context_source}, context_length={len(text_content)}")
            
            # Always use LLM judge for peptide-specific queries to ensure relevance
            logger.info(f"Invoking LLM judge for peptide-specific query: {peptide_name}")
            judge_yes = self._judge_relevance_yes_no(user_query, text_content, peptide_name)
            
            if judge_yes:
                logger.info(f"Judge said YES for '{peptide_name}'; using stored peptide context from {context_source}")
                llm_response = self._generate_llm_response(peptide_data, user_query, peptide_name)
                return {
                    "llm_response": llm_response,
                    "peptide_name": peptide_name,
                    "similarity_score": None,
                    "peptide_context": text_content,
                    "source": "qdrant+judge"
                }
            else:
                logger.info(f"Judge said NO for '{peptide_name}'; falling back to Tavily search")
                tavily_content, tavily_score = self._tavily_fetch_content(f"{peptide_name} {user_query}")
                logger.info(f"Tavily search returned {len(tavily_content)} content chunks with score: {tavily_score}")
                answer = self._generate_final_answer_from_content(user_query, tavily_content, peptide_name_hint=peptide_name)
                return {
                    "llm_response": answer,
                    "peptide_name": peptide_name,
                    "similarity_score": tavily_score,
                    "peptide_context": "\n\n".join(tavily_content) if tavily_content else None,
                    "source": "tavily"
                }
            
        except Exception as e:
            logger.error(f"Error querying peptide: {str(e)}")
            raise

    def delete_peptide(self, peptide_name: str) -> bool:
        """Delete a peptide by name using vector store repository"""
        try:
            logger.info(f"Deleting peptide: {peptide_name}")
            vector_repo = repository_manager.vector_store
            success = vector_repo.delete_by_name(peptide_name)
            
            if success:
                logger.info(f"Peptide {peptide_name} deleted successfully")
            else:
                logger.warning(f"Peptide {peptide_name} not found or already deleted")
            
            return success
            
        except Exception as e:
            logger.error(f"Error deleting peptide: {str(e)}")
            raise

    def search_and_answer(self, query: str) -> Dict[str, Any]:
        """Search for peptides using vector similarity and answer queries with LLM-judge and Tavily fallback"""
        try:
            logger.info(f"Starting search_and_answer for query: '{query[:100]}...' (length: {len(query)})")
            
            # Generate embedding for the search query
            logger.debug("Generating embedding for search query")
            query_embedding = self._generate_embedding(query)
            logger.debug(f"Generated embedding with {len(query_embedding)} dimensions")
            
            # Search for the most similar peptide using vector store repository
            vector_repo = repository_manager.vector_store
            logger.debug("Searching Qdrant for similar peptides")
            search_result = vector_repo.search_similar(query_embedding, limit=1)
            logger.info(f"Qdrant search returned {len(search_result)} result(s)")
            
            if not search_result:
                # No candidates; go directly to Tavily fallback path
                logger.warning("No peptides found in Qdrant; invoking Tavily fallback")
                tavily_content, tavily_score = self._tavily_fetch_content(query)
                logger.info(f"Tavily search returned {len(tavily_content)} content chunks with score: {tavily_score}")
                answer = self._generate_final_answer_from_content(query, tavily_content, peptide_name_hint=None)
                return {
                    "llm_response": answer,
                    "peptide_name": None,
                    "similarity_score": tavily_score,
                    "peptide_context": "\n\n".join(tavily_content) if tavily_content else None,
                    "source": "tavily"
                }
            
            # Get the best match
            best_match = search_result[0]
            peptide_name = best_match.get("name", "Unknown")
            similarity_score = best_match.get("score")
            available_keys = list(best_match.keys())
            logger.info(f"Best match found: peptide_name='{peptide_name}', similarity_score={similarity_score}, available_keys={available_keys}")
            
            # Get context for judge and return value (embedding_text, text_content, or construct from fields)
            embedding_text = best_match.get("embedding_text")
            text_content_field = best_match.get("text_content")
            
            if embedding_text:
                peptide_context = embedding_text
                context_source = "embedding_text"
                logger.debug(f"Using embedding_text for context (length: {len(peptide_context)})")
            elif text_content_field:
                peptide_context = text_content_field
                context_source = "text_content"
                logger.debug(f"Using text_content for context (length: {len(peptide_context)})")
            else:
                # Construct from individual fields
                overview = best_match.get('overview', '')
                mechanism = best_match.get('mechanism_of_actions', '')
                research_fields = best_match.get('potential_research_fields', '')
                peptide_context = f"name: {peptide_name} overview: {overview} mechanism of actions: {mechanism} potential research fields: {research_fields}"
                context_source = "constructed_from_fields"
                logger.warning(f"No embedding_text or text_content in payload. Constructed from fields. Available keys: {available_keys}")
            
            logger.info(f"Context source: {context_source}, context length: {len(peptide_context)}")

            # If below similarity threshold, ask LLM judge if the context is relevant
            from app.core.config import settings
            threshold = settings.MIN_VECTOR_SIMILARITY
            high_confidence_threshold = 0.7  # Skip judge for very high similarity
            logger.debug(f"Similarity threshold: {threshold}, high confidence: {high_confidence_threshold}, current score: {similarity_score}")
            
            # Skip judge for very high similarity scores (fast path)
            if similarity_score is not None and similarity_score >= high_confidence_threshold:
                logger.info(f"High similarity {similarity_score} >= {high_confidence_threshold}; skipping judge, using Qdrant context directly")
                llm_response = self._generate_llm_response(best_match, query, peptide_name)
                return {
                    "llm_response": llm_response,
                    "peptide_name": peptide_name,
                    "similarity_score": round(similarity_score, 6),
                    "peptide_context": peptide_context,
                    "source": "qdrant"
                }
            
            if similarity_score is None or similarity_score < threshold:
                logger.info(f"Similarity {similarity_score} < threshold {threshold}; invoking LLM judge")
                judge_yes = self._judge_relevance_yes_no(query, peptide_context, peptide_name)
                logger.info(f"LLM judge result: {'YES' if judge_yes else 'NO'}")
                
                if judge_yes:
                    logger.info(f"Judge said YES; using Qdrant context from {context_source}")
                    llm_response = self._generate_llm_response(best_match, query, peptide_name)
                    return {
                        "llm_response": llm_response,
                        "peptide_name": peptide_name,
                        "similarity_score": round(similarity_score, 6) if similarity_score is not None else None,
                        "peptide_context": peptide_context,
                        "source": "qdrant+judge"
                    }
                else:
                    logger.info(f"Judge said NO; falling back to Tavily search for '{peptide_name}'")
                    tavily_content, tavily_score = self._tavily_fetch_content(query)
                    logger.info(f"Tavily search returned {len(tavily_content)} content chunks with score: {tavily_score}")
                    answer = self._generate_final_answer_from_content(query, tavily_content, peptide_name_hint=peptide_name)
                    return {
                        "llm_response": answer,
                        "peptide_name": peptide_name,
                        "similarity_score": tavily_score,
                        "peptide_context": "\n\n".join(tavily_content) if tavily_content else None,
                        "source": "tavily"
                    }

            # Above threshold: use Qdrant context directly
            logger.info(f"Similarity {similarity_score} >= threshold {threshold}; using Qdrant context directly from {context_source}")
            llm_response = self._generate_llm_response(best_match, query, peptide_name)
            logger.info(f"Search completed successfully for '{peptide_name}' with source: qdrant")
            return {
                "llm_response": llm_response,
                "peptide_name": peptide_name,
                "similarity_score": round(similarity_score, 6),
                "peptide_context": peptide_context,
                "source": "qdrant"
            }
            
        except Exception as e:
            logger.error(f"Error searching and answering for query '{query}': {str(e)}", exc_info=True)
            raise

    def _get_chat_restrictions(self) -> str:
        """Get all chat restrictions and format them for LLM prompts"""
        try:
            # Get database session
            from app.core.database import SessionLocal
            db = SessionLocal()
            
            try:
                # Get chat restrictions service
                restriction_service = ChatRestrictionService(db)
                restrictions = restriction_service.get_all_chat_restrictions()
                
                if not restrictions:
                    return ""
                
                # Format restrictions for LLM prompt
                restrictions_text = "\n".join([f"- {restriction.restriction_text}" for restriction in restrictions])
                return f"\n\nIMPORTANT RESTRICTIONS TO FOLLOW:\n{restrictions_text}\n\nYou MUST follow these restrictions while answering."
                
            finally:
                db.close()
                
        except Exception as e:
            logger.warning(f"Could not fetch chat restrictions: {str(e)}")
            return ""

    def _judge_relevance_yes_no(self, user_query: str, candidate_content: str, peptide_name: str | None) -> bool:
        """Ask LLM to judge if candidate_content is relevant to user_query; expect 'Yes' or 'No'"""
        try:
            logger.debug(f"Judging relevance: query='{user_query[:100]}...', peptide='{peptide_name}', content_length={len(candidate_content)}")
            result = provider_manager.openai.judge_relevance(user_query, candidate_content, peptide_name)
            logger.debug(f"Judge relevance result: {result} for peptide '{peptide_name}'")
            return result
        except Exception as e:
            logger.warning(f"Judge relevance failed for peptide '{peptide_name}': {str(e)}", exc_info=True)
            return False

    def _tavily_fetch_content(self, query: str) -> tuple[List[str], float]:
        """Fetch content snippets via Tavily search and return content + average score"""
        try:
            logger.debug(f"Starting Tavily search for query: '{query[:100]}...'")
            from app.core.config import settings
            api_key = settings.TAVILY_API_KEY
            if not api_key:
                logger.warning("TAVILY_API_KEY not configured; returning empty content list")
                return [], 0.0

            try:
                from tavily import TavilyClient
            except Exception as e:
                logger.warning(f"Tavily import failed: {str(e)}")
                return [], 0.0

            client = TavilyClient(api_key=api_key)
            logger.debug("Tavily client initialized, performing search")
            
            with ExternalApiTimer("tavily", operation="search", metadata={
                "query": query, 
                "max_results": 5,
                "search_depth": "advanced",
                "search_type": "advanced_search"
            }) as t:
                result = client.search(
                    query=query,
                    search_depth="advanced",
                    include_answer=True,
                    include_images=False,
                    max_results=5
                )
                t.set_status(status_code=200, success=True)

            contents: List[str] = []
            scores = self._extract_tavily_scores(result)
            average_score = sum(scores) / len(scores) if scores else 0.0
            logger.debug(f"Tavily search completed: extracted {len(scores)} scores, average: {average_score}")
            
            if isinstance(result, dict) and "results" in result and isinstance(result["results"], list):
                for item in result["results"]:
                    if isinstance(item, dict) and "content" in item:
                        contents.append(item["content"])
            
            logger.info(f"Tavily search returned {len(contents)} content chunks with average score: {average_score:.4f}")
            return contents, average_score
        except Exception as e:
            logger.warning(f"Tavily search failed for query '{query}': {str(e)}", exc_info=True)
            return [], 0.0

    def _extract_tavily_scores(self, response: dict) -> List[float]:
        """Extract scores from Tavily API response"""
        scores = []
        if "results" in response and isinstance(response["results"], list):
            for item in response["results"]:
                if isinstance(item, dict) and "score" in item:
                    try:
                        score = float(item["score"])
                        scores.append(score)
                    except (ValueError, TypeError):
                        continue
        return scores

    def _generate_final_answer_from_content(self, user_query: str, contents: List[str], peptide_name_hint: str | None) -> str:
        """Synthesize a final answer from external contents using LLM"""
        try:
            joined = "\n\n".join(contents[:5]) if contents else ""
            name_hint = peptide_name_hint or "the peptide"
            logger.debug(f"Generating final answer from {len(contents)} content chunks for '{name_hint}', query length: {len(user_query)}")
            
            restrictions_text = self._get_chat_restrictions()
            system_prompt = (
                "You are a helpful assistant specializing in peptide research. "
                "Use only the provided content to answer the user's question succinctly. "
                "If insufficient, be honest."
            ) + f"\n{restrictions_text}"

            user_prompt = (
                f"Context about {name_hint}:\n{joined}\n\n"
                f"User Question: {user_query}\n"
                "Answer in plain text, under 1000 characters."
            )

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            logger.debug(f"Calling LLM with {len(contents)} content chunks, total context length: {len(joined)}")
            response = provider_manager.openai.generate_chat_completion(
                messages=messages,
                model="gpt-4o",
                temperature=0.3,
                max_tokens=400,
                timeout=45
            )
            
            cleaned = self._clean_llm_response(response)
            logger.info(f"Generated final answer from external content: length={len(cleaned)} chars for '{name_hint}'")
            return cleaned
            
        except Exception as e:
            logger.warning(f"Generate final answer failed for '{peptide_name_hint}': {str(e)}", exc_info=True)
            return "I could not generate an answer at this time."

    def get_peptide_chemical_info(self, peptide_name: str) -> PeptideChemicalInfo:
        """Get chemical information for a peptide using the per-field generator (no function calls)."""
        try:
            seq = self.generate_chemical_field(peptide_name, "sequence") or None
            chem = self.generate_chemical_field(peptide_name, "chemical_formula") or None
            mass = self.generate_chemical_field(peptide_name, "molecular_mass") or None
            iupac = self.generate_chemical_field(peptide_name, "iupac_name") or None
            return PeptideChemicalInfo(
                peptide_name=peptide_name,
                sequence=seq,
                chemical_formula=chem,
                molecular_mass=mass,
                iupac_name=iupac
            )
        except Exception as e:
            logger.error(f"Error getting chemical information for {peptide_name}: {str(e)}")
            raise

    def generate_chemical_field(self, peptide_name: str, field: str) -> str | None:
        """Generate exactly one requested chemical field using LLM only.

        field ∈ {sequence, chemical_formula, molecular_mass, iupac_name}
        Returns a plain string or None. The prompt enforces returning ONLY the requested field.
        """
        try:
            return provider_manager.openai.generate_chemical_field(peptide_name, field)
        except Exception as e:
            logger.error(f"Unhandled error generating chemical field '{field}' for '{peptide_name}': {str(e)}")
            return ""

    # Note: No regex parsing/validation; we return only what the LLM provides or empty fields

    def find_similar_peptides(self, peptide_name: str, top_k: int = 4) -> List[Dict[str, Any]]:
        """Find similar peptides based on vector similarity using vector store repository"""
        try:
            logger.info(f"Finding similar peptides for: {peptide_name}")
            
            # First, get the target peptide to extract its embeddings
            vector_repo = repository_manager.vector_store
            target_peptide = vector_repo.get_by_name(peptide_name)
            
            if not target_peptide:
                raise ValueError(f"Peptide '{peptide_name}' not found")
            
            # Get the target peptide's embeddings
            target_embedding = target_peptide["vector"]
            
            # Search for similar peptides using the target's embeddings
            similar_results = vector_repo.search_similar(target_embedding, limit=top_k + 1)
            
            # Filter out the target peptide itself and format results
            similar_peptides = []
            for result in similar_results:
                result_name = result["name"]
                if result_name != peptide_name:  # Exclude the target peptide
                    similar_peptides.append({
                        "name": result_name,
                        "overview": result["overview"],
                        "similarity_score": round(result["score"], 6)
                    })
                    
                    # Stop when we have enough results
                    if len(similar_peptides) >= top_k:
                        break
            
            logger.info(f"Found {len(similar_peptides)} similar peptides for {peptide_name}")
            return similar_peptides
            
        except Exception as e:
            logger.error(f"Error finding similar peptides: {str(e)}")
            raise



