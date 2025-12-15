import time

from service import MarkdownSemanticSearch

# Initialize search system
search = MarkdownSemanticSearch("knowledge_base.db")

# Check if documents already exist
stats = search.get_stats()
if stats['files'] == 0:
    print("\n📚 No documents found in database. Please add markdown files.")
    print("Enter URLs to markdown files (one per line, empty line to finish):")
    
    urls = []
    while True:
        url = input("URL: ").strip()
        if not url:
            break
        urls.append(url)
    
    if urls:
        start = time.time()
        loaded_count = 0
        
        for url in urls:
            filename, content = search.download_markdown_from_url(url)
            if filename and content:
                with open(filename, "w", encoding='utf-8') as f:
                    f.write(content)
                search.add_markdown_file(filename, chunk_size=500, overlap=100)
                loaded_count += 1
        
        load_time = time.time() - start
        print(f"\n⏱️  Loaded {loaded_count} documents in {load_time:.3f}s")
    else:
        print("\n⚠️  No URLs provided. Database remains empty.")
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