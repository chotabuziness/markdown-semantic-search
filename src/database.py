import duckdb
import math

class DatabaseManager:
    def __init__(self, db_path: str = ":memory:"):
        """Initialize DuckDB connection and create optimized tables."""
        self.conn = duckdb.connect(db_path)
        self._create_tables()
        
    def _create_tables(self):
        """Create optimized tables with proper indexing."""
        self.conn.execute("CREATE SEQUENCE IF NOT EXISTS chunks_seq START 1")
        
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
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS idf_scores (
                term VARCHAR PRIMARY KEY,
                doc_frequency INTEGER,
                idf_score DOUBLE
            )
        """)
        
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_term ON tfidf_vectors(term)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_chunk ON tfidf_vectors(chunk_id)")

    def insert_chunk(self, data: tuple) -> int:
        """Insert a single chunk and return its ID."""
        return self.conn.execute("""
            INSERT INTO chunks (source_file, chunk_text, chunk_index, token_count)
            VALUES (?, ?, ?, ?)
            RETURNING id
        """, data).fetchone()[0]

    def delete_file(self, source_file: str):
        """Remove all chunks and related TF-IDF vectors for a specific file."""
        # Get chunk IDs for this file
        chunk_ids = self.conn.execute(
            "SELECT id FROM chunks WHERE source_file = ?", [source_file]
        ).fetchall()
        
        if chunk_ids:
            ids = [row[0] for row in chunk_ids]
            # Delete TF-IDF vectors first (due to foreign key)
            self.conn.execute(
                f"DELETE FROM tfidf_vectors WHERE chunk_id IN ({','.join(['?']*len(ids))})", 
                ids
            )
            # Delete chunks
            self.conn.execute(
                "DELETE FROM chunks WHERE source_file = ?", [source_file]
            )
            print(f"🧹 Cleared existing data for {source_file}")

    def insert_tfidf_vectors(self, tfidf_data: list):
        """Bulk insert TF-IDF vectors."""
        self.conn.executemany("""
            INSERT INTO tfidf_vectors (chunk_id, term, tf, tfidf)
            VALUES (?, ?, ?, ?)
        """, tfidf_data)

    def get_total_docs(self) -> int:
        """Get total number of chunks."""
        return self.conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]

    def file_exists(self, source_file: str) -> bool:
        """Check if a file is already indexed in the database."""
        result = self.conn.execute(
            "SELECT 1 FROM chunks WHERE source_file = ? LIMIT 1", [source_file]
        ).fetchone()
        return result is not None

    def update_idf_and_tfidf(self, total_docs: int):
        """Update IDF scores and TF-IDF vectors in bulk."""
        self.conn.execute("""
            INSERT OR REPLACE INTO idf_scores (term, doc_frequency, idf_score)
            SELECT 
                term,
                COUNT(DISTINCT chunk_id) as doc_freq,
                LN((1.0 + ?) / COUNT(DISTINCT chunk_id)) + 1.0 as idf
            FROM tfidf_vectors
            GROUP BY term
        """, [total_docs])
        
        self.conn.execute("""
            UPDATE tfidf_vectors
            SET tfidf = tf * (
                SELECT idf_score FROM idf_scores WHERE idf_scores.term = tfidf_vectors.term
            )
        """)

    def get_query_tfidf(self, terms: list) -> list:
        """Get IDF scores for query terms."""
        placeholders = ','.join('?' * len(terms))
        return self.conn.execute(f"""
            SELECT term, idf_score
            FROM idf_scores
            WHERE term IN ({placeholders})
        """, terms).fetchall()

    def search_chunks(self, query_vector: dict, top_k: int) -> list:
        """Execute semantic search query with proper dot product logic."""
        if not query_vector:
            return []
            
        terms = list(query_vector.keys())
        query_mag = math.sqrt(sum(v**2 for v in query_vector.values()))
        
        # Build a temporary table or use a case statement for query weights
        placeholders = ', '.join(['?'] * len(terms))
        
        # We can use a CASE statement to inject query weights into the SQL
        weight_cases = " ".join([f"WHEN tv.term = ? THEN {weight}" for term, weight in query_vector.items()])
        
        params = terms + [query_mag, top_k]
        
        return self.conn.execute(f"""
            WITH chunk_scores AS (
                SELECT 
                    tv.chunk_id,
                    SUM(tv.tfidf * (CASE {weight_cases} END)) as dot_product,
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
        """, list(query_vector.keys()) + params).fetchall()

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
