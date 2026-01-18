import os
import subprocess
import pytest

def test_rag_flow():
    # 1. Create a sample markdown file
    sample_md = "test_doc.md"
    with open(sample_md, "w") as f:
        f.write("# RAG Test File\n\nThis is a test file for the Markdown Semantic Search RAG feature.\n"
                "The secret code is 'SQUIRREL'.\n"
                "Deployment should be done using 'uv run main.py'.")
    
    db_name = "test_rag.db"
    
    try:
        # 2. Add the file to the database
        subprocess.run(["uv", "run", "main.py", "add", sample_md, "--db", db_name], check=True)
        
        # 3. Ask a question using the CLI
        # Note: This requires OPENROUTER_API_KEY to be set in the environment
        if not os.getenv("OPENROUTER_API_KEY"):
            pytest.skip("OPENROUTER_API_KEY not set")
            
        result = subprocess.run(
            ["uv", "run", "main.py", "ask", "What is the secret code and how to deploy?", "--db", db_name],
            capture_output=True,
            text=True,
            check=True
        )
        
        print(result.stdout)
        
        # 4. Verify the output
        assert "SQUIRREL" in result.stdout
        assert "uv run main.py" in result.stdout
        assert "🤖 Response" in result.stdout
        
    finally:
        # Cleanup
        if os.path.exists(sample_md):
            os.remove(sample_md)
        if os.path.exists(db_name):
            os.remove(db_name)

if __name__ == "__main__":
    test_rag_flow()
