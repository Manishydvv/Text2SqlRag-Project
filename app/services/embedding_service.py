"""
Embedding Service
Handles generation of embeddings using OpenAI's API.
"""

from typing import List, Tuple, Optional, Dict
from openai import AsyncOpenAI
import logging
from app.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating text embeddings using OpenAI."""

    def __init__(self, api_key: str | None = None, query_cache_service=None):
        """
        Initialize the embedding service.

        Args:
            api_key: OpenAI API key (optional, uses settings if not provided)
            query_cache_service: Optional QueryCacheService for embedding caching
        """
        self.api_key = api_key or settings.OPENAI_API_KEY
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY in .env file.")

        self.client = AsyncOpenAI(api_key=self.api_key)
        self.model = "text-embedding-3-small"  # 1536 dimensions
        self.dimensions = 1536
        self.query_cache_service = query_cache_service  # Optional cache service

    async def generate_embeddings(self, texts: List[str]) -> Tuple[List[List[float]], Optional[Dict]]:
        """
        Generate embeddings for a list of texts with caching support.

        NEW: Implements per-text caching to avoid re-computing identical embeddings.
        - Cache key: hash(text)
        - Cache TTL: 7 days (embeddings are deterministic)
        - Falls back to uncached if Redis unavailable

        Args:
            texts: List of text strings to embed

        Returns:
            Tuple of (embeddings, usage_info) where:
            - embeddings: List of embedding vectors (each is a list of floats)
            - usage_info: Dict with token counts and model info for cost tracking

        Raises:
            Exception: If embedding generation fails
        """
        if not texts:
            return [], None

        # If cache is available, check each text individually
        if self.query_cache_service and self.query_cache_service.enabled:
            embeddings = []
            texts_to_generate = []
            text_indices = []  # Track original indices for uncached texts
            cache_hits = 0
            cache_misses = 0

            for i, text in enumerate(texts):
                cache_key = self.query_cache_service.get_embedding_key(text)
                cached = self.query_cache_service.get(cache_key, cache_type="embedding")

                if cached and "embedding" in cached:
                    embeddings.append(cached["embedding"])
                    cache_hits += 1
                else:
                    embeddings.append(None)  # Placeholder
                    texts_to_generate.append(text)
                    text_indices.append(i)
                    cache_misses += 1

            # Generate embeddings for uncached texts
            if texts_to_generate:
                try:
                    response = await self.client.embeddings.create(
                        model=self.model,
                        input=texts_to_generate,
                        encoding_format="float"
                    )

                    new_embeddings = [item.embedding for item in response.data]

                    # Cache new embeddings and fill in results
                    for idx, embedding in zip(text_indices, new_embeddings):
                        embeddings[idx] = embedding

                        # Cache individual embedding
                        cache_key = self.query_cache_service.get_embedding_key(texts[idx])
                        cache_value = {
                            "embedding": embedding,
                            "model": self.model,
                            "text_length": len(texts[idx])
                        }
                        ttl = settings.CACHE_TTL_EMBEDDINGS  # Default: 7 days
                        self.query_cache_service.set(cache_key, cache_value, ttl=ttl, cache_type="embedding")

                    # Log cache statistics
                    logger.debug(f"Embedding cache: {cache_hits} hits, {cache_misses} misses "
                               f"({cache_hits/(cache_hits+cache_misses)*100:.1f}% hit rate)")

                    # Build usage info
                    usage_info = {
                        "prompt_tokens": response.usage.prompt_tokens,
                        "total_tokens": response.usage.total_tokens,
                        "model": self.model,
                        "cache_hits": cache_hits,
                        "cache_misses": cache_misses
                    } if hasattr(response, 'usage') and response.usage else {
                        "cache_hits": cache_hits,
                        "cache_misses": cache_misses
                    }

                    return embeddings, usage_info

                except Exception as e:
                    raise Exception(f"Failed to generate embeddings: {str(e)}")
            else:
                # All embeddings came from cache
                logger.debug(f"Embedding cache: {cache_hits} hits, 0 misses (100% cache hit rate)")
                return embeddings, {
                    "cache_hits": cache_hits,
                    "cache_misses": 0,
                    "model": self.model
                }

        # No cache available - generate all embeddings
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=texts,
                encoding_format="float"
            )

            embeddings = [item.embedding for item in response.data]

            usage_info = {
                "prompt_tokens": response.usage.prompt_tokens,
                "total_tokens": response.usage.total_tokens,
                "model": self.model
            } if hasattr(response, 'usage') and response.usage else None

            return embeddings, usage_info

        except Exception as e:
            raise Exception(f"Failed to generate embeddings: {str(e)}")

    async def generate_single_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text string to embed

        Returns:
            Embedding vector (list of floats)
        """
        embeddings, _ = await self.generate_embeddings([text])
        return embeddings[0]

    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of embeddings produced by this service.

        Returns:
            int: Embedding dimension (1536 for text-embedding-3-small)
        """
        return self.dimensions
