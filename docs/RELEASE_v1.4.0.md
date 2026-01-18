# Release Notes - v1.4.0 🚀

We are excited to announce version 1.4.0 of **Markdown Semantic Search**! This release transforms the project from a simple search tool into a powerful, conversational RAG (Retrieval-Augmented Generation) assistant.

## ✨ Key Features

### 🤖 LangGraph RAG Integration
- **Natural Language Question Answering**: Use the new `ask` command to have a conversation with your markdown documents.
- **OpenRouter Support**: Seamlessly integrate with any LLM via OpenRouter (defaults to Gemini 2.0 Flash for high performance).
- **Strict Context Adherence**: Our assistant is now strictly document-bound. It will only answer based on your knowledge base and politely apologize if the information is missing—no hallucinations.
- **Conversation Memory**: Support for follow-up questions within a single session using LangGraph's in-memory persistence.

### 🍱 Interactive Interface Refinements
- **Consolidated Wizard**: Simplified the interactive menu to prioritize natural language questioning for existing databases.
- **Improved DB Discovery**: The app now automatically scans for and lists databases in the `knowledge/` directory.
- **Manual DB Entry**: Always allows manual entry of database paths, even if no local `.db` files are detected.

### 📦 Infrastructure & Tooling
- **`uv` Integration**: Switched to `uv` for lightning-fast dependency management and project execution.
- **Simplified Setup**: No more complex pip installs; just `uv run main.py`.

## 🛠️ Internal Improvements
- **Enhanced SearchService**: New `get_top_context()` method for cleanly formatting multi-chunk retrieval results for LLM consumption.
- **Assistant Personality**: Refined system prompts for a polite, human-like, and assistive tone.
- **Robust Documentation**: Fully updated README.md with comprehensive RAG setup and usage guides.

## 🚀 How to Upgrade
If you're using `uv`, your environment will update automatically on the next run. Otherwise, re-install in editable mode:
```bash
uv pip install -e .
```

---
*Built with ❤️ by ChotaBuziness - Smart engineering beats expensive tools.*
