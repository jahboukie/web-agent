# AI Collaboration Guide for WebAgent Development

**Document Version:** 1.0  
**Date:** June 19, 2025  
**Purpose:** Define protocols for hybrid AI development with Claude Code and Augment Code

---

## Overview

This guide establishes the collaboration framework between human developers and AI assistants (Claude Code and Augment Code) for the WebAgent project. It defines roles, responsibilities, handoff protocols, and quality standards to ensure efficient and effective development.

## AI Assistant Roles & Responsibilities

### Claude Code (Architecture & Design AI)

**Primary Responsibilities:**
- System architecture and high-level design decisions
- Database schema design and complex data modeling
- Security architecture and implementation patterns
- Cross-cutting concerns (logging, error handling, middleware)
- Integration patterns between major system components
- Performance optimization strategies
- Code review and refactoring guidance

**Typical Tasks:**
- Design database schemas with proper relationships and constraints
- Create application architecture diagrams and documentation
- Define API contracts and interface specifications
- Design error handling and retry strategies
- Create security patterns and authentication flows
- Plan integration strategies for external services
- Review and optimize system-wide patterns

**Output Expectations:**
- Comprehensive architectural documentation
- Detailed implementation specifications for Augment Code
- Database migration scripts and model definitions
- Security implementation guidelines
- Performance benchmarking criteria

### Augment Code (Implementation AI)

**Primary Responsibilities:**
- Daily feature implementation following established patterns
- API endpoint development based on specifications
- Unit test generation and maintenance
- Browser automation script development
- Error handling and logging implementation
- Performance optimization and code cleanup
- Documentation updates for implemented features

**Typical Tasks:**
- Implement CRUD operations for database models
- Create FastAPI endpoints following OpenAPI specifications
- Write comprehensive unit tests with pytest
- Develop Playwright browser automation scripts
- Implement error handling and logging in services
- Create data validation and serialization logic
- Generate API documentation and code comments

**Output Expectations:**
- Production-ready feature implementations
- Comprehensive test coverage (90%+ target)
- Well-documented code with proper error handling
- Performance-optimized implementations
- Consistent code style following project standards

## Collaboration Protocols

### Task Handoff Protocol

#### From Human to Claude Code

**When to Engage Claude Code:**
- New feature requiring architectural decisions
- Database schema changes or complex queries
- Security implementation requirements
- System integration planning
- Performance bottleneck analysis
- Cross-cutting concern implementation

**Required Information:**
- Clear problem statement and requirements
- Business context and constraints
- Performance and scalability requirements
- Security considerations
- Integration requirements with existing systems

**Expected Deliverables:**
- Architectural design document
- Implementation specifications for Augment Code
- Database schema changes (if applicable)
- Security requirements and patterns
- Testing strategy and acceptance criteria

#### From Claude Code to Augment Code

**Handoff Requirements:**
- Complete architectural specification
- Detailed implementation requirements
- Code patterns and style guidelines
- Test requirements and coverage targets
- Error handling specifications
- Performance benchmarks

**Handoff Template:**
```markdown
## Implementation Task: [Feature Name]

### Overview
[Brief description of what needs to be implemented]

### Architecture Context
[Reference to architectural decisions and patterns]

### Implementation Requirements
1. [Specific requirement 1]
2. [Specific requirement 2]
3. [Specific requirement 3]

### Code Patterns to Follow
- [Pattern 1 with example]
- [Pattern 2 with example]

### Testing Requirements
- Unit tests for [specific components]
- Integration tests for [specific flows]
- Performance tests for [specific metrics]

### Acceptance Criteria
- [ ] [Criterion 1]
- [ ] [Criterion 2]
- [ ] [Criterion 3]

### Files to Create/Modify
- `app/services/[service_name].py`
- `app/api/v1/endpoints/[endpoint_name].py`
- `tests/unit/test_[component].py`
```

#### From Augment Code to Human

**Completion Report Template:**
```markdown
## Implementation Complete: [Feature Name]

### What Was Implemented
[Summary of implemented functionality]

### Files Created/Modified
- [List of files with brief description of changes]

### Test Coverage
- Unit tests: [X]% coverage
- Integration tests: [Number] scenarios
- Performance tests: [Results]

### Known Issues/Limitations
- [Issue 1 with suggested resolution]
- [Issue 2 with suggested resolution]

### Next Steps
- [Suggested follow-up tasks]
- [Areas needing human review]
```

### Quality Assurance Protocols

#### Code Quality Standards

