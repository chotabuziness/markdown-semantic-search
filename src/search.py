import os
import math
from collections import Counter
from typing import List, Tuple

from .database import DatabaseManager
from .processor import DocumentProcessor
from .downloader import Downloader

class SearchService:
    def __init__(self, db_path: str = ":memory:"):
        self.db = DatabaseManager(db_path)
        self.processor = DocumentProcessor()
        self.downloader = Downloader()

    def add_markdown_file(self, file_path: str, chunk_size: int = 500, overlap: int = 100, mode: str = 'replace'):
        """Optimized bulk insertion of markdown content with progress tracking.
        
        Args:
            file_path: Path to the markdown file
            chunk_size: Size of each chunk in characters
            overlap: Overlap between chunks
            mode: 'replace' (default) - delete existing records for this file first
                  'skip' - if file exists, do nothing
                  'append' - add records without checking (may cause duplicates)
        """
        # Handle existing entries based on mode
        if mode == 'skip':
            if self.db.file_exists(file_path):
                print(f"⏩ Skipping {file_path} (already indexed)")
                return False
        elif mode == 'replace':
            self.db.delete_file(file_path)
        
        print(f"📖 Processing {file_path}...")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"📝 Chunking document ({len(content):,} characters)...")
        chunks = self.processor.chunk_markdown(content, chunk_size, overlap)
        print(f"✂️  Created {len(chunks)} chunks")
        
        # Batch tokenization
        print(f"🔤 Tokenizing chunks...")
        token_lists = []
        for i, chunk in enumerate(chunks):
            if i % 10 == 0 or i == len(chunks) - 1:
                print(f"   Progress: {i+1}/{len(chunks)} chunks tokenized", end='\r')
            token_lists.append(self.processor.tokenize(chunk))
        print()
        
        print(f"📊 Calculating TF scores...")
        tf_scores_batch = self.processor.calculate_tf_batch(token_lists)
        
        print(f"💾 Inserting chunks into database...")
        chunk_ids = []
        for i, (chunk, tokens) in enumerate(zip(chunks, token_lists)):
            if i % 10 == 0 or i == len(chunks) - 1:
                print(f"   Progress: {i+1}/{len(chunks)} chunks inserted", end='\r')
            cid = self.db.insert_chunk((file_path, chunk, i, len(tokens)))
            chunk_ids.append(cid)
        print()
        
        # Bulk insert TF scores
        print(f"🔢 Building TF-IDF vectors...")
        tfidf_data = []
        for chunk_id, tf_scores in zip(chunk_ids, tf_scores_batch):
            for term, tf in tf_scores.items():
                tfidf_data.append((chunk_id, term, tf, tf))
        
        if tfidf_data:
            print(f"💾 Inserting {len(tfidf_data):,} TF-IDF vectors...")
            batch_size = 1000
            for i in range(0, len(tfidf_data), batch_size):
                batch = tfidf_data[i:i + batch_size]
                self.db.insert_tfidf_vectors(batch)
                progress = min(i + batch_size, len(tfidf_data))
                print(f"   Progress: {progress:,}/{len(tfidf_data):,} vectors inserted", end='\r')
            print()
        
        print(f"🧮 Updating IDF scores...")
        total_docs = self.db.get_total_docs()
        self.db.update_idf_and_tfidf(total_docs)
        
        print(f"✅ Successfully added {len(chunks)} chunks from {file_path}")
        
        try:
            os.remove(file_path)
            print(f"🗑️  Deleted {file_path}")
        except OSError as e:
            print(f"⚠️  Could not delete {file_path}: {e}")

    def search(self, query: str, top_k: int = 5) -> List[Tuple[str, float, str]]:
        """Optimized search using SQL-based vector operations."""
        query_tokens = self.processor.tokenize(query)
        if not query_tokens:
            return []
        
        query_tf = {term: count / len(query_tokens) for term, count in Counter(query_tokens).items()}
        query_tfidf_res = self.db.get_query_tfidf(list(query_tf.keys()))
        
        query_vector = {term: query_tf[term] * idf for term, idf in query_tfidf_res}
        return self.db.search_chunks(query_vector, top_k)

    def download_markdown_from_url(self, url: str) -> Tuple[str, str]:
        return self.downloader.download_markdown_from_url(url)

    def get_stats(self) -> dict:
        return self.db.get_stats()

    def close(self):
        self.db.close()
