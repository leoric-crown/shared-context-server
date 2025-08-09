# Framework Initialization Command

## Description

Initiates a collaborative, multi-phase process to initialize the Claude multi-agent framework for a new project. This command installs and customizes the framework from the `~/.claude/claude-framework/` template into the target project's `.claude/` directory through conversation, automated research, and intelligent adaptation.

**What This Command Does:**
1. **Installs Framework**: Copies `~/.claude/claude-framework/` template to target project's `.claude/` directory
2. **Adapts Content**: Replaces `[ADAPT: ...]` markers with project-specific content based on research
3. **Customizes for Stack**: Configures agents and guides for detected technology stack and architecture
4. **Moves CLAUDE.md**: Moves main configuration to project root and cleans up template files

**Initialization Types Supported:**
- **Fresh Repository**: Empty or minimal repository - installs complete framework
- **Existing Codebase**: Established project - analyzes patterns and installs adapted framework
- **Claude Migration**: Project with basic Claude setup - upgrades to full multi-agent framework
- **Framework Enhancement**: Existing framework - updates with latest patterns and improvements

## Workflow

### Phase 1: Project Discovery & Context Loading (Internal)

**Goal**: To understand the target project's current state, technology stack, and development patterns before engaging the user.

**IMPORTANT**: This analysis focuses on the TARGET PROJECT where the framework will be installed, NOT the `claude-framework/` template directory.

**Prerequisites Check**: Verify MCP tools are available for research:
- Test if sequential-thinking, octocode, crawl4ai, and brave-search are accessible
- If missing, guide user to:
  1. Copy `~/.claude/claude-framework/settings.local.template.json` to target project's `.claude/settings.local.json`
  2. Or reference `~/.claude/claude-framework/MCP_SETUP.md` for manual configuration
- Framework can work without MCP tools but with reduced research capabilities

1. **Target Repository Analysis**: Examine the target project (completely ignore `claude-framework/` template directory)
   - **Framework Status**: Check if target already has `.claude/` directory installed (not the template)
   - **Project Assessment**: Analyze actual project files, requirements documents, and code structure  
   - **Dependency Analysis**: Parse package files (`package.json`, `requirements.txt`, `Cargo.toml`, etc.) for technology stack
   - **Infrastructure Detection**: Identify existing testing, CI/CD, deployment, and quality assurance setup

2. **Technology Stack Detection**: Automatically identify key technologies
   - Programming language and version requirements
   - Package manager (npm, pip, cargo, composer, etc.)
   - Primary frameworks (React, FastAPI, Django, Express, etc.)
   - Testing frameworks (pytest, jest, vitest, etc.)
   - Quality tools (eslint, ruff, prettier, etc.)

3. **Project Structure Analysis**: Understand current organization
   - Source code directory structure
   - Configuration file locations
   - Documentation patterns
   - Build and deployment setup

4. **Existing Context Synthesis**: Create baseline understanding
   - **Project Maturity Assessment**: Empty repo vs established codebase vs production system
   - **Existing Patterns Recognition**: Code organization, naming conventions, architectural decisions
   - **Development Workflow Detection**: Current testing, deployment, and quality practices
   - **Integration Point Analysis**: External services, APIs, databases, and deployment environments
   - **Legacy Configuration Handling**: How to preserve or migrate existing configurations

### Phase 2: Interactive Project Configuration (User-Facing)

**Goal**: To collaboratively discover and validate project-specific configuration through structured conversation.

1. **Adaptive Project Discovery** (varies based on repository state)

   **For Fresh/Empty Repositories:**
   ```
   "I notice this appears to be a fresh repository. Let me gather the key information to set up your multi-agent framework:
   
   📋 PROJECT BASICS
   • What is the name of your project? (detected: [repo-name])
   • How would you describe what this project will do in one sentence?
   • What is the primary purpose or goal of this new system?
   ```

   **For Existing Codebases:**
   ```
   "I've analyzed your existing codebase and detected [technology stack] with [X files, Y components]. Let me validate my understanding:
   
   📋 PROJECT VALIDATION
   • Project: [detected-name] - Is this correct?
   • Purpose: Based on the code, it appears this system [inferred-purpose] - Is this accurate?
   • Current State: I see [detected-features/components] - Are there other key aspects I should know about?
   ```