**All AI-Generated Code Must Include:**
- Type hints for all functions and methods
- Comprehensive docstrings with parameter descriptions
- Error handling with appropriate exception types
- Logging at appropriate levels
- Input validation and sanitization
- Performance considerations (async/await where applicable)

**Testing Requirements:**
- Unit tests for all public methods
- Integration tests for API endpoints
- Property-based testing for data validation
- Performance benchmarks for critical paths
- Error scenario testing

**Security Requirements:**
- Input validation and sanitization
- SQL injection prevention
- Authentication and authorization checks
- Secrets management (no hardcoded credentials)
- Rate limiting implementation
- Audit logging for sensitive operations

#### AI-to-AI Review Protocol

**When Claude Code Reviews Augment Code Output:**
1. Verify implementation follows architectural specifications
2. Check security patterns are correctly implemented
3. Validate error handling meets system standards
4. Assess performance implications
5. Ensure proper testing coverage

**When Augment Code Reviews Claude Code Output:**
1. Verify specifications are implementable
2. Check for missing implementation details
3. Identify potential performance bottlenecks
4. Suggest testing strategies
5. Highlight dependencies or prerequisites

### Communication Patterns

#### Effective Prompting for Claude Code

**Architecture/Design Prompts:**
```
Claude, design the [component] architecture for WebAgent with these requirements:
1. [Functional requirement 1]
2. [Non-functional requirement 2]
3. [Constraint 3]

Consider:
- Scalability to [specific metric]
- Security implications of [specific concern]
- Integration with [existing components]
- Performance requirements of [specific benchmark]

Provide:
- High-level architecture diagram
- Component interaction patterns
- Data flow specifications
- Error handling strategy
- Implementation roadmap for Augment Code
```

#### Effective Prompting for Augment Code

**Implementation Prompts:**
```
Augment, implement [feature] following Claude's architecture in [reference document].

Requirements:
1. [Specific implementation requirement]
2. [Testing requirement]
3. [Performance requirement]

Use these patterns:
- [Pattern 1 from codebase]
- [Pattern 2 from codebase]

Files to implement:
- [File 1]: [Purpose]
- [File 2]: [Purpose]

Ensure:
- 90%+ test coverage
- Proper error handling
- Async/await patterns
- Type hints and docstrings
```

### Development Workflow

#### Phase 1: Foundation (Completed by Claude Code)
✅ Project structure and configuration  
✅ Database schema design  
✅ Core models and schemas  
✅ FastAPI application structure  

#### Phase 2: Core Services (Claude Code → Augment Code)
**Claude Code Tasks:**
- Design WebParser service architecture
- Create TaskPlanner framework
- Define ActionExecutor patterns
- Plan SecurityManager implementation

**Augment Code Tasks:**
- Implement services following specifications
- Create comprehensive tests
- Add error handling and logging
- Optimize performance

#### Phase 3: Integration & Testing (Collaborative)
**Claude Code Tasks:**
- Design integration testing strategy
- Create end-to-end test scenarios
- Plan deployment architecture

**Augment Code Tasks:**
- Implement integration tests
- Create deployment scripts
- Add monitoring and alerting

### Documentation Standards

#### Architecture Documentation (Claude Code)
- System overview and component diagrams
- Data flow and interaction patterns
- Security model and threat analysis
- Performance characteristics and benchmarks
- Deployment and scaling strategies

#### Implementation Documentation (Augment Code)
- API endpoint documentation
- Service implementation details
- Testing guides and procedures
- Deployment and configuration guides
- Troubleshooting and debugging guides

### Error Escalation

#### When to Escalate to Human Developer

**From Claude Code:**
- Architectural decisions requiring business input
- Security implications beyond technical scope
- Resource/budget constraint decisions
- External integration complexity
- Conflicting requirements resolution

**From Augment Code:**
- Implementation blockers not resolvable with available specifications
- Test failures indicating architectural issues
- Performance issues requiring system-level changes
- External dependency integration problems
- Security concerns during implementation

#### Escalation Template
```markdown
## Issue Escalation: [Issue Title]

### Issue Type
[ ] Architecture Decision Needed
[ ] Implementation Blocker
[ ] Security Concern
[ ] Performance Issue
[ ] External Dependency

### Description
[Clear description of the issue]

### Context
[Relevant background and attempted solutions]

### Impact
[How this affects project timeline and scope]

### Recommendations
[Suggested approaches or solutions]

### Required Decision/Input
[Specific human input needed to proceed]
```

---

This collaboration guide ensures efficient AI-assisted development while maintaining high quality standards and clear accountability. Regular updates to this guide will be made based on practical experience and lessons learned during development.