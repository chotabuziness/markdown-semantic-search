import time
import shutil
import os

from service import MarkdownSemanticSearch

# Get custom database name
db_name = input("Enter database name (or press Enter for 'knowledge_base.db'): ").strip()
if not db_name:
    db_name = "knowledge_base.db"
if not db_name.endswith(".db"):
    db_name += ".db"

# Initialize search system
search = MarkdownSemanticSearch(db_name)

# Check if documents already exist
stats = search.get_stats()
if stats['files'] == 0:
    print("\n📚 No documents found in database. Please add markdown files.")
    print("Enter URLs or local file paths (one per line, empty line to finish):")
    
    inputs = []
    while True:
        path = input("URL/Path: ").strip()
        if not path:
            break
        inputs.append(path)
    
    if inputs:
        start = time.time()
        loaded_count = 0
        
        for path in inputs:
            if path.startswith(('http://', 'https://')):
                # Handle URL
                filename, content = search.download_markdown_from_url(path)
                if filename and content:
                    with open(filename, "w", encoding='utf-8') as f:
                        f.write(content)
                    search.add_markdown_file(filename, chunk_size=500, overlap=100)
                    loaded_count += 1
            else:
                # Handle local file
                try:
                    # Copy local file to current directory
                    filename = os.path.basename(path)
                    shutil.copy2(path, filename)
                    search.add_markdown_file(filename, chunk_size=500, overlap=100)
                    loaded_count += 1
                except Exception as e:
                    print(f"❌ Failed to load {path}: {e}")
        
        load_time = time.time() - start
        print(f"\n⏱️  Loaded {loaded_count} documents in {load_time:.3f}s")
    else:
        print("\n⚠️  No files provided. Database remains empty.")
else:
    print(f"\n📚 Using existing {stats['files']} documents in database")

# Display stats
stats = search.get_stats()
print(f"\n📊 Knowledge Base Stats:")
print(f"   Files: {stats['files']}")
print(f"   Chunks: {stats['chunks']}")
print(f"   Avg tokens/chunk: {stats['avg_tokens']}")
print(f"   Unique terms: {stats['unique_terms']}")

print("\n" + "="*80)
print("🔍 SEMANTIC SEARCH - Enter your queries (type 'quit' to exit)")
print("="*80)

while True:
    query = input("\nEnter your search query (or 'quit/exit/q' to exit): ").strip()
    
    if query.lower() in ['quit', 'exit', 'q']:
        break
    
    if not query:
        continue
    
    start = time.time()
    results = search.search(query, top_k=3)
    search_time = time.time() - start
    
    print(f"\nQuery: '{query}' ({search_time*1000:.2f}ms)\n")
    
    if results:
        for i, (text, score, source) in enumerate(results, 1):
            print(f"  {i}. Score: {score:.4f} | {source}")
            print(f"     {text[:150]}...")
            print()
    else:
        print("  No results found.")

search.close()
print("\n✓ Done!")