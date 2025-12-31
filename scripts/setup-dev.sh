#!/bin/bash
# Development environment setup script

set -e

echo "🔧 Setting up development environment..."

# Check if pre-commit is installed
if ! command -v pre-commit &> /dev/null; then
    echo "📦 Installing pre-commit..."
    pip install pre-commit
fi

# Install pre-commit hooks
echo "🔗 Installing pre-commit hooks..."
pre-commit install

# Setup frontend
echo "📦 Installing frontend dependencies..."
cd frontend
npm install
cd ..

# Setup backend (for local development)
if [ -d "backend" ]; then
    echo "📦 Installing backend dependencies..."
    cd backend
    if command -v uv &> /dev/null; then
        uv sync
    else
        pip install -r requirements.txt
    fi
    cd ..
fi

echo "✅ Development environment setup complete!"
echo ""
echo "Available commands:"
echo "  Frontend:"
echo "    npm run lint       - Run ESLint"
echo "    npm run lint:fix   - Fix ESLint issues"
echo "    npm run type-check - TypeScript type checking"
echo ""
echo "  Backend:"
echo "    cd backend && make lint      - Run Ruff linting"
echo "    cd backend && make format    - Format code with Ruff"
echo "    cd backend && make lint-fix  - Fix linting issues"
echo "    cd backend && make test      - Run tests"
echo ""
echo "  Pre-commit hooks will run automatically on git commit!"