2. **Technology Stack Validation & Enhancement** (adaptive based on discovery)

   **For Fresh Repositories:**
   ```
   🔧 TECHNOLOGY STACK SELECTION
   I detected minimal setup. Let's choose your technology stack:
   • What programming language will you use?
   • What package manager do you prefer? (npm, pip, cargo, etc.)
   • Do you have a preferred framework in mind?
   • Any specific version requirements or constraints?
   ```

   **For Existing Codebases:**
   ```
   🔧 TECHNOLOGY STACK VALIDATION
   I detected the following from your existing code:
   • Language: [detected language and version]
   • Package Manager: [detected manager from lock files]
   • Primary Framework: [detected framework from dependencies]
   • Testing: [detected testing framework]
   • Quality Tools: [detected linters/formatters]
   
   • Is this detection accurate? Any corrections needed?
   • Are there additional tools or frameworks I should know about?
   • Any upcoming technology changes planned?
   ```

3. **Architecture & Development Patterns**
   ```
   🏗️ ARCHITECTURE PATTERNS
   • Does your project follow any specific architectural patterns?
   • What are your main components or modules?
   • How is data handled and stored in your system?
   • Are there external services or APIs you integrate with?
   ```

4. **Development Workflow & Quality Standards**
   ```
   ✅ DEVELOPMENT PRACTICES
   • What testing frameworks and approaches do you use?
   • What code quality tools are important to you? (linting, type checking)
   • How do you prefer to handle documentation?
   • Do you have specific deployment or build processes?
   ```

5. **Current Development Status & Goals**
   ```
   🎯 PROJECT STATUS & GOALS
   • What percentage complete would you say your project is?
   • What are you actively working on now?
   • What are your upcoming milestones or goals?
   • Are there specific development challenges you're facing?
   ```

6. **Existing Configuration Handling** (for established projects)
   ```
   📁 CONFIGURATION MIGRATION
   • I found existing configuration files: [list detected files]
   • How would you like to handle existing .claude/, CLAUDE.md, etc.?
     - Replace completely with new framework
     - Merge with existing configuration  
     - Backup existing and create fresh setup
   • Are there custom patterns or scripts you want to preserve?
   • Any existing AI workflows or agents you want to maintain?
   ```

7. **Agent & Workflow Preferences**
   ```
   🤖 FRAMEWORK CUSTOMIZATION
   • Do you work on UI/visual components? (affects visual validation setup)
   • How important is automated testing in your workflow?
   • Do you prefer detailed documentation or minimal docs?
   • Are there specific development workflows you want to maintain?
   ```

### Phase 3: Comprehensive MCP Research & Pattern Discovery (Internal)

**Goal**: To gather comprehensive technical context, proven patterns, and framework-specific guidance using our MCP research infrastructure.

#### 3.1 Technology Stack Research (10-15 min)
**Use Crawl4AI for official documentation and current patterns:**
```
Framework Documentation Research:
• Primary Framework: Scrape official docs for detected framework
  - crawl4ai: {detected_framework_docs_url} 
  - Focus: Architecture patterns, best practices, project structure
  - Query: "project structure patterns setup configuration"

• Testing Framework: Research testing approaches and patterns
  - crawl4ai: {testing_framework_docs_url}
  - Focus: Modern testing patterns, configuration, integration
  - Query: "testing patterns setup configuration best practices"

• Package Manager: Research setup and workflow patterns
  - crawl4ai: {package_manager_docs_url}
  - Focus: Installation, dependency management, scripts
  - Query: "project setup installation configuration workflows"
```

#### 3.2 Proven Implementation Patterns (15-20 min)
**Use Octocode for battle-tested implementations:**
```
Repository Pattern Research:
• Similar Projects: Find successful projects with same tech stack
  - octocode: githubSearchRepositories
  - Query: ["{detected_language}", "{primary_framework}", "{project_domain}"]
  - Stars: ">100" (quality filter)
  - Language: {detected_language}
  - Updated: ">2023-01-01" (recent/maintained)

• Architecture Patterns: Study proven architectural approaches
  - octocode: githubSearchCode  
  - Query: ["{architecture_pattern}", "{framework_name}", "structure"]
  - Focus: Project organization, configuration patterns, best practices

• Quality Standards: Research testing and code quality approaches
  - octocode: githubSearchCode
  - Query: ["{testing_framework}", "{lint_tool}", "configuration"]
  - Focus: Testing patterns, CI/CD, quality gates

• Integration Patterns: Find integration and deployment patterns
  - octocode: githubSearchCode
  - Query: ["{framework_name}", "deployment", "configuration"]
  - Focus: Environment setup, deployment patterns, production config
```

