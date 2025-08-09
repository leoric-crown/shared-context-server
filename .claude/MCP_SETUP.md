# MCP Server Setup for Framework

The Claude multi-agent framework requires several MCP servers for research and code analysis. Add these to your project's `.claude/settings.local.json`.

## Required MCP Tools

```json
{
  "permissions": {
    "allow": [
      "mcp__sequential-thinking__sequentialthinking",
      "mcp__octocode__githubSearchRepositories", 
      "mcp__octocode__githubSearchCode",
      "mcp__octocode__githubGetFileContent",
      "mcp__octocode__githubViewRepoStructure",
      "mcp__crawl4ai__md",
      "mcp__crawl4ai__ask", 
      "mcp__crawl4ai__crawl",
      "mcp__brave-search__brave_web_search"
    ]
  }
}
```

## What Each Tool Does

- **sequential-thinking**: Multi-step reasoning for complex architectural decisions
- **octocode**: GitHub code search and repository analysis for proven patterns
- **crawl4ai**: Web scraping for official documentation and current practices
- **brave-search**: Web search for industry best practices and standards (requires API key)

## Installation

The framework-init command will check if these tools are available and provide setup instructions if missing.

## Optional Tools

You can also add these useful tools:
- **firecrawl**: Alternative web scraping (requires API key)
- **WebFetch**: Direct web fetching for specific domains

## Setup Validation

Test your MCP setup:
1. Try using one of the research tools in a conversation
2. The framework-init command will validate MCP availability during initialization