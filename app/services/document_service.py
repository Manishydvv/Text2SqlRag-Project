"""
Document Processing Service
Handles parsing and chunking of various document formats (PDF, DOCX, CSV, JSON).

Now supports context-aware chunking with Docling for improved RAG quality.
"""

from typing import List, Dict, Any
import tiktoken
import logging
from unstructured.partition.auto import partition
from pathlib import Path
from app.config import settings

logger = logging.getLogger("rag_app.document_service")


def parse_document(file_path: str) -> str:
    """
    Parse any document type and return extracted text.
    Uses fast direct read for simple text files (.txt, .md, .csv).
    Uses Unstructured.io for complex formats (PDF, DOCX, JSON, etc.).

    Args:
        file_path: Path to the document file

    Returns:
        str: Extracted text content from the document

    Raises:
        FileNotFoundError: If the file doesn't exist
        Exception: If parsing fails
    """
    # Verify file exists
    if not Path(file_path).exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Fast path for simple text files - bypass unstructured library
    # This is critical for Lambda performance (avoids 30+ second timeout)
    file_extension = Path(file_path).suffix.lower()
    if file_extension in ['.txt', '.md', '.csv', '.log', '.json']:
        try:
            logger.info(f"Using fast text read for {file_extension} file")
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(file_path, 'r', encoding='latin-1') as f:
                    return f.read()
            except Exception as e:
                logger.warning(f"Fast text read failed: {e}, falling back to unstructured")
        except Exception as e:
            logger.warning(f"Fast text read failed: {e}, falling back to unstructured")

    try:
        # Use Unstructured.io's auto partition for complex formats (PDF, DOCX, etc.)
        # strategy="fast" disables OCR (tesseract) for Lambda compatibility
        # OCR can be enabled by adding tesseract Lambda layer and using strategy="hi_res"
        logger.info(f"Using unstructured library for {file_extension} file")
        elements = partition(
            filename=file_path,
            strategy="fast"  # Fast mode: no OCR, works without tesseract
        )

        # Combine all elements into a single text string
        text = "\n\n".join([str(el) for el in elements])

        return text

    except Exception as e:
        raise Exception(f"Failed to parse document {file_path}: {str(e)}")


def chunk_text(
    text: str,
    chunk_size: int = 512,
    overlap: int = 50,
    encoding_name: str = "cl100k_base"  # GPT-4 encoding
) -> List[Dict[str, Any]]:
    """
    Split text into overlapping chunks based on token count.

    Args:
        text: The text to chunk
        chunk_size: Maximum tokens per chunk (default: 512)
        overlap: Number of overlapping tokens between chunks (default: 50)
        encoding_name: Tokenizer encoding to use (default: cl100k_base for GPT-4)

    Returns:
        List of dictionaries containing:
            - text: The chunk text
            - chunk_index: Index of the chunk
            - token_count: Number of tokens in the chunk
            - start_char: Starting character position
            - end_char: Ending character position
    """
    # Initialize tokenizer
    try:
        tokenizer = tiktoken.get_encoding(encoding_name)
    except Exception:
        # Fallback to default encoding
        tokenizer = tiktoken.encoding_for_model("gpt-4")

    # Encode the entire text
    tokens = tokenizer.encode(text)

    chunks = []
    start_idx = 0

    while start_idx < len(tokens):
        # Get chunk tokens
        end_idx = min(start_idx + chunk_size, len(tokens))
        chunk_tokens = tokens[start_idx:end_idx]

        # Decode back to text
        chunk_text = tokenizer.decode(chunk_tokens)

        # Calculate character positions (approximate)
        if chunks:
            # For subsequent chunks, use the previous end position
            start_char = chunks[-1]['end_char'] - (overlap * 4)  # Rough estimate
            start_char = max(0, start_char)
        else:
            start_char = 0

        end_char = start_char + len(chunk_text)

        # Create chunk metadata
        chunk_data = {
            'text': chunk_text,
            'chunk_index': len(chunks),
            'token_count': len(chunk_tokens),
            'start_char': start_char,
            'end_char': end_char
        }

        chunks.append(chunk_data)

        # Move to next chunk with overlap
        start_idx += (chunk_size - overlap)

        # Break if we've reached the end
        if end_idx >= len(tokens):
            break

    return chunks