#### 3.3 Framework-Specific Architecture Research (10-15 min)
**Use SequentialThinking for complex architectural decisions:**
```
Architecture Decision Analysis:
• Project Structure: Analyze optimal project organization for tech stack
  - sequential-thinking: Multi-step analysis of project structure options
  - Consider: Scalability, maintainability, team collaboration patterns
  - Evaluate: Monolithic vs modular, feature-based vs layer-based organization

• Integration Strategy: Plan integration approaches for detected dependencies
  - sequential-thinking: Integration pattern analysis
  - Consider: External services, database patterns, API design
  - Evaluate: Synchronous vs asynchronous, event-driven vs request-response

• Quality Strategy: Design testing and quality assurance approach
  - sequential-thinking: Testing strategy analysis  
  - Consider: Unit vs integration vs e2e testing ratios
  - Evaluate: CI/CD pipeline design, deployment strategies
```

#### 3.4 Industry Best Practices Research (5-10 min)
**Use Brave Search for current industry standards:**
```
Industry Standards Research:
• Framework Best Practices: Current recommendations for detected tech stack
  - brave-search: "{framework_name} best practices 2024 project structure"
  - brave-search: "{framework_name} production setup deployment patterns"

• Quality Standards: Industry quality and testing standards
  - brave-search: "{language} testing best practices 2024 modern patterns"
  - brave-search: "{language} code quality tools linting standards"

• Security Patterns: Security best practices for tech stack
  - brave-search: "{framework_name} security best practices production"
```

#### 3.5 Research Context Synthesis (5 min)
**Consolidate all research findings:**
```
Research Integration:
• Pattern Consolidation: Merge findings from all MCP sources
  - Official documentation patterns (crawl4ai)
  - Proven implementation examples (octocode) 
  - Architectural decision analysis (sequential-thinking)
  - Industry best practices (brave-search)

• Validation & Consistency: Ensure research coherence
  - Cross-validate patterns across sources
  - Identify conflicting recommendations and resolve
  - Prioritize patterns by source credibility and project fit

• Template Value Mapping: Map research findings to template variables
  - Architecture patterns → ARCHITECTURE.* variables
  - Quality tools → QUALITY.* and TESTING.* variables  
  - Project structure → WORKFLOW.* and SETUP.* variables
  - Integration patterns → CONFIG.* and CLI.* variables
```

### Phase 4: Framework Customization & Template Processing (Internal)

**Goal**: Generate fully customized framework files by replacing specific template markers with project values.

**Files Requiring Natural Language Adaptation:**

1. **CLAUDE.md** (Main Configuration) - **Heavy adaptation needed**
   - Project identity: `[ADAPT: Project name...]`, `[ADAPT: Project description...]`
   - Tech stack: `[ADAPT: Detected programming language...]`, libraries from research
   - Architecture components: `[ADAPT: Main system coordinator...]` from detected patterns
   - Commands: `[ADAPT: Installation command...]`, `[ADAPT: Quality commands...]`
   - All content intelligently adapted based on research and conversation

2. **All agent files** - **Moderate adaptation needed**
   - `[ADAPT: System integration patterns...]` based on detected architecture
   - `[ADAPT: Quality tools...]` based on detected tech stack
   - `[ADAPT: Framework-specific examples...]` based on research findings
   - `[ADAPT: Testing patterns...]` based on detected testing approach

3. **All tech guides** - **Moderate adaptation needed**
   - `[ADAPT: Language-specific patterns...]` based on detected tech stack
   - `[ADAPT: Domain examples...]` based on project domain and purpose
   - `[ADAPT: Integration patterns...]` based on detected services

