import requests
import logging
from typing import List, Dict, Any
from app.models.peptide import PeptideCreate, PeptidePayload
from app.services.qdrant_service import QdrantService
from app.services.chat_restriction_service import ChatRestrictionService
from app.core.config import settings
from app.core.database import get_db
from app.utils.helpers import logger

class PeptideService:
    def __init__(self):
        """Initialize peptide service with Qdrant and OpenAI integration"""
        self.qdrant_service = QdrantService()
        self.openai_api_key = settings.OPENAI_API_KEY
        
        # Ensure the name index exists for efficient searching
        try:
            self.qdrant_service.ensure_name_index()
        except Exception as e:
            logger.warning(f"Could not ensure name index: {str(e)}")

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
            
            # Store in Qdrant
            point_id = self.qdrant_service.store_peptide(peptide_payload, embedding)
            
            logger.info(f"Peptide '{peptide_data.name}' created successfully with ID: {point_id}")
            
            return {
                "name": peptide_data.name,
                "message": "Peptide stored successfully in vector database"
            }
            
        except Exception as e:
            logger.error(f"Error creating peptide: {str(e)}")
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
                "model": "text-embedding-3-small"
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
                # Truncate to 768 dimensions to match your Qdrant collection
                embedding = embedding[:768]
                logger.info(f"Generated embedding successfully for text of length: {len(text)}, truncated to {len(embedding)} dimensions")
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
            You have access to detailed information about the peptide {peptide_name}.
            
            Please answer the user's question based ONLY on the peptide information provided.
            If the question cannot be answered with the available information, say so clearly.
            
            IMPORTANT FORMATTING REQUIREMENTS:
            - Write in plain text only, NO markdown formatting
            - Use normal paragraphs with proper spacing
            - Keep response under 1000 characters
            - Make it easy to read and understand
            
            {restrictions_text}"""
            
            user_prompt = f"""Peptide Information for {peptide_name}:
            {peptide_context}
            
            User Question: {user_query}
            
            Please provide a clear, accurate answer based on the peptide information above.
            Remember: plain text only, no markdown, under 1000 characters, normal paragraphs."""
            
            payload = {
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.3,
                "max_tokens": 400  # Reduced to ensure under 1000 characters
            }
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=45
            )
            
            if response.status_code == 200:
                data = response.json()
                llm_response = data["choices"][0]["message"]["content"]
                
                # Clean up the response to ensure it's plain text and under 1000 characters
                cleaned_response = self._clean_llm_response(llm_response)
                
                logger.info(f"Generated LLM response successfully for peptide: {peptide_name}")
                return cleaned_response
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

    def query_peptide(self, peptide_name: str, user_query: str) -> str:
        """Query a peptide using LLM with the peptide data as context"""
        try:
            logger.info(f"Querying peptide: {peptide_name} with question: {user_query}")
            
            # Get peptide data from Qdrant
            peptide_data = self.qdrant_service.get_peptide_by_name(peptide_name)
            
            if not peptide_data:
                raise ValueError(f"Peptide '{peptide_name}' not found")
            
            # Extract the text content for LLM context
            text_content = peptide_data["payload"]["text_content"]
            
            # Generate LLM response using the peptide context
            llm_response = self._generate_llm_response(text_content, user_query, peptide_name)
            
            logger.info(f"Successfully generated LLM response for peptide: {peptide_name}")
            return llm_response
            
        except Exception as e:
            logger.error(f"Error querying peptide: {str(e)}")
            raise

    def delete_peptide(self, peptide_name: str) -> bool:
        """Delete a peptide by name"""
        try:
            logger.info(f"Deleting peptide: {peptide_name}")
            
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
        """Search for peptides using vector similarity and answer queries"""
        try:
            logger.info(f"Searching peptides with query: {query}")
            
            # Generate embedding for the search query
            query_embedding = self._generate_embedding(query)
            
            # Search for the most similar peptide in Qdrant
            search_result = self.qdrant_service.search_peptides(query_embedding, limit=1)
            
            if not search_result:
                raise ValueError("No peptides found in the database")
            
            # Get the best match
            best_match = search_result[0]
            peptide_name = best_match["payload"]["name"]
            similarity_score = best_match["score"]
            peptide_context = best_match["payload"]["text_content"]
            
            logger.info(f"Found best matching peptide: {peptide_name} with score: {similarity_score}")
            
            # Generate LLM response using the peptide context
            llm_response = self._generate_llm_response(peptide_context, query, peptide_name)
            
            return {
                "llm_response": llm_response,
                "peptide_name": peptide_name,
                "similarity_score": similarity_score,
                "peptide_context": peptide_context
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

    def find_similar_peptides(self, peptide_name: str, top_k: int = 4) -> List[Dict[str, Any]]:
        """Find similar peptides based on vector similarity"""
        try:
            logger.info(f"Finding similar peptides for: {peptide_name}")
            
            # First, get the target peptide to extract its embeddings
            target_peptide = self.qdrant_service.get_peptide_by_name(peptide_name)
            
            if not target_peptide:
                raise ValueError(f"Peptide '{peptide_name}' not found")
            
            # Get the target peptide's embeddings
            target_embedding = target_peptide["vector"]
            
            # Search for similar peptides using the target's embeddings
            similar_results = self.qdrant_service.search_peptides(target_embedding, limit=top_k + 1)  # +1 to exclude self
            
            # Filter out the target peptide itself and format results
            similar_peptides = []
            for result in similar_results:
                result_name = result["payload"]["name"]
                if result_name != peptide_name:  # Exclude the target peptide
                    similar_peptides.append({
                        "name": result_name,
                        "overview": result["payload"]["overview"],
                        "similarity_score": result["score"]
                    })
                    
                    # Stop when we have enough results
                    if len(similar_peptides) >= top_k:
                        break
            
            logger.info(f"Found {len(similar_peptides)} similar peptides for {peptide_name}")
            return similar_peptides
            
        except Exception as e:
            logger.error(f"Error finding similar peptides: {str(e)}")
            raise
