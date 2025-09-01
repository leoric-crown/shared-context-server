---
session_id: session_243dcbc33f72467c
session_purpose: "PRP creation: UI Auto-scroll Improvements for shared-context-server web dashboard"
created_date: 2025-08-31T18:54:00+00:00
stage: "2-prps"
planning_source: session_f98bd607ce594fbb
planning_contributors: ["codex-cli-assistant", "cursor-analyst"]
---

# PRP: UI Auto-Scroll Improvements

## Research Context & Architectural Analysis

**Research Integration**: Comprehensive multi-agent research completed in planning session `session_f98bd607ce594fbb`. Industry research conducted on WebSocket patterns, auto-scroll UX best practices, and Jinja template integration. Key findings include Discord/Slack auto-scroll patterns, 64px threshold for "at bottom" detection, and template-scoped WebSocket management approaches.

**Architectural Scope**: Focused on shared-context-server web dashboard session views. Integration required across WebSocket real-time messaging, frontend JavaScript scroll detection, backend notification filtering, and existing markdown rendering systems.

**Existing Patterns**: Leverages established patterns including template-scoped WebSocket connections (session_view.html:442-553), Bootstrap CSS styling, Jinja variable injection, and DOMPurify sanitization for markdown content.

## Implementation Specification

### Core Requirements

**Primary Problem**: Session views currently perform full page reloads (`window.location.reload()`) on WebSocket `session_update` events, causing jarring user experience especially with long messages or histories. Users reading previous messages lose their position when new messages arrive.

**Core Functionality to Implement**:
1. **Eliminate Page Reloads**: Remove `window.location.reload()` from WebSocket `session_update` handler (session_view.html:551)
2. **Smart Auto-Scroll**: Implement scroll position detection with 64px "at bottom" threshold
3. **User Control**: Add "Jump to latest" button that appears when user scrolls up from bottom
4. **Consistent Rendering**: Ensure new messages use same markdown rendering as server-rendered history
5. **WebSocket Optimization**: Prevent duplicate WebSocket connections, maintain heartbeat and reconnection

### Integration Points

**Frontend Integration** (session_view.html):
- **WebSocket Handler**: Modify `handleRealtimeMessage()` function (lines 544-553)
- **Scroll Detection**: Add debounced scroll event handlers to `#messages-list` container
- **UI Controls**: Integrate "Jump to latest" button into existing `session-header-controls` (lines 17-27)
- **Message Rendering**: Enhance `addNewMessage()` function with markdown processing consistency

**Backend Integration** (admin_resources.py):
- **Notification Filtering**: Modify `trigger_resource_notifications()` (lines 361-393) to stop broadcasting `session_update` for normal message additions
- **Event Types**: Reserve `session_update` broadcasts for structural/metadata changes only
- **WebSocket Messages**: Maintain existing `new_message` broadcast pattern for live message updates

### Data Model Changes

**No Database Schema Changes Required**: All functionality builds on existing message storage and WebSocket infrastructure.

**JavaScript State Management**:
```javascript
// New state variables to add
let isAtBottom = true;           // Track user scroll position
let autoScrollEnabled = true;    // Track auto-scroll preference
let unreadCount = 0;            // Count messages when scrolled up
let scrollDetectionTimeout;     // Debounce scroll events
```

### Interface Requirements

**Enhanced Header Controls**:
```html
<!-- Add to existing session-header-controls -->
<button class="btn btn-primary auto-follow-toggle" id="auto-follow-toggle"
        onclick="jumpToLatest()" data-tooltip="Jump to latest messages"
        style="display: none;">
    <span class="btn-icon">↓</span>
    <span class="btn-text">Jump to latest</span>
    <span class="unread-badge" id="unread-count" style="display: none;">0</span>
</button>
```

**Scroll Detection Logic**:
```javascript
function isAtBottomOfContainer(element, threshold = 64) {
    return (element.scrollHeight - element.scrollTop - element.clientHeight) < threshold;
}

function handleSmartAutoScroll(messageElement) {
    const messagesList = document.getElementById('messages-list');
    const wasAtBottom = isAtBottomOfContainer(messagesList);

    if (wasAtBottom && autoScrollEnabled) {
        messageElement.scrollIntoView({ behavior: 'smooth', block: 'end' });
    } else {
        showJumpToLatestButton();
        incrementUnreadCount();
    }
}
```

## Quality Requirements

### Testing Strategy

