import re
from collections import Counter
from typing import List, Dict

class DocumentProcessor:
    def __init__(self):
        # Expanded stop words list
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'should', 'could', 'may', 'might', 'must', 'can', 'this', 'that',
            'these', 'those', 'it', 'its', 'they', 'them', 'their'
        }

    def chunk_markdown(self, text: str, chunk_size: int = 500, overlap: int = 100) -> List[str]:
        """Optimized markdown chunking with smart boundary detection."""
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        # Validate parameters
        if chunk_size <= 0: raise ValueError("chunk_size must be positive")
        if overlap < 0: raise ValueError("overlap must be non-negative")
        if overlap >= chunk_size: raise ValueError("overlap must be smaller than chunk_size")

        chunks = []
        start = 0
        text_len = len(text)
        
        while start < text_len:
            end = min(start + chunk_size, text_len)
            if end < text_len:
                search_start = max(end - 50, start)
                search_end = min(end + 50, text_len)
                window = text[search_start:search_end]
                for pattern in (r'\n\n', r'[.!?]\s', r'\s'):
                    matches = list(re.finditer(pattern, window))
                    if matches:
                        closest = min(matches, key=lambda m: abs((search_start + m.end()) - end))
                        end = search_start + closest.end()
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            start = end - overlap
            if end >= text_len or start >= text_len:
                break
        return chunks

    def tokenize(self, text: str) -> List[str]:
        """Optimized tokenization with single-pass processing."""
        tokens = re.findall(r'\b[a-z]{3,}\b', text.lower())
        return [t for t in tokens if t not in self.stop_words]

    def calculate_tf_batch(self, token_lists: List[List[str]]) -> List[Dict[str, float]]:
        """Batch calculate term frequencies for multiple chunks."""
        return [
            {term: count / len(tokens) for term, count in Counter(tokens).items()}
            if tokens else {}
            for tokens in token_lists
        ]
