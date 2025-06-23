# PowerShell script to commit the LangChain dependency fix
Write-Host "Committing LangChain dependency fix..."

# Add the modified pyproject.toml
git add pyproject.toml

# Check status
git status

# Commit the changes
git commit -m "Fix LangChain dependency conflict in CI/CD pipeline

- Updated LangChain packages to compatible versions (0.3.x series)
- langchain: ^0.3.26 (was ^0.2.0)
- langchain-anthropic: ^0.3.15 (was ^0.1.0)
- langchain-openai: ^0.3.25 (was ^0.1.0)
- langchain-community: ^0.3.26 (was ^0.2.0)
- langchain-experimental: ^0.3.4 (was ^0.0.50)
- langchain-core: ^0.3.66 (was ^0.2.0)

This resolves the version conflict where langchain-experimental 0.0.50
required langchain-core <0.2.0 but the project specified ^0.2.0.
All packages now use compatible 0.3.x versions."

# Push to remote
git push origin main

Write-Host "Changes committed and pushed successfully!"
