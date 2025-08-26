#!/bin/bash
# Generate secure keys for Shared Context MCP Server
# Usage: ./scripts/generate-keys.sh [--append-to-env]

set -e

echo "🔐 Generating secure keys for Shared Context MCP Server..."
echo

# Generate keys
API_KEY=$(openssl rand -base64 32)
JWT_SECRET_KEY=$(openssl rand -base64 32)
JWT_ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())" 2>/dev/null || python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")

# Display keys
echo "Generated keys:"
echo "==============="
echo "API_KEY=$API_KEY"
echo "JWT_SECRET_KEY=$JWT_SECRET_KEY"
echo "JWT_ENCRYPTION_KEY=$JWT_ENCRYPTION_KEY"
echo

# Append to .env if requested
if [[ "$1" == "--append-to-env" ]]; then
    if [[ -f .env ]]; then
        echo "📝 Appending keys to existing .env file..."
        echo "" >> .env
        echo "# Generated keys $(date)" >> .env
        echo "API_KEY=$API_KEY" >> .env
        echo "JWT_SECRET_KEY=$JWT_SECRET_KEY" >> .env
        echo "JWT_ENCRYPTION_KEY=$JWT_ENCRYPTION_KEY" >> .env
        echo "✅ Keys appended to .env file"
    else
        echo "❌ No .env file found. Create one first:"
        echo "   cp .env.minimal .env"
        echo "   ./scripts/generate-keys.sh --append-to-env"
        exit 1
    fi
elif [[ -f .env ]]; then
    echo "💡 To update your .env file, either:"
    echo "   1. Manually copy the keys above, or"
    echo "   2. Run: ./scripts/generate-keys.sh --append-to-env"
else
    echo "💡 To create .env file with these keys:"
    echo "   1. cp .env.minimal .env"
    echo "   2. Update .env with the keys shown above"
fi

echo
echo "🚀 Keys are ready! Start your server with:"
echo "   docker compose up -d"
echo "   # OR"
echo "   uv run python -m shared_context_server.scripts.cli"
