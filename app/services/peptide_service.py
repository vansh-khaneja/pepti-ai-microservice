import requests
import logging
from typing import List, Dict, Any
from app.models.peptide import PeptideCreate, PeptidePayload, PeptideChemicalInfo
from app.services.qdrant_service import QdrantService
from app.services.chat_restriction_service import ChatRestrictionService
from app.core.config import settings
from app.core.database import get_db
from app.utils.helpers import logger

class PeptideService:
    def __init__(self):
        """Initialize peptide service with lazy Qdrant usage for OpenAI-only endpoints"""
        self.qdrant_service: QdrantService | None = None
        self.openai_api_key = settings.OPENAI_API_KEY

    def create_peptide(self, peptide_data: PeptideCreate) -> Dict[str, Any]:
        """Create a new peptide entry in Qdrant"""
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
            
            # Ensure Qdrant and store
            self._ensure_qdrant()
            point_id = self.qdrant_service.store_peptide(peptide_payload, embedding)  # type: ignore[attr-defined]
            
            logger.info(f"Peptide '{peptide_data.name}' created successfully with ID: {point_id}")
            
            return {
                "name": peptide_data.name,
                "message": "Peptide stored successfully in vector database"
            }
            
        except Exception as e:
            logger.error(f"Error creating peptide: {str(e)}")
            raise

    def update_peptide(self, original_name: str, peptide_data: PeptideCreate) -> Dict[str, Any]:
        """Update an existing peptide by deleting old entry and creating a new one.

        We delete the peptide by its original name from Qdrant, then insert a new
        entry using the provided `peptide_data` (which may include a new name and
        updated fields). Embedding is regenerated from updated text.
        """
        try:
            logger.info(f"Updating peptide '{original_name}' -> '{peptide_data.name}'")

            self._ensure_qdrant()
            # Delete old entry if it exists (ignore if not found)
            try:
                deleted = self.qdrant_service.delete_peptide(original_name)  # type: ignore[attr-defined]
                if deleted:
                    logger.info(f"Deleted old peptide entry: {original_name}")
                else:
                    logger.warning(f"Old peptide '{original_name}' not found; proceeding to create new entry")
            except Exception as e:
                # Don't fail the whole update on delete error; surface error
                logger.warning(f"Delete during update failed for '{original_name}': {str(e)}")
                # Continue to create the new entry regardless

            # Create payload from updated data
            peptide_payload = PeptidePayload(
                name=peptide_data.name,
                overview=peptide_data.overview,
                mechanism_of_actions=peptide_data.mechanism_of_actions,
                potential_research_fields=peptide_data.potential_research_fields
            )

            # Generate fresh embedding and store
            embedding = self._generate_embedding(peptide_payload.to_text())
            point_id = self.qdrant_service.store_peptide(peptide_payload, embedding)  # type: ignore[attr-defined]

            logger.info(f"Peptide updated. New name='{peptide_data.name}', point_id='{point_id}'")
            return {
                "name": peptide_data.name,
                "message": "Peptide updated successfully in vector database"
            }
        except Exception as e:
            logger.error(f"Error updating peptide '{original_name}': {str(e)}")
            raise

    def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using OpenAI API"""
        try:
            if not self.openai_api_key:
                raise ValueError("OpenAI API key not configured")
            
            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "input": text,
                "model": "text-embedding-3-large"
            }
            
            response = requests.post(
                "https://api.openai.com/v1/embeddings",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                embedding = data["data"][0]["embedding"]
                # Use full embedding size from model (expected 3072 for text-embedding-3-large)
                logger.info(f"Generated embedding successfully for text length {len(text)}, dimensions: {len(embedding)}")
                return embedding
            else:
                logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
                raise Exception(f"Failed to generate embedding: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise

    def _generate_llm_response(self, peptide_context: str, user_query: str, peptide_name: str) -> str:
        """Generate LLM response using peptide context"""
        try:
            if not self.openai_api_key:
                raise ValueError("OpenAI API key not configured")
            
            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }
            
            # Get chat restrictions
            restrictions_text = self._get_chat_restrictions()
            
            # Create a focused prompt for the specific peptide
            system_prompt = f"""You are a helpful assistant specializing in peptide research and information.
            
            CRITICAL INSTRUCTIONS:
            1. If the user asks basic greetings (hi, hello, how are you) or general questions NOT about peptides, answer simply and briefly without using any peptide context.
            
            2. If the user asks about a DIFFERENT peptide than {peptide_name}, respond with: "I don't have information about that specific peptide."
            
            3. If the user asks about {peptide_name} but the question is vague or unclear, ask them to be more specific about what they want to know (uses, mechanism, research fields, etc.).
            
            4. ONLY use the provided peptide information when the user asks SPECIFIC questions about {peptide_name}.
            
            5. Answer precisely and concisely. If asked about "uses", only mention uses. If asked about "mechanism", only mention mechanism.
            
            IMPORTANT FORMATTING REQUIREMENTS:
            - Write in plain text only, NO markdown formatting
            - Use normal paragraphs with proper spacing
            - Keep response under 1000 characters
            - Be direct and to the point
            
            {restrictions_text}"""
            
            user_prompt = f"""Peptide Information for {peptide_name}:
            {peptide_context}
            
            User Question: {user_query}
            
            Please provide a clear, accurate answer based on the peptide information above.
            Remember: plain text only, no markdown, under 1000 characters, normal paragraphs."""
            
            # Combine system and user prompts for Responses API
            full_input = f"{system_prompt}\n\n{user_prompt}"
            
            payload = {
                "model": "gpt-4o",
                "input": full_input,
                "temperature": 0.3,
                "max_output_tokens": 400  # Reduced to ensure under 1000 characters
            }
            
            response = requests.post(
                "https://api.openai.com/v1/responses",
                headers=headers,
                json=payload,
                timeout=45
            )
            
            if response.status_code == 200:
                data = response.json()
                # Parse Responses API response format
                if data.get("status") == "completed" and "output" in data:
                    # Extract text from the output array
                    output_text = ""
                    for output_item in data["output"]:
                        if output_item.get("type") == "message" and "content" in output_item:
                            for content_item in output_item["content"]:
                                if content_item.get("type") == "output_text" and "text" in content_item:
                                    output_text += content_item["text"]
                    
                    if output_text.strip():
                        # Clean up the response to ensure it's plain text and under 1000 characters
                        cleaned_response = self._clean_llm_response(output_text.strip())
                        logger.info(f"Generated LLM response successfully for peptide: {peptide_name}")
                        return cleaned_response
                    else:
                        logger.error("No text found in Responses API output")
                        raise Exception("No response generated from Responses API")
                else:
                    logger.error(f"OpenAI Responses API returned unexpected status: {data.get('status')}")
                    raise Exception(f"Unexpected response status: {data.get('status')}")
            else:
                logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
                raise Exception(f"Failed to generate LLM response: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error generating LLM response: {str(e)}")
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

    def _ensure_qdrant(self) -> None:
        """Lazily initialize Qdrant service and ensure index once."""
        if self.qdrant_service is None:
            try:
                # QdrantService.__init__ already ensures collection and (once per process) name index as needed.
                self.qdrant_service = QdrantService()
            except Exception as e:
                logger.error(f"Failed to initialize Qdrant service: {str(e)}")
                raise

    def query_peptide(self, peptide_name: str, user_query: str) -> Dict[str, Any]:
        """Query a peptide using LLM with the peptide data as context, with LLM judge and Tavily fallback"""
        try:
            logger.info(f"Querying peptide: {peptide_name} with question: {user_query}")
            
            # Get peptide data from Qdrant
            self._ensure_qdrant()
            peptide_data = self.qdrant_service.get_peptide_by_name(peptide_name)  # type: ignore[attr-defined]
            
            if not peptide_data:
                # Peptide not found in DB; use Tavily fallback
                logger.warning(f"Peptide '{peptide_name}' not found in database; invoking Tavily fallback")
                tavily_content, tavily_score = self._tavily_fetch_content(f"{peptide_name} {user_query}")
                answer = self._generate_final_answer_from_content(user_query, tavily_content, peptide_name_hint=peptide_name)
                return {
                    "llm_response": answer,
                    "peptide_name": peptide_name,
                    "similarity_score": tavily_score,
                    "peptide_context": "\n\n".join(tavily_content) if tavily_content else None,
                    "source": "tavily"
                }
            
            # Extract the text content for LLM context
            text_content = peptide_data["payload"]["text_content"]
            
            # Always use LLM judge for peptide-specific queries to ensure relevance
            logger.info(f"Invoking LLM judge for peptide-specific query: {peptide_name}")
            judge_yes = self._judge_relevance_yes_no(user_query, text_content, peptide_name)
            
            if judge_yes:
                logger.info("Judge said YES; using stored peptide context")
                llm_response = self._generate_llm_response(text_content, user_query, peptide_name)
                return {
                    "llm_response": llm_response,
                    "peptide_name": peptide_name,
                    "similarity_score": None,
                    "peptide_context": text_content,
                    "source": "qdrant+judge"
                }
            else:
                logger.info("Judge said NO; falling back to Tavily search")
                tavily_content, tavily_score = self._tavily_fetch_content(f"{peptide_name} {user_query}")
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
        """Delete a peptide by name"""
        try:
            logger.info(f"Deleting peptide: {peptide_name}")
            # Ensure Qdrant client is initialized before deletion
            self._ensure_qdrant()
            success = self.qdrant_service.delete_peptide(peptide_name)
            
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
            logger.info(f"Searching peptides with query: {query}")
            
            # Generate embedding for the search query
            query_embedding = self._generate_embedding(query)
            
            # Search for the most similar peptide in Qdrant
            self._ensure_qdrant()
            search_result = self.qdrant_service.search_peptides(query_embedding, limit=1)  # type: ignore[attr-defined]
            
            if not search_result:
                # No candidates; go directly to Tavily fallback path
                logger.warning("No peptides found; invoking Tavily fallback")
                tavily_content, tavily_score = self._tavily_fetch_content(query)
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
            peptide_name = best_match["payload"]["name"]
            similarity_score = best_match["score"]
            peptide_context = best_match["payload"]["text_content"]
            
            logger.info(f"Found best matching peptide: {peptide_name} with score: {similarity_score}")

            # If below similarity threshold, ask LLM judge if the context is relevant
            from app.core.config import settings
            threshold = settings.MIN_VECTOR_SIMILARITY
            if similarity_score is None or similarity_score < threshold:
                logger.info(f"Similarity {similarity_score} < threshold {threshold}; invoking LLM judge")
                judge_yes = self._judge_relevance_yes_no(query, peptide_context, peptide_name)
                if judge_yes:
                    logger.info("Judge said YES; using current context")
                    llm_response = self._generate_llm_response(peptide_context, query, peptide_name)
                    return {
                        "llm_response": llm_response,
                        "peptide_name": peptide_name,
                        "similarity_score": round(similarity_score, 6) if similarity_score is not None else None,
                        "peptide_context": peptide_context,
                        "source": "qdrant+judge"
                    }
                else:
                    logger.info("Judge said NO; falling back to Tavily search")
                    tavily_content, tavily_score = self._tavily_fetch_content(query)
                    answer = self._generate_final_answer_from_content(query, tavily_content, peptide_name_hint=peptide_name)
                    return {
                        "llm_response": answer,
                        "peptide_name": peptide_name,
                        "similarity_score": tavily_score,
                        "peptide_context": "\n\n".join(tavily_content) if tavily_content else None,
                        "source": "tavily"
                    }

            # Above threshold: use Qdrant context directly
            llm_response = self._generate_llm_response(peptide_context, query, peptide_name)
            return {
                "llm_response": llm_response,
                "peptide_name": peptide_name,
                "similarity_score": round(similarity_score, 6),
                "peptide_context": peptide_context,
                "source": "qdrant"
            }
            
        except Exception as e:
            logger.error(f"Error searching and answering: {str(e)}")
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
                "model": "gpt-4o",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.0,
                "max_tokens": 2
            }

            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=20
            )
            if response.status_code == 200:
                data = response.json()
                text = ""
                try:
                    text = data["choices"][0]["message"]["content"].strip()
                except Exception:
                    pass
                normalized = text.lower()
                return normalized.startswith("yes")
            else:
                logger.warning(f"LLM judge API error: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.warning(f"Judge relevance failed: {str(e)}")
            return False

    def _tavily_fetch_content(self, query: str) -> tuple[List[str], float]:
        """Fetch content snippets via Tavily search and return content + average score"""
        try:
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
            result = client.search(
                query=query,
                search_depth="advanced",
                include_answer=True,
                include_images=False,
                max_results=5
            )

            contents: List[str] = []
            scores = self._extract_tavily_scores(result)
            average_score = sum(scores) / len(scores) if scores else 0.0
            
            if isinstance(result, dict) and "results" in result and isinstance(result["results"], list):
                for item in result["results"]:
                    if isinstance(item, dict) and "content" in item:
                        contents.append(item["content"])
            return contents, average_score
        except Exception as e:
            logger.warning(f"Tavily search failed: {str(e)}")
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
            if not self.openai_api_key:
                raise ValueError("OpenAI API key not configured")

            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }

            joined = "\n\n".join(contents[:5]) if contents else ""
            name_hint = peptide_name_hint or "the peptide"
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

            payload = {
                "model": "gpt-4o",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 400
            }

            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=45
            )
            if response.status_code == 200:
                data = response.json()
                try:
                    text = data["choices"][0]["message"]["content"].strip()
                    return self._clean_llm_response(text)
                except Exception:
                    return "I could not synthesize an answer from the available content."
            else:
                logger.warning(f"Final answer generation error: {response.status_code} - {response.text}")
                return "I could not generate an answer at this time."
        except Exception as e:
            logger.warning(f"Generate final answer failed: {str(e)}")
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
            if not self.openai_api_key:
                raise ValueError("OpenAI API key not configured")

            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }

            rules = (
                "You MUST return ONLY the value for the requested field in plain text."
                " No labels, no extra words, no units unless the field requires it,"
                " no punctuation beyond what is part of the value."
            )

            if field == "sequence":
                requirement = (
                    "Return ONLY the sequence for this entity."
                )
            elif field == "chemical_formula":
                requirement = (
                    "Return ONLY the chemical formula (e.g., C38H68N10O14)."
                )
            elif field == "molecular_mass":
                requirement = (
                    "Return ONLY the molecular mass with units 'g/mol' (e.g., 973.13 g/mol)."
                    
                )
            elif field == "iupac_name":
                requirement = (
                    "Return ONLY the IUPAC or systematic name."
                )
            else:
                raise ValueError("Unsupported field")

            system_prompt = (
                "You are a precise extractor for peptide chemical data. "
                + rules
            )
            user_prompt = (
                f"Peptide name: {peptide_name}\nRequested field: {field}\n"
                f"Instruction: {requirement}"
            )

            payload = {
                "model": "gpt-5-2025-08-07",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "max_completion_tokens": 120
            }

            # Log intent (debug level to avoid noise)
            logger.debug(f"Generating chemical field: field='{field}', peptide='{peptide_name}'")

            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                try:
                    text = data["choices"][0]["message"]["content"].strip()
                    if not text:
                        logger.warning(
                            f"OpenAI returned empty content for field='{field}', peptide='{peptide_name}'"
                        )
                    return text
                except Exception as parse_err:
                    logger.warning(
                        f"Failed to parse OpenAI response for field='{field}', peptide='{peptide_name}': {parse_err}. Raw: {data}"
                    )
                    return ""
            else:
                try:
                    body = response.text
                except Exception:
                    body = "<no-body>"
                logger.error(
                    f"OpenAI API error while generating field='{field}', peptide='{peptide_name}': "
                    f"status={response.status_code}, body={body}"
                )
                return ""
        except Exception as e:
            logger.error(
                f"Unhandled error generating chemical field '{field}' for '{peptide_name}': {str(e)}",
                exc_info=True
            )
            return ""

    # Note: No regex parsing/validation; we return only what the LLM provides or empty fields

    def find_similar_peptides(self, peptide_name: str, top_k: int = 4) -> List[Dict[str, Any]]:
        """Find similar peptides based on vector similarity"""
        try:
            logger.info(f"Finding similar peptides for: {peptide_name}")
            
            # First, get the target peptide to extract its embeddings
            self._ensure_qdrant()
            target_peptide = self.qdrant_service.get_peptide_by_name(peptide_name)  # type: ignore[attr-defined]
            
            if not target_peptide:
                raise ValueError(f"Peptide '{peptide_name}' not found")
            
            # Get the target peptide's embeddings
            target_embedding = target_peptide["vector"]
            
            # Search for similar peptides using the target's embeddings
            similar_results = self.qdrant_service.search_peptides(target_embedding, limit=top_k + 1)  # type: ignore[attr-defined]  # +1 to exclude self
            
            # Filter out the target peptide itself and format results
            similar_peptides = []
            for result in similar_results:
                result_name = result["payload"]["name"]
                if result_name != peptide_name:  # Exclude the target peptide
                    similar_peptides.append({
                        "name": result_name,
                        "overview": result["payload"]["overview"],
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



