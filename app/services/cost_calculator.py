"""
Cost Calculator Service for External API Usage Tracking

This service calculates the cost of external API calls based on configurable pricing models.
Supports OpenAI (token-based), Qdrant (request-based), Tavily (request-based), and SerpAPI (request-based).
Pricing is configurable through environment variables.
"""

from typing import Dict, Any, Optional, Tuple
from decimal import Decimal
import tiktoken
import os
from app.utils.helpers import logger
from app.core.config import settings


class CostCalculator:
    """Service for calculating costs of external API calls"""
    
    def __init__(self):
        """Initialize cost calculator with environment variable pricing"""
        self.openai_pricing = self._load_openai_pricing()
        self.other_pricing = self._load_other_pricing()
        
        # Validate pricing configuration
        validation = self.validate_pricing_config()
        if not validation["valid"]:
            logger.warning("⚠️ Pricing configuration validation failed:")
            if validation["missing_vars"]:
                logger.warning(f"Missing variables: {validation['missing_vars']}")
            if validation["invalid_vars"]:
                logger.warning(f"Invalid variables: {validation['invalid_vars']}")
        else:
            logger.info("✅ Pricing configuration validation passed")
        
        # Log pricing configuration
        logger.info("💰 Cost calculator initialized with environment variable pricing")
        logger.debug(f"OpenAI pricing loaded: {len(self.openai_pricing)} models")
        logger.debug(f"Other providers pricing loaded: {list(self.other_pricing.keys())}")
    
    def _load_openai_pricing(self) -> Dict[str, Dict[str, float]]:
        """Load OpenAI pricing from settings"""
        pricing = {
            "gpt-4o": {
                "input": settings.OPENAI_GPT4O_INPUT_PRICE,
                "output": settings.OPENAI_GPT4O_OUTPUT_PRICE
            },
            "gpt-4o-mini": {
                "input": settings.OPENAI_GPT4O_MINI_INPUT_PRICE,
                "output": settings.OPENAI_GPT4O_MINI_OUTPUT_PRICE
            },
            "text-embedding-3-large": {
                "input": settings.OPENAI_EMBEDDING_3_LARGE_PRICE,
                "output": 0.0  # No output tokens for embeddings
            },
            "text-embedding-3-small": {
                "input": settings.OPENAI_EMBEDDING_3_SMALL_PRICE,
                "output": 0.0  # No output tokens for embeddings
            },
            "text-embedding-ada-002": {
                "input": settings.OPENAI_EMBEDDING_ADA002_PRICE,
                "output": 0.0  # No output tokens for embeddings
            }
        }
        return pricing
    
    def _load_other_pricing(self) -> Dict[str, Dict[str, float]]:
        """Load other providers pricing from settings"""
        pricing = {
            "qdrant": {
                "search": settings.QDRANT_SEARCH_PRICE,
                "upsert": settings.QDRANT_UPSERT_PRICE,
                "retrieve": settings.QDRANT_RETRIEVE_PRICE,
                "scroll": settings.QDRANT_SCROLL_PRICE,
                "delete": settings.QDRANT_DELETE_PRICE
            },
            "tavily": {
                "search": settings.TAVILY_BASIC_SEARCH_PRICE,
                "advanced_search": settings.TAVILY_ADVANCED_SEARCH_PRICE
            },
            "serpapi": {
                "google_search": settings.SERPAPI_DEVELOPER_PLAN_PRICE,
                "bing_search": settings.SERPAPI_DEVELOPER_PLAN_PRICE,
                "baidu_search": settings.SERPAPI_DEVELOPER_PLAN_PRICE
            }
        }
        return pricing
    
    def validate_pricing_config(self) -> Dict[str, Any]:
        """Validate that all required pricing variables are configured"""
        validation_result = {
            "valid": True,
            "missing_vars": [],
            "invalid_vars": [],
            "warnings": []
        }
        
        # Check OpenAI pricing
        openai_prices = [
            settings.OPENAI_GPT4O_INPUT_PRICE, settings.OPENAI_GPT4O_OUTPUT_PRICE,
            settings.OPENAI_GPT4O_MINI_INPUT_PRICE, settings.OPENAI_GPT4O_MINI_OUTPUT_PRICE,
            settings.OPENAI_EMBEDDING_3_LARGE_PRICE, settings.OPENAI_EMBEDDING_3_SMALL_PRICE,
            settings.OPENAI_EMBEDDING_ADA002_PRICE
        ]
        
        # Check other providers pricing
        other_prices = [
            settings.TAVILY_BASIC_SEARCH_PRICE, settings.TAVILY_ADVANCED_SEARCH_PRICE,
            settings.SERPAPI_DEVELOPER_PLAN_PRICE, settings.SERPAPI_DEVELOPER_PLAN_PRICE,
            settings.SERPAPI_DEVELOPER_PLAN_PRICE,
            settings.QDRANT_SEARCH_PRICE, settings.QDRANT_UPSERT_PRICE, settings.QDRANT_RETRIEVE_PRICE,
            settings.QDRANT_SCROLL_PRICE, settings.QDRANT_DELETE_PRICE
        ]
        
        # Check for invalid values (negative prices)
        all_prices = openai_prices + other_prices
        for price in all_prices:
            if price < 0:
                validation_result["invalid_vars"].append(f"Negative price: {price}")
                validation_result["valid"] = False
        
        return validation_result
    
    def get_pricing_summary(self) -> Dict[str, Any]:
        """Get a summary of current pricing configuration"""
        return {
            "openai_models": {
                model: {
                    "input_price_per_1k": pricing["input"],
                    "output_price_per_1k": pricing["output"]
                }
                for model, pricing in self.openai_pricing.items()
            },
            "other_providers": {
                provider: {
                    operation: price
                    for operation, price in operations.items()
                }
                for provider, operations in self.other_pricing.items()
            }
        }
    
    def calculate_openai_cost(self, model: str, input_tokens: int, output_tokens: int = 0) -> Tuple[float, str]:
        """
        Calculate OpenAI API cost based on model and token usage
        
        Args:
            model: OpenAI model name (e.g., "gpt-4o", "text-embedding-3-large")
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens (0 for embeddings)
            
        Returns:
            Tuple of (cost_usd, pricing_model)
        """
        try:
            if model not in self.openai_pricing:
                logger.warning(f"Unknown OpenAI model: {model}, using default pricing")
                model = "gpt-4o"  # Default fallback
            
            pricing = self.openai_pricing[model]
            
            # Calculate cost per 1K tokens
            input_cost = (input_tokens / 1000) * pricing["input"]
            output_cost = (output_tokens / 1000) * pricing["output"]
            
            total_cost = input_cost + output_cost
            
            return round(total_cost, 6), model
            
        except Exception as e:
            logger.error(f"Error calculating OpenAI cost: {e}")
            return 0.0, model
    
    def calculate_qdrant_cost(self, operation: str) -> Tuple[float, str]:
        """
        Calculate Qdrant API cost based on operation
        
        Args:
            operation: Qdrant operation (e.g., "search", "upsert")
            
        Returns:
            Tuple of (cost_usd, pricing_model)
        """
        try:
            pricing_model = f"qdrant-{operation}"
            cost = self.other_pricing["qdrant"].get(operation, 0.0)
            return cost, pricing_model
            
        except Exception as e:
            logger.error(f"Error calculating Qdrant cost: {e}")
            return 0.0, f"qdrant-{operation}"
    
    def calculate_tavily_cost(self, search_depth: str = "basic") -> Tuple[float, str]:
        """
        Calculate Tavily API cost based on search depth
        
        Args:
            search_depth: Search depth ("basic" or "advanced")
            
        Returns:
            Tuple of (cost_usd, pricing_model)
        """
        try:
            if search_depth == "advanced":
                cost = self.other_pricing["tavily"]["advanced_search"]
                pricing_model = "tavily-advanced"
            else:
                cost = self.other_pricing["tavily"]["search"]
                pricing_model = "tavily-basic"
            
            return cost, pricing_model
            
        except Exception as e:
            logger.error(f"Error calculating Tavily cost: {e}")
            return 0.001, "tavily-basic"  # Default fallback
    
    def calculate_serpapi_cost(self, search_type: str = "google_search") -> Tuple[float, str]:
        """
        Calculate SerpAPI cost based on search type
        
        Args:
            search_type: Type of search (e.g., "google_search", "bing_search")
            
        Returns:
            Tuple of (cost_usd, pricing_model)
        """
        try:
            cost = self.other_pricing["serpapi"].get(search_type, 0.001)
            pricing_model = f"serpapi-{search_type}"
            return cost, pricing_model
            
        except Exception as e:
            logger.error(f"Error calculating SerpAPI cost: {e}")
            return 0.001, f"serpapi-{search_type}"
    
    def count_tokens(self, text: str, model: str = "gpt-4o") -> int:
        """
        Count tokens in text for OpenAI models
        
        Args:
            text: Text to count tokens for
            model: OpenAI model name
            
        Returns:
            Number of tokens
        """
        try:
            # Map models to their tokenizers
            tokenizer_models = {
                "gpt-4o": "cl100k_base",
                "gpt-4o-mini": "cl100k_base",
                "text-embedding-3-large": "cl100k_base",
                "text-embedding-3-small": "cl100k_base",
                "text-embedding-ada-002": "cl100k_base"
            }
            
            encoding_name = tokenizer_models.get(model, "cl100k_base")
            encoding = tiktoken.get_encoding(encoding_name)
            return len(encoding.encode(text))
            
        except Exception as e:
            logger.error(f"Error counting tokens: {e}")
            # Fallback: rough estimation (1 token ≈ 4 characters)
            return len(text) // 4
    
    def calculate_cost(self, provider: str, operation: str, metadata: Dict[str, Any] = None) -> Tuple[float, str, Optional[int], Optional[int]]:
        """
        Calculate cost for any provider based on operation and metadata
        
        Args:
            provider: Provider name (openai, qdrant, tavily, serpapi)
            operation: Operation type
            metadata: Additional metadata (model, tokens, etc.)
            
        Returns:
            Tuple of (cost_usd, pricing_model, input_tokens, output_tokens)
        """
        try:
            metadata = metadata or {}
            
            if provider.lower() == "openai":
                model = metadata.get("model", "gpt-4o")
                input_tokens = metadata.get("input_tokens", 0)
                output_tokens = metadata.get("output_tokens", 0)
                
                # If tokens not provided, try to count them
                if input_tokens == 0 and "input_text" in metadata:
                    input_tokens = self.count_tokens(metadata["input_text"], model)
                if output_tokens == 0 and "output_text" in metadata:
                    output_tokens = self.count_tokens(metadata["output_text"], model)
                
                cost, pricing_model = self.calculate_openai_cost(model, input_tokens, output_tokens)
                return cost, pricing_model, input_tokens, output_tokens
                
            elif provider.lower() == "qdrant":
                cost, pricing_model = self.calculate_qdrant_cost(operation)
                return cost, pricing_model, None, None
                
            elif provider.lower() == "tavily":
                search_depth = metadata.get("search_depth", "basic")
                cost, pricing_model = self.calculate_tavily_cost(search_depth)
                return cost, pricing_model, None, None
                
            elif provider.lower() == "serpapi":
                search_type = metadata.get("search_type", "google_search")
                cost, pricing_model = self.calculate_serpapi_cost(search_type)
                return cost, pricing_model, None, None
            
            else:
                logger.warning(f"Unknown provider: {provider}")
                return 0.0, f"{provider}-{operation}", None, None
                
        except Exception as e:
            logger.error(f"Error calculating cost for {provider}: {e}")
            return 0.0, f"{provider}-{operation}", None, None


# Global instance
cost_calculator = CostCalculator()
