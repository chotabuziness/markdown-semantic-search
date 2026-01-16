#!/bin/bash

# Exit on error
set -e

echo "🚀 Starting publication process..."

# 1. Clean old builds
echo "🧹 Cleaning old build artifacts..."
rm -rf dist/ build/ *.egg-info

# 2. Ensure build tools are installed
echo "📦 Ensuring build tools are installed..."
./.venv/bin/python -m pip install --upgrade build twine

# 3. Build the package
echo "🏗️  Building source and wheel distributions..."
./.venv/bin/python -m build

# 4. Verify the package
echo "🔍 Verifying distributions with twine..."
./.venv/bin/python -m twine check dist/*

# 5. Upload to PyPI
read -p "❓ Do you want to upload to PyPI now? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]
then
    echo "📤 Uploading to PyPI..."
    ./.venv/bin/python -m twine upload dist/*
else
    echo "🛑 Upload cancelled. Build artifacts are ready in dist/"
fi

echo "✅ Done!"