def chunk_text_semantic(
    text: str,
    chunk_size: int = 512,
    encoding_name: str = "cl100k_base"
) -> List[Dict[str, Any]]:
    """
    Split text into semantic chunks using semchunk library.

    Better than token-based chunking because it:
    - Respects sentence boundaries (no mid-sentence splits)
    - Maintains semantic coherence
    - Still lightweight (pure Python, no PyTorch)

    Falls back to token-based chunking if semchunk unavailable.

    Args:
        text: The text to chunk
        chunk_size: Maximum tokens per chunk (default: 512)
        encoding_name: Tokenizer encoding to use (default: cl100k_base for GPT-4)

    Returns:
        List of dictionaries containing chunk metadata
    """
    # Initialize tokenizer
    tokenizer = tiktoken.get_encoding(encoding_name)

    try:
        from semchunk import chunkerify

        # Create chunker with tokenizer and chunk size
        chunker = chunkerify(tokenizer, chunk_size=chunk_size)

        # Use semchunk for semantic boundaries
        semantic_chunks = chunker(text)

        # Convert to standard format with metadata
        chunks = []
        char_position = 0

        for idx, chunk_text in enumerate(semantic_chunks):
            tokens = tokenizer.encode(chunk_text)

            chunk_data = {
                'text': chunk_text,
                'chunk_index': idx,
                'token_count': len(tokens),
                'start_char': char_position,
                'end_char': char_position + len(chunk_text),
                # Add empty metadata for compatibility with Dockling format
                'headings': [],
                'page_numbers': [],
                'doc_items': [],
                'captions': []
            }

            chunks.append(chunk_data)
            char_position += len(chunk_text)

        logger.info(f"Semantic chunking complete: {len(chunks)} chunks (semchunk)")
        return chunks

    except ImportError:
        logger.warning("semchunk not available, falling back to token-based chunking")
        # Use the standard token-based chunking function
        fallback_chunks = chunk_text(text, chunk_size=chunk_size, overlap=50)

        # Add empty metadata for compatibility
        for chunk in fallback_chunks:
            chunk['headings'] = []
            chunk['page_numbers'] = []
            chunk['doc_items'] = []
            chunk['captions'] = []

        return fallback_chunks

    except Exception as e:
        logger.warning(f"Semantic chunking failed: {e}, falling back to token-based")
        # Use the standard token-based chunking function
        fallback_chunks = chunk_text(text, chunk_size=chunk_size, overlap=50)

        # Add empty metadata for compatibility
        for chunk in fallback_chunks:
            chunk['headings'] = []
            chunk['page_numbers'] = []
            chunk['doc_items'] = []
            chunk['captions'] = []

        return fallback_chunks


def get_document_stats(file_path: str) -> Dict[str, Any]:
    """
    Get statistics about a document.

    Args:
        file_path: Path to the document

    Returns:
        Dictionary with document statistics
    """
    path = Path(file_path)

    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Parse document
    text = parse_document(file_path)

    # Get token count
    tokenizer = tiktoken.encoding_for_model("gpt-4")
    tokens = tokenizer.encode(text)

    return {
        "filename": path.name,
        "file_size_bytes": path.stat().st_size,
        "file_type": path.suffix,
        "character_count": len(text),
        "token_count": len(tokens),
        "estimated_chunks_512": (len(tokens) // 512) + 1
    }


def parse_and_chunk_with_context(file_path: str, chunk_size: int = 512, min_chunk_size: int = 256) -> List[Dict[str, Any]]:
    """
    Parse and chunk document using Docling's context-aware approach.

    This is the RECOMMENDED method that provides:
    - Semantic boundary detection (no mid-sentence splits)
    - Hierarchical heading context preservation
    - Rich metadata (page numbers, captions, document structure)
    - Smart merging to ensure chunks are 256-512 tokens (not too small)

    Falls back to traditional token-based chunking if Docling is unavailable.

    Args:
        file_path: Path to the document file
        chunk_size: Maximum tokens per chunk (default: 512)
        min_chunk_size: Minimum tokens per chunk - smaller chunks will be merged (default: 256)

    Returns:
        List of chunk dictionaries with rich metadata
    """
    # Fast path for simple text files - bypass Docling to avoid Lambda timeout
    # This is critical for Lambda performance (Docling causes 30+ second timeout)
    file_extension = Path(file_path).suffix.lower()
    if file_extension in ['.txt', '.md', '.csv', '.log', '.json']:
        logger.info(f"Using fast semantic chunking for {file_extension} file (bypassing Docling)")
        text = parse_document(file_path)  # Uses fast path internally
        chunks = chunk_text_semantic(text, chunk_size=chunk_size)
        logger.info(f"Fast semantic chunking complete: {len(chunks)} chunks")
        return chunks

    # Check if Docling should be used (config flag)
    if not settings.USE_DOCKLING:
        logger.info(f"Docling disabled via config (USE_DOCKLING=false), using Unstructured + semchunk fallback")
        text = parse_document(file_path)
        chunks = chunk_text_semantic(text, chunk_size=chunk_size)
        logger.info(f"Semantic chunking complete: {len(chunks)} chunks")
        return chunks

    try:
        # Try Docling for complex formats (PDF, DOCX, etc.)
        from app.services.docling_service import parse_and_chunk_document

        logger.info(f"Using Docling for context-aware chunking: {Path(file_path).name}")
        chunks = parse_and_chunk_document(file_path, chunk_size=chunk_size, min_chunk_size=min_chunk_size)

        logger.info(f"Docling chunking complete: {len(chunks)} chunks with heading context")
        return chunks

    except ImportError as e:
        logger.warning(f"Docling not available (import failed), falling back to semantic chunking: {e}")
        text = parse_document(file_path)
        chunks = chunk_text_semantic(text, chunk_size=chunk_size)
        logger.info(f"Semantic chunking complete: {len(chunks)} chunks")
        return chunks

    except Exception as e:
        logger.error(f"Docling failed unexpectedly, falling back to semantic chunking: {e}")
        text = parse_document(file_path)
        chunks = chunk_text_semantic(text, chunk_size=chunk_size)
        logger.info(f"Semantic chunking complete: {len(chunks)} chunks")
        return chunks