4. **Commands and workflows** - **Light adaptation needed**
   - `[ADAPT: Directory structures...]` based on detected project organization
   - `[ADAPT: Process terminology...]` based on detected project domain

**Adaptation Process:**
- LLM reads `[ADAPT: ...]` markers and replaces with contextually appropriate content
- Content informed by MCP research findings and user conversation
- No rigid schema - intelligent adaptation based on project needs

### Phase 5: Framework Deployment & Validation (User-Facing)

1. **Natural Language Adaptation**: Transform all `[ADAPT: ...]` markers with project-specific content
   - Process `CLAUDE.md` with research-informed project details
   - Adapt agent files with detected architecture patterns and quality tools
   - Transform tech guides with language-specific examples and domain context
   - Configure development standards with detected tooling and practices

2. **Tech Guide Customization**: Create stack-specific guidance
   - Framework integration patterns for detected frameworks
   - Testing patterns for detected testing tools
   - Data architecture patterns appropriate for the project
   - Additional custom guides as needed

3. **Command Adaptation**: Adjust workflow commands for project structure
   - Update directory paths in command templates
   - Customize workflow steps for project conventions
   - Adapt quality gates for project standards

4. **Validation & Quality Check**: Ensure framework coherence
   - Verify all template variables are populated
   - Check framework consistency across all files
   - Validate agent coordination patterns
   - Ensure development standards alignment

### Phase 5: Framework Deployment & Validation (User-Facing)

**Goal**: To deploy the configured framework with research-backed customizations and validate it meets project needs.

1. **Research-Informed Framework Preview**: Show the user what will be created with research context
   ```
   🎉 FRAMEWORK CONFIGURATION COMPLETE
   
   I've prepared a customized Claude framework for your {{ PROJECT.NAME }} project based on comprehensive research:
   
   📁 FRAMEWORK STRUCTURE:
   • .claude/CLAUDE.md - Main project guidance ({{ TEMPLATE_VALUES_COUNT }} customizations)
   • .claude/agents/ - 5 specialized agents configured for {{ TECH_STACK.LANGUAGE }}
   • .claude/commands/ - 3-phase workflow system
   • .claude/tech-guides/ - {{ TECH_GUIDE_COUNT }} guides for your technology stack
   • .claude/development-standards.md - Quality standards for {{ QUALITY_TOOLS_LIST }}
   
   🔬 RESEARCH-BACKED CUSTOMIZATIONS:
   • Framework patterns from {{ PRIMARY_FRAMEWORK }} official documentation
   • Testing approaches from {{ SUCCESSFUL_PROJECTS_COUNT }} similar successful projects
   • Architecture decisions validated through multi-step analysis
   • Quality tools based on current industry best practices (2024)
   • Integration patterns from {{ STAR_BACKED_EXAMPLES }} star-backed repositories
   
   📊 RESEARCH SOURCES USED:
   • Official Documentation: {{ CRAWL4AI_SOURCES_COUNT }} framework docs analyzed
   • Proven Patterns: {{ OCTOCODE_REPOS_COUNT }} successful repositories studied  
   • Architecture Analysis: {{ SEQUENTIAL_THINKING_DECISIONS }} design decisions analyzed
   • Industry Standards: {{ BRAVE_SEARCH_QUERIES }} current best practices researched
   
   Does this research-informed configuration look correct for your project?
   ```

2. **User Validation & Adjustments**: Allow final customization
   ```
   📝 FINAL CUSTOMIZATIONS
   • Are there any specific changes you'd like to make?
   • Do you want to add any custom tech guides?
   • Should I adjust any of the development standards?
   • Any additional agent specializations needed?
   ```

