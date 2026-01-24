"""
RAG Service - PDF Parsing, Chunking, and Embedding Generation
===============================================================
This service handles the RAG (Retrieval-Augmented Generation) pipeline:
1. PDF text extraction
2. Text chunking with overlap
3. Vector embedding generation using sentence-transformers

DigiMasterJi - Multilingual AI Tutor for Rural Education

Model: sentence-transformers/all-MiniLM-L6-v2
- 384-dimensional embeddings
- Fast and efficient
- Good for semantic similarity
"""

from typing import List, Dict, Any, Optional, TYPE_CHECKING
import os
import tempfile
import re

# Lazy imports for heavy ML libraries
if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

# Module-level cache for lazy imports
_embedding_model = None
_fitz = None
_tiktoken = None

# Model configuration
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384

# Chunking configuration
DEFAULT_CHUNK_SIZE = 500  # tokens
DEFAULT_CHUNK_OVERLAP = 50  # tokens


def _get_embedding_model():
    """Lazy load the sentence transformer model."""
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        print(f"Loading embedding model: {EMBEDDING_MODEL_NAME}")
        _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        print("Embedding model loaded successfully")
    return _embedding_model


def _get_fitz():
    """Lazy load PyMuPDF (fitz)."""
    global _fitz
    if _fitz is None:
        import fitz
        _fitz = fitz
    return _fitz


def _get_tiktoken():
    """Lazy load tiktoken for token counting."""
    global _tiktoken
    if _tiktoken is None:
        import tiktoken
        _tiktoken = tiktoken
    return _tiktoken


