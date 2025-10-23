"""OpenAI provider implementation for managing OpenAI API interactions."""

import requests
import logging
from typing import List, Dict, Any, Optional
from app.providers.base_provider import BaseProvider
from app.utils.helpers import logger, ExternalApiTimer


class OpenAIProvider(BaseProvider):
    """OpenAI provider for managing all OpenAI API interactions globally."""
    
    def __init__(self, api_key: str):
        """Initialize OpenAI provider with API key."""
        super().__init__(api_key)
        self.base_url = "https://api.openai.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def generate_embedding(self, text: str, model: str = "text-embedding-3-large") -> List[float]:
        """Generate embedding using OpenAI API."""
        try:
            if not self.api_key:
                raise ValueError("OpenAI API key not configured")
            
            payload = {
                "input": text,
                "model": model
            }
            
            # Calculate input tokens for cost tracking
            from app.services.cost_calculator import cost_calculator
            input_tokens = cost_calculator.count_tokens(text, model)
            
            with ExternalApiTimer("openai", operation="embeddings", metadata={
                "model": model, 
                "text_length": len(text),
                "input_tokens": input_tokens,
                "input_text": text
            }) as t:
                response = requests.post(
                    f"{self.base_url}/embeddings",
                    headers=self.headers,
                    json=payload,
                    timeout=30
                )
                
                # Set tracking data
                t.set_status(status_code=response.status_code, success=response.status_code == 200)
                t.set_io(request_bytes=len(str(payload).encode()), response_bytes=len(response.content))
            
            if response.status_code == 200:
                data = response.json()
                embedding = data["data"][0]["embedding"]
                
                # Get actual token counts from OpenAI API response
                usage = data.get("usage", {})
                actual_input_tokens = usage.get("prompt_tokens", input_tokens)
                
                # Update the timer with actual token information
                t.set_cost_data(
                    cost_usd=0.0,  # Will be calculated automatically
                    input_tokens=actual_input_tokens,
                    output_tokens=0,  # Embeddings don't have output tokens
                    pricing_model=model
                )
                
                logger.debug(f"OpenAI Embeddings API tokens - Input: {actual_input_tokens}")
                logger.info(f"Generated embedding successfully for text length {len(text)}, dimensions: {len(embedding)}")
                return embedding
            else:
                logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
                raise Exception(f"Failed to generate embedding: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            raise
    
    def generate_chat_completion(self, messages: List[Dict[str, str]], 
                               model: str = "gpt-4o", 
                               temperature: float = 0.3, 
                               max_tokens: Optional[int] = None,
                               timeout: int = 45) -> str:
        """Generate chat completion using OpenAI API."""
        try:
            if not self.api_key:
                raise ValueError("OpenAI API key not configured")
            
            payload = {
                "model": model,
                "messages": messages,
                "temperature": temperature
            }
            
            if max_tokens:
                payload["max_tokens"] = max_tokens
            
            # Calculate input tokens for cost tracking
            from app.services.cost_calculator import cost_calculator
            input_text = " ".join([msg.get("content", "") for msg in messages])
            input_tokens = cost_calculator.count_tokens(input_text, model)
            
            with ExternalApiTimer("openai", operation="chat.completions", metadata={
                "model": model, 
                "message_count": len(messages),
                "input_tokens": input_tokens,
                "input_text": input_text
            }) as t:
                response = requests.post(
                    f"{self.base_url}/chat/completions",
                    headers=self.headers,
                    json=payload,
                    timeout=timeout
                )
                
                # Set tracking data
                t.set_status(status_code=response.status_code, success=response.status_code == 200)
                t.set_io(request_bytes=len(str(payload).encode()), response_bytes=len(response.content))
            
            if response.status_code == 200:
                data = response.json()
                response_text = data["choices"][0]["message"]["content"].strip()
                
                # Get actual token counts from OpenAI API response
                usage = data.get("usage", {})
                actual_input_tokens = usage.get("prompt_tokens", input_tokens)  # Fallback to estimated if not available
                actual_output_tokens = usage.get("completion_tokens", 0)
                
                # Update the timer with actual token information
                t.set_cost_data(
                    cost_usd=0.0,  # Will be calculated automatically
                    input_tokens=actual_input_tokens,
                    output_tokens=actual_output_tokens,
                    pricing_model=model
                )
                
                logger.debug(f"OpenAI API tokens - Input: {actual_input_tokens}, Output: {actual_output_tokens}")
                
                return response_text
            else:
                logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
                raise Exception(f"Failed to generate chat completion: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error generating chat completion: {str(e)}")
            raise
    
    def generate_response(self, input_text: str, 
                        model: str = "gpt-4o", 
                        temperature: float = 0.3, 
                        max_output_tokens: int = 400,
                        timeout: int = 45) -> str:
        """Generate response using OpenAI Responses API."""
        try:
            if not self.api_key:
                raise ValueError("OpenAI API key not configured")
            
            payload = {
                "model": model,
                "input": input_text,
                "temperature": temperature,
                "max_output_tokens": max_output_tokens
            }
            
            # Calculate input tokens for cost tracking
            from app.services.cost_calculator import cost_calculator
            input_tokens = cost_calculator.count_tokens(input_text, model)
            
            with ExternalApiTimer("openai", operation="responses", metadata={
                "model": model, 
                "input_length": len(input_text),
                "input_tokens": input_tokens,
                "input_text": input_text
            }) as t:
                response = requests.post(
                    f"{self.base_url}/responses",
                    headers=self.headers,
                    json=payload,
                    timeout=timeout
                )
                
                # Set tracking data
                t.set_status(status_code=response.status_code, success=response.status_code == 200)
                t.set_io(request_bytes=len(str(payload).encode()), response_bytes=len(response.content))
            
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
                        # Get actual token counts from OpenAI API response
                        usage = data.get("usage", {})
                        actual_input_tokens = usage.get("prompt_tokens", input_tokens)
                        actual_output_tokens = usage.get("completion_tokens", 0)
                        
                        # Update the timer with actual token information
                        t.set_cost_data(
                            cost_usd=0.0,  # Will be calculated automatically
                            input_tokens=actual_input_tokens,
                            output_tokens=actual_output_tokens,
                            pricing_model=model
                        )
                        
                        logger.debug(f"OpenAI Responses API tokens - Input: {actual_input_tokens}, Output: {actual_output_tokens}")
                        logger.info("Generated response successfully using Responses API")
                        return output_text.strip()
                    else:
                        logger.error("No text found in Responses API output")
                        raise Exception("No response generated from Responses API")
                else:
                    logger.error(f"OpenAI Responses API returned unexpected status: {data.get('status')}")
                    raise Exception(f"Unexpected response status: {data.get('status')}")
            else:
                logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
                raise Exception(f"Failed to generate response: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            raise
    
    def judge_relevance(self, user_query: str, candidate_content: str, 
                       peptide_name: Optional[str] = None) -> bool:
        """Ask LLM to judge if candidate_content is relevant to user_query."""
        try:
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

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            response = self.generate_chat_completion(
                messages=messages,
                model="gpt-4o",
                temperature=0.0,
                max_tokens=2,
                timeout=20
            )
            
            normalized = response.lower()
            return normalized.startswith("yes")
            
        except Exception as e:
            logger.warning(f"Judge relevance failed: {str(e)}")
            return False
    
    def generate_chemical_field(self, peptide_name: str, field: str) -> str:
        """Generate exactly one requested chemical field using LLM only."""
        try:
            rules = (
                "You MUST return ONLY the value for the requested field in plain text."
                " No labels, no extra words, no units unless the field requires it,"
                " no punctuation beyond what is part of the value."
            )

            if field == "sequence":
                requirement = "Return ONLY the sequence for this entity."
            elif field == "chemical_formula":
                requirement = "Return ONLY the chemical formula (e.g., C38H68N10O14)."
            elif field == "molecular_mass":
                requirement = "Return ONLY the molecular mass with units 'g/mol' (e.g., 973.13 g/mol)."
            elif field == "iupac_name":
                requirement = "Return ONLY the IUPAC or systematic name."
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

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            logger.debug(f"Generating chemical field: field='{field}', peptide='{peptide_name}'")

            response = self.generate_chat_completion(
                messages=messages,
                model="gpt-4.1-2025-04-14",
                max_tokens=120,
                timeout=30
            )
            
            if not response:
                logger.warning(f"OpenAI returned empty content for field='{field}', peptide='{peptide_name}'")
            
            return response
            
        except Exception as e:
            logger.error(f"Unhandled error generating chemical field '{field}' for '{peptide_name}': {str(e)}")
            return ""
