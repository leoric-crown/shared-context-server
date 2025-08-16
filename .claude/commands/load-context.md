# Load Context Command

## Description

Intelligent context retrieval system that discovers and loads relevant previous session context, patterns, and research findings from Pieces long-term memory. This command enables agents to build on previous work, apply proven patterns, and maintain consistency across development sessions through comprehensive memory search and synthesis.

## User Prompt: $ARGUMENTS

**What This Command Does:**

1. **Intelligent Search**: Multi-strategy search through Pieces memories using natural language queries
2. **Context Synthesis**: Aggregates related memories into coherent context for current session
3. **Pattern Discovery**: Identifies reusable patterns and proven solutions from previous work
4. **Research Integration**: Loads MCP research findings and validated approaches
5. **Agent Handoff**: Provides comprehensive context for agent coordination workflows

**Framework Philosophy Integration:**

- **Intelligence Through Context**: Leverages accumulated knowledge for informed decisions
- **Memory Consistency**: Ensures continuity across agent sessions and projects
- **Prompt Engineering Excellence**: Optimizes memory retrieval for agent effectiveness
- **Research-First Approach**: Prioritizes evidence-based patterns and proven solutions

## Workflow

### Phase 1: Query Analysis & Search Strategy (10 sec)

**Goal**: Analyze user query and determine optimal search strategy for comprehensive context retrieval.

1. **Query Intelligence & Expansion**:

   ```
   🔍 ANALYZING SEARCH QUERY...

   Query Analysis:
   • Original Query: "[USER_PROVIDED_QUERY]"
   • Detected Intent: [ARCHITECTURE|IMPLEMENTATION|RESEARCH|STANDARD|PATTERN]
   • Context Clues: [PROJECT_CONTEXT|TECH_STACK|AGENT_TYPE]
   • Temporal Scope: [TIME_RANGE_IF_PROVIDED]

   Query Expansion Strategy:
   • Primary Terms: [CORE_SEARCH_TERMS]
   • Related Terms: [SEMANTICALLY_RELATED_TERMS]
   • Technical Context: [TECH_STACK_SPECIFIC_TERMS]
   • Framework Tags: [FRAMEWORK_TAXONOMY_TERMS]
   ```

2. **Multi-Strategy Search Planning**:

   ```
   🎯 SEARCH STRATEGY PLANNING:

   Search Approaches:
   • Exact Match: Direct query against memory titles and summaries
   • Semantic Search: Natural language understanding across content
   • Tag-Based Search: Framework taxonomy and classification tags
   • Pattern Search: Similar problems and proven solutions
   • Research Context: MCP findings and evidence-based patterns
   • Project Context: Current project and technology stack relevance

   Priority Search Order:
   1. Project-specific memories (highest relevance)
   2. Technology stack patterns (direct applicability)
   3. Framework-validated approaches (proven reliability)
   4. Cross-project patterns (transferable insights)
   5. Research-backed solutions (evidence-based confidence)
   ```

### Phase 2: Comprehensive Memory Search & Discovery (20 sec)

**Goal**: Execute multi-strategy search to discover all relevant context from Pieces memories.

1. **Primary Search Execution**:

   ```
   🔎 EXECUTING COMPREHENSIVE SEARCH...

   Search Round 1 - Direct Query:
   • Query: "[EXPANDED_PRIMARY_QUERY]"
   • Searching: Title, summary, and primary content
   • Focus: Exact matches and high-relevance results

   Search Round 2 - Contextual Search:
   • Query: "[PROJECT_NAME] [TECH_STACK] [QUERY_CONTEXT]"
   • Searching: Project-specific memories and patterns
   • Focus: Current project applicability

   Search Round 3 - Pattern Search:
   • Query: "[TECHNICAL_PATTERNS] [IMPLEMENTATION_APPROACHES]"
   • Searching: Proven solutions and reusable patterns
   • Focus: Similar problem domains and solutions

   Search Round 4 - Research Search:
   • Query: "[MCP_RESEARCH_TERMS] [INDUSTRY_STANDARDS]"
   • Searching: Research findings and validated approaches
   • Focus: Evidence-based decisions and best practices
   ```