3. **Framework Installation**: Copy and adapt framework from `~/.claude/claude-framework/` template
   
   **CRITICAL: Correct Copy Command Syntax**
   ```bash
   # CORRECT - Copy contents of ~/.claude/claude-framework/ into .claude/
   cp -r ~/.claude/claude-framework/* .claude/
   
   # OR if .claude/ doesn't exist yet:
   cp -r ~/.claude/claude-framework .claude
   mv .claude/claude-framework/* .claude/
   rmdir .claude/claude-framework
   
   # WRONG - Creates nested structure (.claude/claude-framework/):
   cp -r ~/.claude/claude-framework .claude/  # DON'T DO THIS!
   ```
   
   **Installation Process:**
   - **Step 1**: Ensure clean copy - `~/.claude/claude-framework/` contents go INTO `.claude/`, not nested under it
   - **Step 2**: Verify structure - `.claude/agents/`, `.claude/commands/`, etc. (NOT `.claude/claude-framework/`)
   - **Step 3**: Process all `[ADAPT: ...]` markers with research-informed, project-specific content
   - **Step 4**: Generate contextually appropriate examples based on detected technology stack
   - **Step 5**: Move CLAUDE.md to project root and clean up template references

   **For Fresh Repositories:**
   - Install complete framework structure in new `.claude/` directory
   - All files adapted for detected technology stack and project domain

   **For Existing Projects:**
   - Handle existing `.claude/` configurations based on user preference:
     - **Replace Mode**: Backup existing, install fresh adapted framework
     - **Merge Mode**: Intelligently merge new patterns with existing setup
     - **Migration Mode**: Preserve custom elements, upgrade framework components
   - Validate no conflicts with existing project structure

4. **PRP Directory Structure Creation**: Set up project planning directories
   
   **Create PRP Directory Structure:**
   ```bash
   # Create standardized PRP (Project Requirements & Planning) directory structure
   mkdir -p PRPs/1-planning
   mkdir -p PRPs/2-prps  
   mkdir -p PRPs/3-completed
   mkdir -p PRPs/4-archive
   mkdir -p PRPs/templates
   
   # Create initial planning template if it doesn't exist
   if [ ! -f "PRPs/templates/feature_planning_base.md" ]; then
     echo "# Feature Planning Template" > PRPs/templates/feature_planning_base.md
     echo "## Overview" >> PRPs/templates/feature_planning_base.md
     echo "## Requirements" >> PRPs/templates/feature_planning_base.md
     echo "## Implementation Plan" >> PRPs/templates/feature_planning_base.md
   fi
   ```
   
   **Manual File Migration** (if you have existing feature/PRD files):
   ```bash
   # If you have existing feature files, requirements docs, or PRDs:
   # - Move them to appropriate PRP directories:
   #   • Active planning docs → PRPs/1-planning/
   #   • Formal requirements → PRPs/2-prps/
   #   • Completed features → PRPs/3-completed/
   #   • Legacy docs → PRPs/4-archive/
   
   # Example migrations (adjust paths as needed):
   # mv docs/features/* PRPs/1-planning/
   # mv requirements/* PRPs/2-prps/
   # mv completed-features/* PRPs/3-completed/
   
   # Review and organize manually based on your existing structure
   ```

5. **Generate Tech Stack-Specific .gitignore**: Create appropriate .gitignore based on final project analysis
   
   **Smart .gitignore Generation:**
   ```bash
   # Generate .gitignore based on the FINAL analyzed state of the project
   # (after all discovery, research, and framework installation is complete)
   
   if [ ! -f ".gitignore" ]; then
     # Start with framework template
     cp ~/.claude/claude-framework/.gitignore .gitignore
     
     # Customize based on detected technology stack and final project state:
     # - Add specific ignores for detected frameworks, build tools, and dependencies
     # - Include any project-specific patterns discovered during analysis
     # - Consider build artifacts from detected CI/CD or deployment setup
     # - Add ignores for any development tools mentioned in project documentation
     
     echo "✅ Created .gitignore customized for your detected technology stack"
     echo "   Base template: ~/.claude/claude-framework/.gitignore"
     echo "   Customized for: [list detected technologies here]"
   else
     echo "ℹ️  Project already has .gitignore - reviewing for potential additions..."
     echo "   Framework template available at: ~/.claude/claude-framework/.gitignore"
     echo "   Consider merging relevant sections based on your final tech stack analysis"
   fi
   ```
   
   **Important**: This step occurs AFTER all project discovery and research phases are complete, ensuring the .gitignore reflects the true final state of the project including any detected frameworks, build systems, package managers, and development tools.

