import time
import shutil
import os
import glob

from src import SearchService

def get_existing_databases():
    """List all .db files in the current directory."""
    return glob.glob("*.db")

def select_database(existing_dbs):
    """Prompt user to select an existing database or create a new one."""
    print("\n📂 Available Databases:")
    for i, db in enumerate(existing_dbs, 1):
        print(f"   {i}. {db}")
    
    while True:
        try:
            choice = input("\nSelect a database number (or press Enter for 'knowledge_base.db'): ").strip()
            if not choice:
                return "knowledge_base.db"
            
            idx = int(choice) - 1
            if 0 <= idx < len(existing_dbs):
                return existing_dbs[idx]
            print("❌ Invalid selection. Please try again.")
        except ValueError:
            # If they typed a name instead of a number
            if not choice.endswith(".db"):
                choice += ".db"
            return choice

def main():
    print("="*80)
    print("🤖 MARKDOWN SEMANTIC SEARCH")
    print("="*80)

    existing_dbs = get_existing_databases()
    
    print("\nWhat would you like to do?")
    print("1. 🔍 Search an existing database")
    print("2. 🏗️  Process new documents (replace existing)")
    print("3. ➕ Incremental Add (skip already indexed)")
    
    while True:
        mode = input("\nSelect option (1, 2, or 3): ").strip()
        if mode in ['1', '2', '3']:
            break
        print("❌ Invalid option. Please enter 1, 2, or 3.")

    if mode == '1':
        if not existing_dbs:
            print("\n⚠️  No existing databases found. Switching to processing mode.")
            mode = '2'
            db_name = "knowledge_base.db"
        else:
            db_name = select_database(existing_dbs)
    else:
        db_name = input(f"\nEnter database name to {'update' if mode == '2' else 'incrementally update'} (default: 'knowledge_base.db'): ").strip()
        if not db_name:
            db_name = "knowledge_base.db"
        if not db_name.endswith(".db"):
            db_name += ".db"

    # Initialize search system
    search = SearchService(db_name)
    
    # Logic for processing new documents
    if mode in ['2', '3']:
        update_mode = 'replace' if mode == '2' else 'skip'
        print(f"\n📚 {'REPLACE' if update_mode == 'replace' else 'INCREMENTAL'} MODE")
        print("Enter URLs, local file paths, or directories (one per line, empty line to finish):")
        inputs = []
        while True:
            path = input("URL/Path/Dir: ").strip()
            if not path:
                break
            inputs.append(path)
        
        if inputs:
            start = time.time()
            loaded_count = 0
            
            # Expanded files list to handle directories
            files_to_process = []
            for path in inputs:
                if path.startswith(('http://', 'https://')):
                    files_to_process.append(('url', path))
                elif os.path.isdir(path):
                    # Recursive search for markdown files
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
                        filename, content = search.download_markdown_from_url(path)
                        if filename and content:
                            with open(filename, "w", encoding='utf-8') as f:
                                f.write(content)
                            search.add_markdown_file(filename, chunk_size=500, overlap=100, mode=update_mode)
                            loaded_count += 1
                    else:
                        filename = os.path.basename(path)
                        # Create a temporary copy to avoid modifying original if add_markdown_file deletes it
                        # Note: search.add_markdown_file deletes the file after processing
                        temp_filename = f"temp_{int(time.time()*1000)}_{filename}"
                        shutil.copy2(path, temp_filename)
                        if search.add_markdown_file(temp_filename, chunk_size=500, overlap=100, mode=update_mode) is not False:
                            loaded_count += 1
                        else:
                            # If skipped, cleanup the temp file
                            try:
                                os.remove(temp_filename)
                            except:
                                pass
                except Exception as e:
                    print(f"❌ Failed to load {path}: {e}")
            
            load_time = time.time() - start
            print(f"\n⏱️  Processed {loaded_count} documents in {load_time:.3f}s")
        else:
            print("\n⚠️  No input provided.")

    # Always show stats and enter search loop
    stats = search.get_stats()
    if stats['files'] == 0:
        print(f"\n⚠️  Database '{db_name}' is empty.")
        if mode == '1':
            print("Please run in processing mode (option 2) to add documents.")
            search.close()
            return
    else:
        print(f"\n📊 Knowledge Base Stats ({db_name}):")
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

if __name__ == "__main__":
    main()