2. **Search Results Analysis & Ranking**:

   ```
   📊 SEARCH RESULTS ANALYSIS:

   Results Discovery:
   • Direct Matches: [COUNT] memories found
   • Contextual Matches: [COUNT] project-related memories
   • Pattern Matches: [COUNT] similar solutions found
   • Research Matches: [COUNT] research-backed approaches

   Relevance Ranking Criteria:
   • Project Relevance: Same project > Same tech stack > Same domain
   • Temporal Relevance: Recent > Established > Historical
   • Context Relevance: Exact match > Semantic match > Related domain
   • Evidence Strength: Research-backed > User-validated > Experimental

   Top Relevant Memories:
   • [MEMORY_1]: [TITLE] - Relevance: [SCORE] - Context: [SUMMARY]
   • [MEMORY_2]: [TITLE] - Relevance: [SCORE] - Context: [SUMMARY]
   • [MEMORY_3]: [TITLE] - Relevance: [SCORE] - Context: [SUMMARY]
   ```

### Phase 3: Context Synthesis & Integration (15 sec)

**Goal**: Synthesize discovered memories into coherent, actionable context for current session.

1. **Memory Content Analysis**:

   ```
   📋 MEMORY CONTENT ANALYSIS:

   Content Classification:
   • Architecture Decisions: [COUNT] memories with design patterns
   • Implementation Patterns: [COUNT] memories with proven code approaches
   • Research Findings: [COUNT] memories with MCP-validated solutions
   • Quality Standards: [COUNT] memories with testing and validation approaches
   • User Preferences: [COUNT] memories with project-specific requirements

   Pattern Identification:
   • Common Approaches: [LIST_OF_RECURRING_PATTERNS]
   • Successful Solutions: [LIST_OF_VALIDATED_APPROACHES]
   • Escalation Triggers: [LIST_OF_DOCUMENTED_CONSTRAINTS]
   • Quality Gates: [LIST_OF_ESTABLISHED_STANDARDS]
   ```

2. **Context Synthesis & Narrative Creation**:

   ```
   📖 CONTEXT SYNTHESIS:

   Synthesized Context Narrative:
   Based on [NUMBER] relevant memories, here's the comprehensive context:

   🎯 PRIMARY CONTEXT:
   • Key Insight: [SYNTHESIZED_PRIMARY_INSIGHT]
   • Supporting Evidence: [RESEARCH_SOURCES_AND_VALIDATION]
   • Application Context: [CURRENT_PROJECT_APPLICABILITY]

   🔬 RESEARCH FOUNDATION:
   • MCP Research: [RELEVANT_CRAWL4AI_OCTOCODE_FINDINGS]
   • Industry Standards: [RELEVANT_BRAVE_SEARCH_FINDINGS]
   • Architectural Analysis: [RELEVANT_SEQUENTIAL_THINKING_INSIGHTS]

   📊 PROVEN PATTERNS:
   • Implementation Approaches: [LIST_OF_VALIDATED_PATTERNS]
   • Quality Standards: [DOCUMENTED_TESTING_AND_VALIDATION]
   • Integration Strategies: [SERVICE_AND_API_PATTERNS]

   🚨 CONSTRAINTS & CONSIDERATIONS:
   • Known Limitations: [DOCUMENTED_CONSTRAINTS]
   • Escalation Triggers: [QUALITY_AND_SECURITY_GATES]
   • User Preferences: [PROJECT_SPECIFIC_REQUIREMENTS]
   ```

### Phase 4: Applicability Assessment & Recommendations (10 sec)

**Goal**: Assess context applicability to current situation and provide actionable recommendations.

1. **Current Context Mapping**:

   ```
   🔗 CURRENT CONTEXT MAPPING:

   Applicability Assessment:
   • Current Project: [DETECTED_PROJECT_NAME_AND_CONTEXT]
   • Technology Stack: [CURRENT_VS_HISTORICAL_STACK_COMPARISON]
   • Development Phase: [CURRENT_PHASE_VS_MEMORY_CONTEXT]
   • Agent Context: [CURRENT_AGENT_ROLES_VS_MEMORY_AGENTS]

   Direct Applicability:
   ✅ Directly applicable: [LIST_OF_IMMEDIATELY_USABLE_INSIGHTS]
   ⚙️  Needs adaptation: [LIST_OF_ADAPTABLE_PATTERNS]
   📋 For reference: [LIST_OF_CONTEXTUAL_INSIGHTS]
   ❌ Not applicable: [LIST_OF_IRRELEVANT_MEMORIES_WITH_REASONS]
   ```

