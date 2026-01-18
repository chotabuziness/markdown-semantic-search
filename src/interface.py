import argparse
import glob
from typing import List, Optional
from .app import MarkdownSearchApp

class InteractiveSession:
    """Manages the interactive wizard UI."""
    
    def __init__(self, app: Optional[MarkdownSearchApp] = None):
        self.app = app

    def _get_existing_databases(self):
        dbs = glob.glob("*.db")
        dbs.extend(glob.glob("knowledge/*.db"))
        return sorted(list(set(dbs)))

    def _select_database(self, existing_dbs: List[str]) -> str:
        if existing_dbs:
            print("\n📂 Available Databases:")
            for i, db in enumerate(existing_dbs, 1):
                print(f"   {i}. {db}")
        
        while True:
            prompt = "\nSelect a database number" if existing_dbs else "\nEnter database path"
            choice = input(f"{prompt} (or press Enter for 'knowledge_base.db'): ").strip()
            
            if not choice:
                return "knowledge_base.db"
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(existing_dbs):
                    return existing_dbs[idx]
            except ValueError:
                if not choice.endswith(".db"):
                    choice += ".db"
                return choice
            print("❌ Invalid selection. Please try again.")

    def run(self):
        """Start the interactive session."""
        print("="*80)
        print("🤖 MARKDOWN SEMANTIC SEARCH")
        print("="*80)

        existing_dbs = self._get_existing_databases()
        
        print("\nWhat would you like to do?")
        print("1. 🤖 Ask a question from existing database")
        print("2. 🏗️  Process new documents (replace existing)")
        print("3. ➕ Incremental Add (skip already indexed)")
        
        while True:
            mode_choice = input("\nSelect option (1, 2, or 3): ").strip()
            if mode_choice in ['1', '2', '3']:
                break
            print("❌ Invalid option. Please enter 1, 2, or 3.")

        if mode_choice == '1':
            db_name = self._select_database(existing_dbs)
        else:
            prompt = f"\nEnter database name to {'update' if mode_choice == '2' else 'incrementally update'} (default: 'knowledge_base.db'): "
            db_name = input(prompt).strip() or "knowledge_base.db"

        self.app = MarkdownSearchApp(db_name)
        
        if mode_choice in ['2', '3']:
            update_mode = 'replace' if mode_choice == '2' else 'skip'
            print(f"\n📚 {'REPLACE' if update_mode == 'replace' else 'INCREMENTAL'} MODE")
            print("Enter URLs, local file paths, or directories (one per line, empty line to finish):")
            inputs = []
            while True:
                path = input("URL/Path/Dir: ").strip()
                if not path:
                    break
                inputs.append(path)
            self.app.process_inputs(inputs, mode=update_mode)

        self.app.print_stats()
        
        if self.app.get_stats()['files'] == 0 and mode_choice == '1':
            print("Please run in processing mode (option 2) to add documents.")
            self.app.close()
            return

        is_rag_mode = (mode_choice == '1')
        
        print("\n" + "="*80)
        if is_rag_mode:
            print("🤖 RAG ASK - Ask questions in natural language (type 'quit' to exit)")
        else:
            print("🔍 SEMANTIC SEARCH - Enter your queries (type 'quit' to exit)")
        print("="*80)

        while True:
            prompt_text = "\n" + ("Ask your question" if is_rag_mode else "Enter your search query")
            query = input(f"{prompt_text} (or 'quit/exit/q' to exit): ").strip()
            if query.lower() in ['quit', 'exit', 'q']:
                break
            if not query:
                continue
            
            if is_rag_mode:
                self.app.ask_question(query)
            else:
                # This branch is technically unreachable from wizard now, 
                # but left in case of future expansion or CLI reuse
                self.app.perform_search(query)

        self.app.close()
        print("\n✓ Done!")

class CLIHandler:
    """Handles command-line arguments and routes to the app methods."""
    
    def __init__(self):
        self.parser = self._create_parser()

    def _create_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            description="🤖 Markdown Semantic Search CLI - Search your markdown docs naturally without embeddings.",
            epilog="Examples:\n  md-search search \"how to use\" --top 5\n  md-search add ./docs/ --mode skip\n  md-search stats",
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

        # Search command
        search_parser = subparsers.add_parser("search", help="🔍 Search the knowledge base using natural language")
        search_parser.add_argument("query", help="The natural language query to search for")
        search_parser.add_argument("--db", default="knowledge_base.db", help="Path to the DuckDB database (default: knowledge_base.db)")
        search_parser.add_argument("--top", type=int, default=3, help="Number of top results to return (default: 3)")

        # Ask command
        ask_parser = subparsers.add_parser("ask", help="🤖 Ask a natural language question based on the knowledge base (RAG)")
        ask_parser.add_argument("question", help="The question to ask")
        ask_parser.add_argument("--db", default="knowledge_base.db", help="Path to the DuckDB database (default: knowledge_base.db)")
        ask_parser.add_argument("--top", type=int, default=5, help="Number of chunks to retrieve for context (default: 5)")

        # Add command
        add_parser = subparsers.add_parser("add", help="🏗️  Add files or URLs to the knowledge base")
        add_parser.add_argument("paths", nargs="+", help="One or more URLs (.md), local file paths, or directories to index")
        add_parser.add_argument("--db", default="knowledge_base.db", help="Database to add documents to (default: knowledge_base.db)")
        add_parser.add_argument("--mode", choices=["replace", "skip"], default="replace", 
                                help="Update mode: 'replace' (re-index if exists) or 'skip' (skip if already indexed)")

        # Stats command
        stats_parser = subparsers.add_parser("stats", help="📊 Show statistics about the indexed documents")
        stats_parser.add_argument("--db", default="knowledge_base.db", help="Database to show stats for (default: knowledge_base.db)")
        
        return parser

    def run(self):
        args = self.parser.parse_args()

        if not args.command:
            InteractiveSession().run()
            return

        app = MarkdownSearchApp(args.db)
        
        try:
            if args.command == "search":
                app.perform_search(args.query, top_k=args.top)
            elif args.command == "ask":
                app.ask_question(args.question, top_k=args.top)
            elif args.command == "add":
                app.process_inputs(args.paths, mode=args.mode)
            elif args.command == "stats":
                app.print_stats()
        finally:
            app.close()
