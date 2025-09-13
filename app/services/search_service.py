import requests
from bs4 import BeautifulSoup
from serpapi import GoogleSearch
import tiktoken
import json
from typing import List, Dict, Any
import logging
from sqlalchemy.orm import Session
from app.models.search import SearchRequest, SearchResult, ContentChunk, SearchResponse
from app.core.config import settings
from app.utils.helpers import logger
from datetime import datetime

class SearchService:
    def __init__(self):
        self.serp_api_key = settings.SERP_API_KEY
        self.openai_api_key = settings.OPENAI_API_KEY
        self.chunk_size = 1000  # characters per chunk
        self.chunk_overlap = 200  # overlap between chunks
        self.max_chunks_per_site = 5  # maximum chunks per website

    def search_peptide(self, search_request: SearchRequest, db: Session) -> SearchResponse:
        """Main method to perform complete peptide search"""
        try:
            logger.info(f"Starting search for peptide: {search_request.peptide_name}")
            
            # Step 1: Search using SerpAPI (get more results to find allowed URLs)
            search_results = self._perform_serp_search(search_request)
            logger.info(f"Found {len(search_results)} search results from SerpAPI")
            
            # Step 2: Scrape content from allowed URLs only
            scraped_content = self._scrape_top_results(search_results, db)
            logger.info(f"Scraped content from {len(scraped_content)} allowed websites")
            
            # If no allowed URLs found, return error response
            if not scraped_content:
                logger.warning("No allowed URLs found in search results")
                return SearchResponse(
                    peptide_name=search_request.peptide_name,
                    requirements=search_request.requirements,
                    generated_response="No information found from allowed sources. Please add relevant domains to the allowed URLs list.",
                    source_sites=[],
                    search_timestamp=datetime.utcnow()
                )
            
            # Step 3: Chunk the content
            content_chunks = self._chunk_content(scraped_content)
            logger.info(f"Created {len(content_chunks)} content chunks")
            
            # Step 4: Perform similarity search to find most relevant chunks
            relevant_chunks = self._find_relevant_chunks(content_chunks, search_request)
            logger.info(f"Found {len(relevant_chunks)} relevant chunks")
            
            # Check if no chunks meet the confidence threshold
            if not relevant_chunks:
                logger.warning("No chunks found that meet the confidence score threshold")
                return SearchResponse(
                    peptide_name=search_request.peptide_name,
                    requirements=search_request.requirements,
                    generated_response="No content found that matches the specified confidence score threshold. Please try adjusting the CONFIDENCE_SCORE setting or refine your search query.",
                    source_sites=[],
                    search_timestamp=datetime.utcnow()
                )
            
            # Step 5: Generate LLM response
            generated_response = self._generate_llm_response(relevant_chunks, search_request)
            logger.info("Generated LLM response successfully")
            
            # Step 6: Create final response with similarity scores for source sites
            source_sites = self._calculate_source_similarity_scores(scraped_content, search_request)
            
            return SearchResponse(
                peptide_name=search_request.peptide_name,
                requirements=search_request.requirements,
                generated_response=generated_response,
                source_sites=source_sites,
                search_timestamp=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"Error in search_peptide: {str(e)}")
            raise

    def _perform_serp_search(self, search_request: SearchRequest) -> List[SearchResult]:
        """Perform search using SerpAPI"""
        try:
            query = f"{search_request.peptide_name} {search_request.requirements}"
            
            search = GoogleSearch({
                "q": query,
                "api_key": self.serp_api_key,
                "num": 50  # Get top 50 results to find more allowed URLs
            })
            
            results = search.get_dict()
            organic_results = results.get("organic_results", [])
            
            search_results = []
            for i, result in enumerate(organic_results):
                search_results.append(SearchResult(
                    title=result.get("title", ""),
                    url=result.get("link", ""),
                    snippet=result.get("snippet", ""),
                    rank=i + 1
                ))
            
            return search_results
            
        except Exception as e:
            logger.error(f"Error in SerpAPI search: {str(e)}")
            raise

    def _scrape_top_results(self, search_results: List[SearchResult], db: Session) -> List[Dict[str, Any]]:
        """Scrape content from top results that are in allowed URLs"""
        scraped_content = []
        allowed_count = 0
        
        for result in search_results:
            try:
                logger.info(f"Checking if URL is allowed: {result.url}")
                
                # Check if URL is in allowed URLs
                if not self._is_url_allowed(result.url, db):
                    logger.info(f"URL not allowed, skipping: {result.url}")
                    continue
                
                allowed_count += 1
                logger.info(f"URL allowed, scraping content from: {result.url}")
                
                # Scrape the webpage
                content = self._scrape_webpage(result.url)
                if content:
                    scraped_content.append({
                        "url": result.url,
                        "title": result.title,
                        "content": content
                    })
                    logger.info(f"Successfully scraped content from: {result.url}")
                
                # Stop if we have enough allowed URLs (max 5)
                if allowed_count >= 5:
                    logger.info(f"Reached maximum allowed URLs limit (5)")
                    break
                
            except Exception as e:
                logger.error(f"Error scraping {result.url}: {str(e)}")
                continue
        
        logger.info(f"Total URLs checked: {len(search_results)}, Allowed URLs: {allowed_count}, Successfully scraped: {len(scraped_content)}")
        return scraped_content

    def _is_url_allowed(self, url: str, db: Session) -> bool:
        """Check if URL is in allowed URLs list from database"""
        try:
            from app.services.allowed_url_service import AllowedUrlService
            
            # Extract domain from URL
            from urllib.parse import urlparse
            parsed_url = urlparse(url)
            domain = parsed_url.netloc.lower()
            
            # Remove 'www.' prefix if present
            if domain.startswith('www.'):
                domain = domain[4:]
            
            # Check if domain exists in allowed_urls table
            allowed_url_service = AllowedUrlService(db)
            allowed_urls = allowed_url_service.get_all_allowed_urls()
            
            # First check regular URLs
            for allowed_url in allowed_urls:
                # Skip wildcard URLs for now
                if '*' in allowed_url.url:
                    continue
                    
                allowed_domain = urlparse(allowed_url.url).netloc.lower()
                if allowed_domain.startswith('www.'):
                    allowed_domain = allowed_domain[4:]
                
                # Check if domain matches exactly or is a subdomain
                if domain == allowed_domain or domain.endswith('.' + allowed_domain):
                    return True
            
            # Check for global wildcard "*" (allows any domain)
            for allowed_url in allowed_urls:
                if allowed_url.url == '*':
                    logger.info(f"URL {url} allowed via global wildcard '*'")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking if URL is allowed: {str(e)}")
            return False

    def _scrape_webpage(self, url: str) -> str:
        """Scrape content from a single webpage"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Extract text content
            text = soup.get_text()
            
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            return text[:10000]  # Limit to first 10k characters
            
        except Exception as e:
            logger.error(f"Error scraping webpage {url}: {str(e)}")
            return ""

    def _chunk_content(self, scraped_content: List[Dict[str, Any]]) -> List[ContentChunk]:
        """Break content into chunks"""
        chunks = []
        
        for item in scraped_content:
            content = item["content"]
            url = item["url"]
            
            # Split content into chunks
            content_chunks = self._split_text_into_chunks(content)
            
            for i, chunk in enumerate(content_chunks):
                if len(chunks) >= self.max_chunks_per_site * len(scraped_content):
                    break
                    
                chunks.append(ContentChunk(
                    content=chunk,
                    source_url=url,
                    chunk_index=i,
                    relevance_score=None
                ))
        
        return chunks

    def _split_text_into_chunks(self, text: str) -> List[str]:
        """Split text into overlapping chunks"""
        chunks = []
        start = 0
        
        while start < len(text):
            end = start + self.chunk_size
            chunk = text[start:end]
            
            if chunk.strip():
                chunks.append(chunk.strip())
            
            start = end - self.chunk_overlap
            
            if start >= len(text):
                break
        
        return chunks

    def _find_relevant_chunks(self, chunks: List[ContentChunk], search_request: SearchRequest) -> List[ContentChunk]:
        """Find most relevant chunks using similarity search with confidence score filtering"""
        try:
            from app.core.config import settings
            
            # Simple keyword-based relevance scoring
            query_terms = f"{search_request.peptide_name} {search_request.requirements}".lower().split()
            min_confidence = settings.CONFIDENCE_SCORE
            
            scored_chunks = []
            for chunk in chunks:
                chunk_lower = chunk.content.lower()
                score = sum(1 for term in query_terms if term in chunk_lower)
                
                # Calculate confidence score as percentage (0-100)
                max_possible_score = len(query_terms)
                confidence_score = (score / max_possible_score * 100) if max_possible_score > 0 else 0
                
                chunk.relevance_score = score
                chunk.confidence_score = confidence_score
                scored_chunks.append(chunk)
            
            # Filter chunks by confidence score
            filtered_chunks = [
                chunk for chunk in scored_chunks 
                if chunk.confidence_score >= min_confidence
            ]
            
            # Sort by relevance score (highest first)
            filtered_chunks.sort(key=lambda x: x.relevance_score or 0, reverse=True)
            
            logger.info(f"Chunks filtered: {len(scored_chunks)} total, {len(filtered_chunks)} above {min_confidence}% confidence")
            
            # If no chunks meet the threshold, log the highest confidence found
            if not filtered_chunks and scored_chunks:
                highest_confidence = max(chunk.confidence_score for chunk in scored_chunks)
                logger.warning(f"No chunks meet {min_confidence}% confidence threshold. Highest confidence found: {highest_confidence:.1f}%")
            
            # Return top 10 most relevant chunks that meet confidence threshold
            return filtered_chunks[:10]
            
        except Exception as e:
            logger.error(f"Error in similarity search: {str(e)}")
            return chunks[:10]  # Return first 10 chunks if similarity search fails

    def _generate_llm_response(self, relevant_chunks: List[ContentChunk], search_request: SearchRequest) -> str:
        """Generate response using OpenAI LLM via direct HTTP requests"""
        try:
            if not self.openai_api_key:
                return "LLM processing not available - API key not configured"
            
            # Prepare context from relevant chunks
            context = "\n\n".join([
                f"Source {i+1} ({chunk.source_url}):\n{chunk.content}"
                for i, chunk in enumerate(relevant_chunks)
            ])
            
            # Create prompt
            prompt = f"""
            Based on the following information about {search_request.peptide_name}, 
            please provide a focused response specifically addressing: {search_request.requirements}
            
            Information sources:
            {context}
            
            IMPORTANT FORMATTING REQUIREMENTS:
            - Write in plain text only, NO markdown formatting
            - Use normal paragraphs with proper spacing
            - Keep response under  1000characters
            - Make it easy to read and understand
            - Focus only on what was asked for - do not include extra information unless directly relevant
            - Keep the response focused and to the point
            """
            
            # Call OpenAI Responses API directly via HTTP request
            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }
            
            system_instruction = (
                "You are a helpful assistant specializing in peptide research and information. "
                "Provide focused, concise responses that directly answer the user's specific question "
                "without unnecessary details. Write in plain text only, no markdown formatting."
            )
            full_input = f"{system_instruction}\n\n{prompt}"
            
            payload = {
                "model": "gpt-4o-mini",
                "input": full_input,
                "temperature": 0.3,
                "max_output_tokens": 600  # Reduced to ensure under 1000 characters
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
                        return self._clean_llm_response(output_text.strip())
                    else:
                        logger.error("No text found in Responses API output")
                        return self._clean_llm_response("No response generated")
                else:
                    logger.error(f"OpenAI Responses API returned unexpected status: {data.get('status')}")
                    return self._clean_llm_response(json.dumps(data)[:1000])
            else:
                logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
                return f"Error from OpenAI API: {response.status_code}"
            
        except Exception as e:
            logger.error(f"Error generating LLM response: {str(e)}")
            return f"Error generating response: {str(e)}"

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

    def _calculate_source_similarity_scores(self, scraped_content: List[Dict[str, Any]], search_request: SearchRequest) -> List[Dict[str, Any]]:
        """Calculate similarity scores for each source site"""
        source_sites = []
        query_terms = f"{search_request.peptide_name} {search_request.requirements}".lower().split()
        
        for item in scraped_content:
            content = item["content"].lower()
            title = item["title"].lower()
            
            # Calculate similarity score based on keyword matches
            content_score = sum(1 for term in query_terms if term in content)
            title_score = sum(1 for term in query_terms if term in title)
            
            # Weight title matches more heavily
            total_score = (content_score * 0.7) + (title_score * 0.3)
            
            # Normalize score (0-1 range)
            max_possible_score = len(query_terms) * 0.7 + len(query_terms) * 0.3
            similarity_score = min(total_score / max_possible_score, 1.0) if max_possible_score > 0 else 0.0
            
            source_sites.append({
                "title": item["title"],
                "url": item["url"],
                "similarity_score": round(similarity_score, 3),
                "content_length": len(item["content"])
            })
        
        # Sort by similarity score (highest first)
        source_sites.sort(key=lambda x: x["similarity_score"], reverse=True)
        
        logger.info(f"Calculated similarity scores for {len(source_sites)} sources")
        return source_sites
