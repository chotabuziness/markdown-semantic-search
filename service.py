import duckdb
import re
from typing import List, Tuple, Dict
from collections import Counter
import math

class MarkdownSemanticSearch:
    def __init__(self, db_path: str = ":memory:"):
        """Initialize DuckDB connection and create optimized tables."""
        self.conn = duckdb.connect(db_path)
        self._create_tables()
        
    def _create_tables(self):
        """Create optimized tables with proper indexing."""
        self.conn.execute("""
            CREATE SEQUENCE IF NOT EXISTS chunks_seq START 1
        """)
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                id BIGINT PRIMARY KEY DEFAULT nextval('chunks_seq'),
                source_file VARCHAR,
                chunk_text TEXT,
                chunk_index INTEGER,
                token_count INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Optimized TF-IDF storage with materialized aggregations
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS tfidf_vectors (
                chunk_id BIGINT,
                term VARCHAR,
                tf DOUBLE,
                tfidf DOUBLE,
                PRIMARY KEY (chunk_id, term),
                FOREIGN KEY (chunk_id) REFERENCES chunks(id)
            )
        """)
        
        # Pre-computed IDF scores for fast query processing
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS idf_scores (
                term VARCHAR PRIMARY KEY,
                doc_frequency INTEGER,
                idf_score DOUBLE
            )
        """)
        
        # Indexes for fast retrieval
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_term ON tfidf_vectors(term)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_chunk ON tfidf_vectors(chunk_id)")
   
    def chunk_markdown(self, text: str, chunk_size: int = 500, 
                       overlap: int = 100) -> List[str]:
        """
        Optimized markdown chunking with smart boundary detection.
        """
        # Normalize whitespace in one pass
        text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
        
        # Validate parameters
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if overlap < 0:
            raise ValueError("overlap must be non-negative")
        if overlap >= chunk_size:
            raise ValueError("overlap must be smaller than chunk_size")

        chunks = []
        start = 0
        text_len = len(text)
        
        while start < text_len:
            end = min(start + chunk_size, text_len)
            
            # Smart boundary detection if not at end
            if end < text_len:
                # Search window for natural break
                search_start = max(end - 50, start)
                search_end = min(end + 50, text_len)
                window = text[search_start:search_end]
                
                # Priority: paragraph > sentence > word
                for pattern in (r'\n\n', r'[.!?]\s', r'\s'):
                    matches = list(re.finditer(pattern, window))
                    if matches:
                        # Find closest match to target end using match end (robust)
                        closest = min(matches, key=lambda m: abs((search_start + m.end()) - end))
                        end = search_start + closest.end()
                        break
            
            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)
            # Advance start using overlap; stop if we've reached the end
            start = end - overlap
            if end >= text_len or start >= text_len:
                break
        
        return chunks
    
    def _tokenize(self, text: str) -> List[str]:
        """Optimized tokenization with single-pass processing."""
        # Expanded stop words list
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
            'should', 'could', 'may', 'might', 'must', 'can', 'this', 'that',
            'these', 'those', 'it', 'its', 'they', 'them', 'their'
        }
        
        # Single pass: lowercase + tokenize + filter
        tokens = re.findall(r'\b[a-z]{3,}\b', text.lower())
        return [t for t in tokens if t not in stop_words]
    
    def _calculate_tf_batch(self, token_lists: List[List[str]]) -> List[Dict[str, float]]:
        """Batch calculate term frequencies for multiple chunks."""
        return [
            {term: count / len(tokens) for term, count in Counter(tokens).items()}
            if tokens else {}
            for tokens in token_lists
        ]
    
    def add_markdown_file(self, file_path: str, chunk_size: int = 500, 
                          overlap: int = 100):
        """
        Optimized bulk insertion of markdown content.
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        chunks = self.chunk_markdown(content, chunk_size, overlap)
        
        # Batch tokenization
        token_lists = [self._tokenize(chunk) for chunk in chunks]
        tf_scores_batch = self._calculate_tf_batch(token_lists)
        
        chunk_data = [
            (file_path, chunk, idx, len(tokens))
            for idx, (chunk, tokens) in enumerate(zip(chunks, token_lists))
        ]
        
        chunk_ids = []
        for data in chunk_data:
            result = self.conn.execute("""
                INSERT INTO chunks (source_file, chunk_text, chunk_index, token_count)
                VALUES (?, ?, ?, ?)
                RETURNING id
            """, data).fetchone()
            chunk_ids.append(result)
        
        # Bulk insert TF scores
        tfidf_data = []
        for chunk_id, tf_scores in zip(chunk_ids, tf_scores_batch):
            for term, tf in tf_scores.items():
                tfidf_data.append((chunk_id[0], term, tf, tf))  # Initial tfidf = tf
        
        if tfidf_data:
            self.conn.executemany("""
                INSERT INTO tfidf_vectors (chunk_id, term, tf, tfidf)
                VALUES (?, ?, ?, ?)
            """, tfidf_data)
        
        # Recalculate IDF in bulk
        self._update_idf_scores()
        
        print(f"✓ Added {len(chunks)} chunks from {file_path}")
    
    def _update_idf_scores(self):
        """Optimized IDF calculation using SQL aggregation."""
        total_docs = self.conn.execute(
            "SELECT COUNT(*) FROM chunks"
        ).fetchone()[0]
        
        if total_docs == 0:
            return
        
        # Calculate and store IDF scores in one query
        self.conn.execute("""
            INSERT OR REPLACE INTO idf_scores (term, doc_frequency, idf_score)
            SELECT 
                term,
                COUNT(DISTINCT chunk_id) as doc_freq,
                LN(? / COUNT(DISTINCT chunk_id)) as idf
            FROM tfidf_vectors
            GROUP BY term
        """, [total_docs])
        
        # Update TF-IDF scores using vectorized operation
        self.conn.execute("""
            UPDATE tfidf_vectors
            SET tfidf = tf * (
                SELECT idf_score FROM idf_scores WHERE idf_scores.term = tfidf_vectors.term
            )
        """)
    
    def search(self, query: str, top_k: int = 5) -> List[Tuple[str, float, str]]:
        """
        Optimized search using SQL-based vector operations.
        """
        # Tokenize query
        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []
        
        # Calculate query TF
        query_tf = {term: count / len(query_tokens) 
                    for term, count in Counter(query_tokens).items()}
        
        # Get query TF-IDF using pre-computed IDF
        query_tfidf = self.conn.execute("""
            SELECT term, idf_score
            FROM idf_scores
            WHERE term IN ({})
        """.format(','.join('?' * len(query_tokens))), list(query_tf.keys())).fetchall()
        
        query_vector = {term: query_tf[term] * idf for term, idf in query_tfidf}
        
        if not query_vector:
            return []
        
        # Calculate query magnitude
        query_mag = math.sqrt(sum(v**2 for v in query_vector.values()))
        
        # Simplified similarity calculation
        placeholders = ','.join('?' * len(query_vector))
        params = list(query_vector.keys()) + [query_mag, top_k]
        
        results = self.conn.execute(f"""
            WITH chunk_scores AS (
                SELECT 
                    tv.chunk_id,
                    SUM(tv.tfidf) as dot_product,
                    SQRT(SUM(tv.tfidf * tv.tfidf)) as chunk_magnitude
                FROM tfidf_vectors tv
                WHERE tv.term IN ({placeholders})
                GROUP BY tv.chunk_id
            )
            SELECT 
                c.chunk_text,
                cs.dot_product / (? * cs.chunk_magnitude) as similarity,
                c.source_file
            FROM chunk_scores cs
            JOIN chunks c ON c.id = cs.chunk_id
            WHERE cs.chunk_magnitude > 0
            ORDER BY similarity DESC
            LIMIT ?
        """, params).fetchall()
        
        return results
    
    def get_stats(self) -> dict:
        """Get knowledge base statistics."""
        stats = self.conn.execute("""
            SELECT 
                COUNT(DISTINCT source_file) as num_files,
                COUNT(*) as num_chunks,
                AVG(token_count) as avg_tokens_per_chunk,
                (SELECT COUNT(*) FROM idf_scores) as unique_terms
            FROM chunks
        """).fetchone()
        
        return {
            'files': stats[0],
            'chunks': stats[1],
            'avg_tokens': round(stats[2], 2) if stats[2] else 0,
            'unique_terms': stats[3]
        }
    
    def close(self):
        """Close database connection."""
        self.conn.close()
