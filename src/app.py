import time
import shutil
import os
import glob
from typing import List
from .search import SearchService

class MarkdownSearchApp:
    """Core application logic for Markdown Semantic Search."""
    
    def __init__(self, db_name: str = "knowledge_base.db"):
        if not db_name.endswith(".db"):
            db_name += ".db"
        self.db_name = db_name
        self.search_service = SearchService(self.db_name)

    def process_inputs(self, inputs: List[str], mode: str = 'replace') -> int:
        """Process a list of URLs, files, or directories."""
        if not inputs:
            print("\n⚠️  No input provided.")
            return 0

        start = time.time()
        loaded_count = 0
        
        # Expanded files list to handle directories
        files_to_process = []
        for path in inputs:
            if path.startswith(('http://', 'https://')):
                files_to_process.append(('url', path))
            elif os.path.isdir(path):
                print(f"📂 Scanning directory: {path}")
                md_files = glob.glob(os.path.join(path, "**", "*.md"), recursive=True)
                print(f"   Found {len(md_files)} markdown files")
                for f in md_files:
                    files_to_process.append(('file', f))
            elif os.path.exists(path):
                files_to_process.append(('file', path))
            else:
                print(f"❌ Path not found: {path}")

        for type, path in files_to_process:
            try:
                if type == 'url':
                    filename, content = self.search_service.download_markdown_from_url(path)
                    if filename and content:
                        with open(filename, "w", encoding='utf-8') as f:
                            f.write(content)
                        self.search_service.add_markdown_file(filename, mode=mode)
                        loaded_count += 1
                else:
                    filename = os.path.basename(path)
                    temp_filename = f"temp_{int(time.time()*1000)}_{filename}"
                    shutil.copy2(path, temp_filename)
                    if self.search_service.add_markdown_file(temp_filename, mode=mode) is not False:
                        loaded_count += 1
                    else:
                        try:
                            os.remove(temp_filename)
                        except:
                            pass
            except Exception as e:
                print(f"❌ Failed to load {path}: {e}")
        
        load_time = time.time() - start
        if loaded_count > 0:
            print(f"\n⏱️  Processed {loaded_count} documents in {load_time:.3f}s")
        return loaded_count

    def perform_search(self, query: str, top_k: int = 3):
        """Execute a search query and display results."""
        start = time.time()
        results = self.search_service.search(query, top_k=top_k)
        search_time = time.time() - start
        
        print(f"\n🔍 Query: '{query}' ({search_time*1000:.2f}ms)\n")
        if results:
            for i, (text, score, source) in enumerate(results, 1):
                print(f"  {i}. Score: {score:.4f} | {source}")
                print(f"     {text[:150]}...")
                print()
        else:
            print("  No results found.")

    def get_stats(self) -> dict:
        """Get database statistics."""
        return self.search_service.get_stats()

    def print_stats(self):
        """Print formatted database statistics."""
        stats = self.get_stats()
        if stats['files'] == 0:
            print(f"\n⚠️  Database '{self.db_name}' is empty.")
        else:
            print(f"\n📊 Knowledge Base Stats ({self.db_name}):")
            print(f"   Files: {stats['files']}")
            print(f"   Chunks: {stats['chunks']}")
            print(f"   Avg tokens/chunk: {stats['avg_tokens']}")
            print(f"   Unique terms: {stats['unique_terms']}")

    def close(self):
        """Close the search service."""
        self.search_service.close()