class RAGService:
    """
    RAG Service for document ingestion and embedding generation.
    Handles PDF parsing, text chunking, and vector embedding creation.
    """
    
    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP
    ):
        """
        Initialize the RAG service.
        
        Args:
            chunk_size: Maximum tokens per chunk
            chunk_overlap: Number of overlapping tokens between chunks
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._encoder = None
    
    def _get_token_encoder(self):
        """Get the tiktoken encoder for token counting."""
        if self._encoder is None:
            tiktoken = _get_tiktoken()
            # Use cl100k_base encoding (GPT-4 compatible)
            self._encoder = tiktoken.get_encoding("cl100k_base")
        return self._encoder
    
    def _count_tokens(self, text: str) -> int:
        """Count the number of tokens in a text string."""
        encoder = self._get_token_encoder()
        return len(encoder.encode(text))
    
    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """
        Extract text content from a PDF file.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Extracted text content
        """
        fitz = _get_fitz()
        
        text_content = []
        doc = fitz.open(pdf_path)
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            if text.strip():
                text_content.append(text)
        
        doc.close()
        return "\n\n".join(text_content)
    
    def extract_text_from_pdf_bytes(self, pdf_bytes: bytes) -> str:
        """
        Extract text content from PDF bytes.
        
        Args:
            pdf_bytes: PDF file as bytes
            
        Returns:
            Extracted text content
        """
        fitz = _get_fitz()
        
        text_content = []
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            if text.strip():
                text_content.append(text)
        
        doc.close()
        return "\n\n".join(text_content)
    
    def clean_text(self, text: str) -> str:
        """
        Clean extracted text by removing excessive whitespace and special characters.
        
        Args:
            text: Raw extracted text
            
        Returns:
            Cleaned text
        """
        # Replace multiple newlines with double newline
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Replace multiple spaces with single space
        text = re.sub(r' {2,}', ' ', text)
        
        # Remove leading/trailing whitespace from lines
        lines = [line.strip() for line in text.split('\n')]
        text = '\n'.join(lines)
        
        # Remove empty lines at start/end
        text = text.strip()
        
        return text
    
    def chunk_text(
        self,
        text: str,
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Split text into overlapping chunks based on token count.
        
        Args:
            text: Text to chunk
            chunk_size: Maximum tokens per chunk (default: 500)
            chunk_overlap: Overlap between chunks (default: 50)
            
        Returns:
            List of chunk dictionaries with text and metadata
        """
        chunk_size = chunk_size or self.chunk_size
        chunk_overlap = chunk_overlap or self.chunk_overlap
        
        encoder = self._get_token_encoder()
        
        # Clean the text first
        text = self.clean_text(text)
        
        # Split into paragraphs first (preserve structure)
        paragraphs = text.split('\n\n')
        
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
            
            para_tokens = len(encoder.encode(paragraph))
            
            # If single paragraph exceeds chunk size, split it by sentences
            if para_tokens > chunk_size:
                # Split paragraph into sentences
                sentences = re.split(r'(?<=[.!?])\s+', paragraph)
                for sentence in sentences:
                    sent_tokens = len(encoder.encode(sentence))
                    
                    if current_tokens + sent_tokens > chunk_size and current_chunk:
                        # Save current chunk
                        chunk_text = ' '.join(current_chunk)
                        chunks.append({
                            "text": chunk_text,
                            "token_count": current_tokens,
                            "index": len(chunks)
                        })
                        
                        # Start new chunk with overlap
                        # Keep last few items for overlap
                        overlap_text = chunk_text[-chunk_overlap * 4:]  # Approximate
                        current_chunk = [overlap_text] if overlap_text else []
                        current_tokens = len(encoder.encode(' '.join(current_chunk)))
                    
                    current_chunk.append(sentence)
                    current_tokens += sent_tokens
            else:
                # Check if adding this paragraph exceeds chunk size
                if current_tokens + para_tokens > chunk_size and current_chunk:
                    # Save current chunk
                    chunk_text = '\n\n'.join(current_chunk)
                    chunks.append({
                        "text": chunk_text,
                        "token_count": current_tokens,
                        "index": len(chunks)
                    })
                    
                    # Start new chunk with overlap from previous chunk
                    if chunk_overlap > 0 and current_chunk:
                        # Keep last paragraph for context
                        overlap_chunk = [current_chunk[-1]] if current_chunk else []
                        current_chunk = overlap_chunk
                        current_tokens = len(encoder.encode('\n\n'.join(current_chunk)))
                    else:
                        current_chunk = []
                        current_tokens = 0
                
                current_chunk.append(paragraph)
                current_tokens += para_tokens
        
        # Don't forget the last chunk
        if current_chunk:
            chunk_text = '\n\n'.join(current_chunk)
            chunks.append({
                "text": chunk_text,
                "token_count": self._count_tokens(chunk_text),
                "index": len(chunks)
            })
        
        return chunks
    
    def generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of texts.
        
        Args:
            texts: List of text strings to embed
            
        Returns:
            List of embedding vectors (384 dimensions each)
        """
        model = _get_embedding_model()
        embeddings = model.encode(texts, show_progress_bar=len(texts) > 10)
        return [emb.tolist() for emb in embeddings]
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text string to embed
            
        Returns:
            Embedding vector (384 dimensions)
        """
        model = _get_embedding_model()
        embedding = model.encode(text)
        return embedding.tolist()
    
    def generate_chunk_title(self, chunk_text: str, max_length: int = 100) -> str:
        """
        Generate a title for a chunk from its content.
        
        Args:
            chunk_text: The chunk text
            max_length: Maximum title length
            
        Returns:
            Generated title
        """
        # Take first sentence or first N characters
        first_line = chunk_text.split('\n')[0].strip()
        first_sentence = re.split(r'[.!?]', first_line)[0].strip()
        
        if len(first_sentence) > max_length:
            return first_sentence[:max_length-3] + "..."
        
        return first_sentence if first_sentence else chunk_text[:max_length]
    
    def process_pdf(
        self,
        pdf_bytes: bytes,
        filename: str,
        subject: str,
        language: str,
        tags: List[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Process a PDF file: extract text, chunk, and generate embeddings.
        
        Args:
            pdf_bytes: PDF file as bytes
            filename: Original filename
            subject: Subject category
            language: Content language
            tags: Optional tags for the content
            
        Returns:
            List of processed chunks ready for database insertion
        """
        tags = tags or []
        
        # Extract text
        print(f"Extracting text from: {filename}")
        raw_text = self.extract_text_from_pdf_bytes(pdf_bytes)
        
        if not raw_text.strip():
            raise ValueError(f"No text content found in PDF: {filename}")
        
        # Chunk the text
        print(f"Chunking text into ~{self.chunk_size} token chunks...")
        chunks = self.chunk_text(raw_text)
        print(f"Created {len(chunks)} chunks")
        
        # Generate embeddings for all chunks
        print("Generating embeddings...")
        chunk_texts = [chunk["text"] for chunk in chunks]
        embeddings = self.generate_embeddings(chunk_texts)
        print(f"Generated {len(embeddings)} embeddings")
        
        # Prepare documents for database
        documents = []
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            doc = {
                "title": self.generate_chunk_title(chunk["text"]),
                "content_chunk": chunk["text"],
                "subject": subject,
                "language": language,
                "vector_embedding": embedding,
                "tags": tags,
                "source_file": filename,
                "chunk_index": i
            }
            documents.append(doc)
        
        return documents
    
    def get_info(self) -> Dict[str, Any]:
        """Get information about the RAG service configuration."""
        return {
            "embedding_model": EMBEDDING_MODEL_NAME,
            "embedding_dimension": EMBEDDING_DIMENSION,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "model_loaded": _embedding_model is not None
        }


# Singleton instance
rag_service = RAGService()


# Test function
def test_rag_service():
    """Test the RAG service with sample text."""
    print("=" * 60)
    print("Testing RAG Service")
    print("=" * 60)
    
    service = RAGService()
    
    # Test 1: Service info
    print("\n1. Service Information:")
    info = service.get_info()
    for key, value in info.items():
        print(f"   {key}: {value}")
    
    # Test 2: Text chunking
    print("\n2. Testing text chunking...")
    sample_text = """
    Photosynthesis is the process by which plants convert light energy into chemical energy.
    This process occurs in the chloroplasts of plant cells, specifically in the thylakoid membranes.
    
    The basic equation for photosynthesis is:
    6CO2 + 6H2O + light energy → C6H12O6 + 6O2
    
    This means that carbon dioxide and water, in the presence of light, are converted into glucose and oxygen.
    The glucose is used by the plant for energy and growth, while oxygen is released into the atmosphere.
    
    There are two main stages of photosynthesis:
    1. Light-dependent reactions - occur in the thylakoid membranes
    2. Light-independent reactions (Calvin cycle) - occur in the stroma
    
    Plants are essential for life on Earth because they produce oxygen and form the base of most food chains.
    """
    
    chunks = service.chunk_text(sample_text, chunk_size=100, chunk_overlap=10)
    print(f"   Created {len(chunks)} chunks from sample text")
    for i, chunk in enumerate(chunks):
        print(f"   Chunk {i+1}: {chunk['token_count']} tokens - '{chunk['text'][:50]}...'")
    
    # Test 3: Embedding generation
    print("\n3. Testing embedding generation...")
    test_texts = [
        "What is photosynthesis?",
        "How do plants make food?",
        "Newton's first law of motion"
    ]
    embeddings = service.generate_embeddings(test_texts)
    print(f"   Generated {len(embeddings)} embeddings")
    print(f"   Embedding dimension: {len(embeddings[0])}")
    
    # Test 4: Single embedding
    print("\n4. Testing single embedding...")
    single_emb = service.generate_embedding("Explain the water cycle")
    print(f"   Single embedding dimension: {len(single_emb)}")
    
    print("\n" + "=" * 60)
    print("RAG Service test completed!")
    print("=" * 60)


if __name__ == "__main__":
    test_rag_service()