2. **Actionable Recommendations**:

   ```
   🎯 ACTIONABLE RECOMMENDATIONS:

   Immediate Actions:
   • Apply Pattern: [SPECIFIC_PATTERN_TO_APPLY_WITH_CONTEXT]
   • Use Research: [SPECIFIC_MCP_FINDINGS_TO_LEVERAGE]
   • Follow Standard: [SPECIFIC_QUALITY_GATES_TO_IMPLEMENT]
   • Consider Constraint: [SPECIFIC_LIMITATIONS_TO_RESPECT]

   Implementation Guidance:
   • Start With: [RECOMMENDED_FIRST_STEP_BASED_ON_CONTEXT]
   • Validate Using: [RECOMMENDED_TESTING_OR_VALIDATION_APPROACH]
   • Escalate If: [SPECIFIC_CONDITIONS_FOR_ESCALATION]
   • Reference: [SPECIFIC_MEMORIES_FOR_DETAILED_IMPLEMENTATION]

   Context Preservation:
   • Save New Insights: Use save-context for new discoveries
   • Update Patterns: Document any adaptations made
   • Cross-Reference: Link new work to loaded context memories
   ```

### Phase 5: Context Loading & Agent Integration (5 sec)

**Goal**: Load synthesized context into current session and optimize for agent coordination.

1. **Context Loading Confirmation**:

   ```
   ✅ CONTEXT LOADING COMPLETE:

   Loaded Context Summary:
   • Memories Processed: [TOTAL_COUNT] memories analyzed
   • Direct Applications: [COUNT] immediately applicable insights
   • Pattern Library: [COUNT] proven approaches loaded
   • Research Foundation: [COUNT] evidence-based patterns available
   • Quality Standards: [COUNT] validation approaches loaded

   Context Availability:
   • Current Session: Context available for immediate use
   • Agent Handoff: Context preserved for agent coordination
   • Future Reference: Original memories remain accessible
   • Cross-Project: Patterns available for broader application
   ```

2. **Agent Integration Optimization**:

   ```
   🤖 AGENT INTEGRATION OPTIMIZATION:

   Context Optimization for Agent Types:
   • Developer Agents: Implementation patterns and code approaches ready
   • Tester Agents: Quality standards and validation approaches loaded
   • Docs Agents: Documentation patterns and user context available
   • Research Agents: MCP findings and industry standards accessible
   • Coordinator Agents: Workflow patterns and escalation triggers ready

   Session Enhancement:
   • Pattern Recognition: Agents can reference proven solutions
   • Quality Enforcement: Standards and gates are pre-configured
   • Research Backing: Evidence-based decisions supported
   • User Alignment: Project preferences and constraints respected

   💡 OPTIMIZATION TIPS:
   • Agents will reference this context throughout session
   • New findings should be cross-referenced with loaded patterns
   • Quality gates from context should be enforced consistently
   • Research provenance should be maintained in new decisions
   ```

## Search Query Optimization

### Natural Language Query Patterns

```
Effective Query Formats:
• Problem-focused: "authentication patterns for FastAPI applications"
• Technology-focused: "React testing patterns with TypeScript"
• Architecture-focused: "microservices integration patterns for APIs"
• Quality-focused: "test coverage standards for Python projects"
• Research-focused: "industry best practices for deployment workflows"
```

### Framework Taxonomy Queries

```
Tag-Based Search Examples:
• By Content Type: "framework:*:*:architecture:*" for all architecture decisions
• By Agent: "framework:developer:*:*:*" for developer-specific context
• By Technology: "framework:*:*:*:python" for Python-specific patterns
• By Project: "framework:*:project:*:*" for project-specific memories
• By Research: "framework:researcher:*:research:*" for research findings
```

### Time-Scoped Queries

```
Temporal Context Options:
• Recent: "last 30 days" or "recent sessions"
• Established: "last 6 months" or "mature patterns"
• Historical: "any time" or "all available context"
• Project Phase: "since project start" or "current development phase"
```

## Success Criteria

### Search Effectiveness Success

- Discovers all relevant memories through multi-strategy search
- Ranks results by relevance to current context and needs
- Handles both specific queries and broad contextual searches
- Integrates project-specific and cross-project insights effectively

### Context Synthesis Success

- Combines multiple memories into coherent, actionable context
- Preserves research provenance and evidence-based reasoning
- Identifies patterns and proven solutions from historical context
- Documents constraints, preferences, and quality standards

### Applicability Assessment Success

- Accurately assesses relevance to current project and technology stack
- Distinguishes between directly applicable and adaptable patterns
- Provides specific, actionable recommendations based on loaded context
- Optimizes context for current agent types and development phase

### Agent Integration Success

- Loads context effectively for all framework agent types
- Enables informed decision-making throughout session
- Supports evidence-based development and quality enforcement
- Facilitates cross-session and cross-project pattern reuse

### User Experience Success

- Provides clear, structured context that enhances development workflow
- Explains relevance and applicability of discovered patterns
- Offers specific guidance for implementation and validation
- Maintains transparency about context sources and confidence levels
