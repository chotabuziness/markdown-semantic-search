import time

from service import MarkdownSemanticSearch

# Initialize search system
search = MarkdownSemanticSearch("knowledge_base.db")

# Sample markdown documents
sample_docs = {
    "python_guide.md": """
# Python Programming Guide

## Introduction to Python
Python is a high-level programming language known for its simplicity and readability.
It supports multiple programming paradigms including procedural, object-oriented, and functional programming.

## Data Structures
Python provides several built-in data structures like lists, dictionaries, sets, and tuples.
These data structures are fundamental to writing efficient Python code.

### Lists
Lists are ordered, mutable collections that can contain elements of different types.
You can perform operations like append, insert, and remove on lists.

### Dictionaries
Dictionaries store key-value pairs and provide fast lookup times.
They are implemented using hash tables internally.

## Functions and Modules
Functions help organize code into reusable blocks.
Modules allow you to organize related functions and classes together.
Python's import system makes it easy to reuse code across projects.
""",
        "database_guide.md": """
# Database Systems Guide

## Introduction to Databases
Databases are organized collections of structured information or data.
They are essential for storing and retrieving information efficiently.

## SQL vs NoSQL
SQL databases use structured query language and relational tables.
NoSQL databases offer flexible schemas and horizontal scaling.

### DuckDB
DuckDB is an embedded analytical database management system.
It provides fast analytical queries without requiring a separate server.
DuckDB integrates directly into Python applications.

## Query Optimization
Query optimization improves database performance significantly.
Proper indexing and query planning are crucial for fast retrieval.
"""
}

# Add documents
start = time.time()
for filename, content in sample_docs.items():
    with open(filename, "w") as f:
        f.write(content)
    search.add_markdown_file(filename, chunk_size=200, overlap=50)

load_time = time.time() - start
print(f"\n⏱️  Loaded documents in {load_time:.3f}s")

# Display stats
stats = search.get_stats()
print(f"\n📊 Knowledge Base Stats:")
print(f"   Files: {stats['files']}")
print(f"   Chunks: {stats['chunks']}")
print(f"   Avg tokens/chunk: {stats['avg_tokens']}")
print(f"   Unique terms: {stats['unique_terms']}")

# Search examples
queries = [
    "how to organize code in python",
    "fast database queries",
    "python data structures"
]

print("\n" + "="*80)
print("🔍 SEMANTIC SEARCH RESULTS")
print("="*80)

for query in queries:
    start = time.time()
    results = search.search(query, top_k=3)
    search_time = time.time() - start
    
    print(f"\nQuery: '{query}' ({search_time*1000:.2f}ms)\n")
    
    for i, (text, score, source) in enumerate(results, 1):
        print(f"  {i}. Score: {score:.4f} | {source}")
        print(f"     {text[:150]}...")
        print()

search.close()
print("✓ Done!")