6. **Framework Cleanup & Finalization**: Complete installation with cleanup
   
   **Cleanup Commands:**
   ```bash
   # Move CLAUDE.md to project root (where Claude expects it)
   mv .claude/CLAUDE.md ./CLAUDE.md
   
   # Remove template README.md that was copied (keep your project's README if it exists)
   if [ -f ".claude/README.md" ]; then
     rm .claude/README.md
   fi
   
   # Clean up any remaining template references (if they exist)
   # Note: Template directory ~/.claude/claude-framework remains untouched for future use
   ```
   
7. **Installation Validation**: Verify correct framework structure
   ```bash
   # VERIFY: Correct structure should look like this
   ls -la .claude/
   # Should show: agents/ commands/ tech-guides/ development-standards.md
   # Should NOT show: CLAUDE.md (moved to root) or claude-framework/ (nested directory)
   
   ls -la ./CLAUDE.md
   # Should show: CLAUDE.md in project root
   
   # If you see .claude/claude-framework/, you copied incorrectly - fix it:
   mv .claude/claude-framework/* .claude/
   rmdir .claude/claude-framework
   ```
   
   **Validation Checklist:**
   - ✅ `.claude/agents/` exists with 5 agent files
   - ✅ `.claude/commands/` exists with 3 command files  
   - ✅ `./CLAUDE.md` exists in project root (not in `.claude/`)
   - ✅ `PRPs/` directory structure exists (1-planning, 2-prps, 3-completed, 4-archive, templates)
   - ✅ `.gitignore` exists with tech stack-specific ignores
   - ✅ No `.claude/README.md` (template README removed)
   - ✅ No nested `.claude/claude-framework/` directory
   - ✅ Template directory `~/.claude/claude-framework/` remains intact for future use
   - ✅ All `[ADAPT: ...]` markers processed with project-specific content
   - ✅ Framework files are syntactically correct
   - ✅ Existing feature/PRD files manually migrated to appropriate PRP directories (if applicable)

8. **Research-Enhanced Next Steps Guidance**: Provide clear direction with research context preservation
   ```
   ✅ FRAMEWORK INITIALIZATION COMPLETE!
   
   🚀 GETTING STARTED (Research-Enhanced):
   1. Your Claude framework is now active with research-backed customizations
   2. All agents have access to research context from framework initialization:
      • {{ CRAWL4AI_PATTERNS_COUNT }} proven patterns from official documentation
      • {{ OCTOCODE_EXAMPLES_COUNT }} battle-tested implementation examples  
      • {{ SEQUENTIAL_THINKING_DECISIONS }} architectural analysis results
   3. Try the feature planning workflow: Agents will use research context for intelligent decisions
   4. Quality standards are enforced based on industry research for {{ QUALITY_TOOLS }}
   
   📚 RESEARCH-INFORMED COMMANDS:
   • Feature Planning: Agents use framework research for intelligent planning
   • PRP Generation: Implementation specs informed by proven patterns
   • Code Implementation: Development guided by research-validated approaches
   
   🎯 RESEARCH-ENHANCED FRAMEWORK FEATURES:
   • Context-Enriched Decision Making (with research provenance)
   • 5-Agent Intelligent Coordination (research-informed)
   • MCP Tools Integration (crawl4ai, octocode, sequential-thinking, brave-search)
   • {{ PROJECT_SPECIFIC_FEATURES }} (validated against similar successful projects)
   
   🔬 RESEARCH CONTEXT PRESERVED FOR FUTURE USE:
   • Framework patterns stored in agent knowledge base
   • Proven implementations accessible for reference
   • Architectural decisions documented with rationale
   • Quality standards backed by industry research
   
   Your research-enhanced framework is ready for intelligent development!
   ```

## Template Processing Philosophy

**Targeted & Specific**: Only a few key files need templating. Most agents and guides work as-is.

### Core Template Markers (Only These Need Replacement)
```
{{ PROJECT.NAME }}                - "my-awesome-app" (used in 15+ places)
{{ TECH_STACK.LANGUAGE }}         - "Python" | "TypeScript" | "Rust" 
{{ QUALITY.LINT_COMMAND }}        - "ruff check" | "eslint" | "cargo clippy"
{{ SETUP.INSTALL_COMMAND }}       - "pip install -e ." | "npm install"
{{ CLI.COMMAND_1.NAME }}          - "Server Management" | "Build Tools"
```