**Behavioral Testing Approach**:
1. **Cross-Browser Compatibility**: Test scroll detection across Chrome, Firefox, Safari (latest 2 versions)
2. **Message Scenarios**: Validate with long messages (>100 lines), rapid message bursts, large histories (>1k messages)
3. **User Interaction Patterns**: Test manual scroll up, accidental scroll, touch/mobile scrolling, keyboard navigation
4. **WebSocket Resilience**: Verify functionality during connection drops, reconnections, and network instability
5. **Accessibility Validation**: Screen reader compatibility, keyboard navigation, ARIA labels

**Specific Test Cases**:
- User scrolls up to read previous messages → auto-scroll disables, "Jump to latest" appears
- User at bottom when new message arrives → smooth scroll to new message
- User clicks "Jump to latest" → smooth scroll to bottom, auto-scroll re-enables
- Page reload/reconnect → maintain user's scroll position preference
- Large message batch → no scroll jank or performance degradation

### Documentation Needs

**User-Facing Documentation**: Update session interaction guide to explain auto-scroll behavior and "Jump to latest" functionality.

**Developer Documentation**: Document WebSocket message flow changes and scroll detection implementation patterns for future maintenance.

### Performance Considerations

**Scroll Performance**: Implement debounced scroll handlers (100ms) to prevent excessive calculations during rapid scrolling.

**Memory Management**: Ensure proper cleanup of scroll event listeners and timeout handlers to prevent memory leaks.

**Large History Handling**: Maintain existing performance characteristics for sessions with extensive message histories.

## Coordination Strategy

### Recommended Approach: **Single cfw-developer Agent**

**Rationale**:
- **Research Complete**: Comprehensive planning eliminates need for additional research coordination
- **Tight Integration**: Frontend JavaScript and backend WebSocket changes are interdependent
- **Established Patterns**: All modifications build on well-documented existing architecture
- **Cohesive Implementation**: Single agent maintains full context of data flow and user experience requirements

### Implementation Phases

**Phase 1: Core Functionality (Day 1)**
1. Remove `window.location.reload()` from `session_update` handler
2. Implement basic scroll position detection with 64px threshold
3. Add WebSocket message filtering in `admin_resources.py`
4. Verify no functionality regression in existing session behavior

**Phase 2: Enhanced UX (Day 2)**
1. Add "Jump to latest" button with unread counter to header controls
2. Implement smooth scroll animations and user state management
3. Ensure consistent markdown rendering for new messages
4. Add debounced scroll detection and performance optimizations

**Phase 3: Polish & Validation (Day 3)**
1. Cross-browser testing and mobile scroll handling
2. Accessibility improvements (ARIA labels, keyboard shortcuts)
3. Performance validation with large message histories
4. Documentation updates and implementation notes

### Risk Mitigation

**Progressive Enhancement Strategy**: New functionality enhances existing behavior without replacing core features. Users can still manually refresh if needed.

**Feature Toggle Ready**: Implementation allows for easy rollback via JavaScript feature detection or server-side configuration.

**Backward Compatibility**: Preserve all existing WebSocket connection management, authentication patterns, and UI navigation functionality.

## Success Criteria

### Functional Success

**Core Behaviors**:
- ✅ Zero full page reloads during normal session usage
- ✅ Users reading previous messages are not interrupted by new message arrivals
- ✅ Users at bottom of messages continue to see new messages automatically
- ✅ "Jump to latest" functionality provides smooth navigation back to live updates
- ✅ All existing markdown rendering, syntax highlighting, and formatting preserved

### Integration Success

**System Integration Validation**:
- ✅ WebSocket connection stability maintained across all browsers
- ✅ Heartbeat and reconnection logic continues to function properly
- ✅ Real-time message delivery maintains sub-second latency
- ✅ No memory leaks or performance degradation with extended session usage
- ✅ Existing session navigation, copying, and sharing functionality unchanged

### Quality Gates

**Testing & Validation Requirements**:
- ✅ Automated testing coverage for scroll detection logic and WebSocket integration
- ✅ Manual validation across target browsers and devices (desktop + mobile)
- ✅ Accessibility compliance verification with screen readers and keyboard navigation
- ✅ Performance benchmarking with large message histories (1000+ messages)
- ✅ User acceptance testing of enhanced workflow without learning curve

**Documentation Validation**:
- ✅ Implementation patterns documented for future maintenance
- ✅ User-facing behavior changes explained in session interaction guides
- ✅ WebSocket message flow changes documented in architecture notes

`★ Insight ─────────────────────────────────────`
This PRP transforms a complex multi-agent planning discussion into a concrete, single-agent implementation specification. The comprehensive research and architectural analysis enables intelligent coordination by providing the cfw-developer agent with complete context about integration requirements, risk factors, and quality expectations - eliminating the need for additional discovery phases.
`─────────────────────────────────────────────────`