### Template Processing Scope
- **CLAUDE.md**: Needs extensive templating (~50 markers)
- **docs.md agent**: Needs minimal templating (~7 markers)  
- **commands/**: Need directory paths and tech guide names
- **development-standards.md**: Just project name
- **All other files**: Work as-is, no templating needed

### Smart Auto-Detection
- Detects project name, language, package manager, testing framework
- LLM fills in reasonable defaults through conversation
- No complex schema processing needed

### Example Outcomes

**Python FastAPI Project:**
- Language: Python 3.9+ with uv package manager
- Testing: pytest with async support
- Quality: ruff + mypy for code quality
- Architecture: Clean API architecture with SQLAlchemy

**TypeScript React Project:**
- Language: TypeScript with npm/yarn
- Testing: vitest with React Testing Library  
- Quality: eslint + typescript compiler
- Architecture: Component-based with Next.js patterns

**Rust CLI Project:**
- Language: Rust with cargo
- Testing: built-in cargo test + proptest
- Quality: clippy + rustfmt
- Architecture: CLI-focused with clap patterns

## Success Criteria

### Discovery Success
- All critical project information is gathered through conversation
- Technology stack is accurately identified and validated through auto-detection
- Development patterns and preferences are understood and documented
- User requirements are clearly captured and validated

### MCP Research Success
- **Crawl4AI**: Official framework documentation successfully analyzed for patterns
- **Octocode**: Multiple similar successful projects identified and studied
- **SequentialThinking**: Complex architectural decisions analyzed with multi-step reasoning
- **Brave Search**: Current industry best practices researched and integrated
- Research findings are synthesized and mapped to template variables

### Framework Customization Success
- All template variables are populated with research-informed values
- Tech guides are customized based on official documentation and proven patterns
- Agent configurations include research context for intelligent decision making
- Development standards reflect both project needs and industry best practices
- Quality tools are configured based on research findings

### Research Context Preservation Success
- Framework patterns from research are embedded in agent configurations
- Proven implementation examples are accessible to agents during development
- Architectural decisions are documented with research-backed rationale
- Research provenance is maintained throughout the framework

### Deployment Success
- Framework files are created correctly with research-enhanced customizations
- All agents have access to research context bundles
- Template processing includes research findings integration
- Framework passes validation with research coherence checks

### User Experience Success
- Research process is transparent but doesn't overwhelm user
- User sees clear value from research-backed recommendations
- Framework setup leverages research for intelligent defaults
- Getting started guidance includes research context and validated approaches

## Common Installation Issues & Fixes

### Issue: Nested `.claude/claude-framework/` Directory
**Symptom**: Framework files are in `.claude/claude-framework/` instead of `.claude/`
**Cause**: Used `cp -r claude-framework .claude/` instead of `cp -r claude-framework/* .claude/`
**Fix**:
```bash
# Move files to correct location
mv .claude/claude-framework/* .claude/
rmdir .claude/claude-framework

# Verify correct structure
ls .claude/  # Should show: agents/ commands/ tech-guides/ CLAUDE.md
```

### Issue: Template Markers Not Processed
**Symptom**: Files still contain `[ADAPT: ...]` markers
**Cause**: Framework copied but adaptation step not completed
**Fix**: Process adaptation markers with project-specific content based on research findings

### Issue: Missing MCP Tools
**Symptom**: Research phases fail or skip
**Cause**: MCP tools not configured in `.claude/settings.local.json`
**Fix**: Copy `~/.claude/claude-framework/settings.local.template.json` or follow `~/.claude/claude-framework/MCP_SETUP.md` instructions

## Completion

The command is complete when:
1. All project discovery is finished through collaborative conversation
2. Framework is correctly installed in `.claude/` directory (not nested)
3. All `[ADAPT: ...]` markers are processed with project-specific content
4. PRP directory structure is created and existing files are manually migrated (if applicable)
5. Tech stack-specific .gitignore is generated based on detected project type
6. CLAUDE.md is moved to project root and template cleanup is complete (including README.md removal)
7. Framework validation confirms correct structure and functionality
8. User receives clear guidance for getting started with the framework

**Next Steps**: User can immediately begin using the framework for feature planning, development coordination, and quality assurance through the intelligent agent system.