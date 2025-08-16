# Browser Automation with Playwright MCP

## Overview

Browser automation integration for the Claude Multi-Agent Framework using Playwright MCP server. Enables true user behavior validation, visual regression testing, and research-first web development patterns.

## Core Philosophy

**Behavioral Testing First**: Test what users experience, not implementation details. Browser automation validates that research-discovered patterns work in real user scenarios.

**Visual Quality Assurance**: Zero-tolerance for visual regressions. Every UI change must be validated through automated browser testing.

**Research-First Validation**: Use browser automation to validate that documented patterns and examples actually work in practice.

## Playwright MCP Tools Overview

### Navigation & Page Management

- `browser_navigate` - Navigate to URLs
- `browser_navigate_back/forward` - Browser history navigation
- `browser_tab_*` - Multi-tab management (list, new, select, close)
- `browser_close` - Clean browser shutdown
- `browser_resize` - Responsive testing

### User Interactions

- `browser_click` - Click elements (left, right, middle, double-click)
- `browser_type` - Text input with optional submission
- `browser_hover` - Hover interactions
- `browser_drag` - Drag and drop operations
- `browser_select_option` - Dropdown selections
- `browser_press_key` - Keyboard interactions

### Content Validation

- `browser_snapshot` - Accessibility-focused page snapshots (preferred for actions)
- `browser_take_screenshot` - Visual capture (full page or element-specific)
- `browser_evaluate` - JavaScript execution and evaluation

### Advanced Features

- `browser_file_upload` - File upload testing
- `browser_wait_for` - Wait for text appearance/disappearance or time delays
- `browser_handle_dialog` - Dialog interaction (alerts, confirms, prompts)
- `browser_console_messages` - Console log monitoring
- `browser_network_requests` - Network traffic analysis

## Integration Patterns

### 1. Behavioral Test Workflows

```markdown
## User Story Validation Pattern

1. **Setup**: Navigate to application state
2. **Action**: Perform user actions via browser automation
3. **Validation**: Verify expected outcomes using snapshots/screenshots
4. **Cleanup**: Reset state for next test

Example: Login Flow Testing
- Navigate to login page
- Fill credentials via browser_type
- Click login button via browser_click
- Validate dashboard appearance via browser_snapshot
- Screenshot comparison for visual regression
```

### 2. Research Validation Pattern

```markdown
## Documentation Pattern Verification

1. **Research**: Find implementation patterns via MCP tools
2. **Implementation**: Apply patterns in codebase
3. **Browser Validation**: Verify patterns work via Playwright
4. **Documentation**: Capture working examples with screenshots

Example: CSS Framework Integration
- Research component patterns via Crawl4AI
- Implement components in codebase
- Validate rendering via browser_screenshot
- Capture visual examples for documentation
```

### 3. Visual Regression Prevention

```markdown
## Zero-Regression Protocol

1. **Baseline**: Capture reference screenshots before changes
2. **Implementation**: Make code changes
3. **Comparison**: Capture new screenshots
4. **Validation**: Compare for visual differences
5. **Approval**: Manual review of intentional changes

Tools: browser_take_screenshot with element targeting
```

### 4. Multi-Device Testing

```markdown
## Responsive Validation Pattern

1. **Desktop**: Test at 1920x1080 via browser_resize
2. **Tablet**: Test at 768x1024 via browser_resize
3. **Mobile**: Test at 375x667 via browser_resize
4. **Validation**: Ensure layout integrity across sizes

Automation: Loop through device sizes with screenshot capture
```

## Agent-Specific Integration

### Tester Agent Enhancement

The `tester` agent becomes the primary browser automation user:

```markdown
## Enhanced Capabilities

**Behavioral Testing**: Use Playwright for user-centric test scenarios
**Visual Validation**: Screenshot-based regression testing
**Accessibility Testing**: Leverage browser_snapshot for a11y validation
**Performance Monitoring**: Network request analysis via browser_network_requests

## Tool Priority
1. browser_snapshot (for understanding page state)
2. browser_click/type (for user interactions)
3. browser_take_screenshot (for visual validation)
4. browser_evaluate (for custom validation logic)
```

### Developer Agent Support

The `developer` agent can use browser automation for implementation validation:

```markdown
## Research-First Validation

**Pattern Verification**: Test that researched patterns work in browsers
**Component Testing**: Validate new components render correctly
**Integration Testing**: Ensure components work together visually
**Debug Assistance**: Use console_messages for runtime debugging

## Common Workflows
- Implement component → browser_navigate → browser_snapshot → validate
- Research pattern → implement → browser_screenshot → compare
- Fix bug → browser_evaluate → verify fix → screenshot
```

## Development Standards Integration

### Browser Testing Requirements

```markdown
## Quality Standards

**Visual Regression**: Zero tolerance for unintended visual changes
**Accessibility**: All UI changes must pass browser_snapshot validation
**Cross-Browser**: Test in multiple environments when possible
**Performance**: Monitor network requests for performance impacts

## Test Categories
1. **Smoke Tests**: Basic functionality via browser navigation
2. **User Flows**: Complete user scenarios via interaction chains
3. **Visual Tests**: Screenshot-based regression detection
4. **Accessibility Tests**: Snapshot-based a11y validation
```

### Escalation Triggers

```markdown
## When to Escalate

**Visual Regressions**: Unexpected visual changes detected
**Accessibility Issues**: browser_snapshot reveals a11y problems
**Performance Degradation**: Network analysis shows slowdowns
**Browser Compatibility**: Cross-browser testing failures

## Browser-Specific Concerns
- JavaScript errors via console_messages
- Network failures via network_requests
- Dialog handling issues
- File upload complications
```

## Framework Commands Integration

### Enhanced Feature Planning

```markdown
## Browser Testing Considerations

When planning features that involve UI:
1. Define visual validation requirements
2. Plan responsive testing approach
3. Identify accessibility testing needs
4. Design visual regression prevention

Integration: Add browser testing steps to feature-planning command
```

### PRP Generation Enhancement

```markdown
## Browser Automation PRPs

Include browser testing specifications:
- User interaction scenarios
- Visual validation checkpoints
- Responsive testing requirements
- Accessibility validation steps

Format: Executable test scenarios with Playwright commands
```

## Common Patterns & Examples

### 1. Form Testing Pattern

```markdown
## Complete Form Validation

1. browser_navigate(form_url)
2. browser_type(name_field, "Test User")
3. browser_type(email_field, "test@example.com")
4. browser_select_option(country_dropdown, ["United States"])
5. browser_click(submit_button)
6. browser_wait_for(success_message)
7. browser_take_screenshot(confirmation_page)
```

### 2. Multi-Step User Journey

```markdown
## E-commerce Purchase Flow

1. browser_navigate(product_page)
2. browser_click(add_to_cart)
3. browser_navigate(cart_page)
4. browser_click(checkout_button)
5. browser_type(payment_form, payment_data)
6. browser_click(complete_purchase)
7. browser_snapshot() # Final state validation
```

### 3. Visual Component Testing

```markdown
## Component Isolation Testing

1. browser_navigate(component_demo_page)
2. browser_resize(1920, 1080) # Desktop
3. browser_take_screenshot(component_element)
4. browser_resize(768, 1024) # Tablet
5. browser_take_screenshot(component_element)
6. Compare screenshots for responsive behavior
```

## MCP Permission Configuration

Add to `settings.local.template.json`:

```json
{
  "permissions": {
    "allow": [
      "mcp__playwright__browser_navigate",
      "mcp__playwright__browser_navigate_back",
      "mcp__playwright__browser_navigate_forward",
      "mcp__playwright__browser_click",
      "mcp__playwright__browser_type",
      "mcp__playwright__browser_hover",
      "mcp__playwright__browser_drag",
      "mcp__playwright__browser_select_option",
      "mcp__playwright__browser_press_key",
      "mcp__playwright__browser_snapshot",
      "mcp__playwright__browser_take_screenshot",
      "mcp__playwright__browser_evaluate",
      "mcp__playwright__browser_file_upload",
      "mcp__playwright__browser_wait_for",
      "mcp__playwright__browser_handle_dialog",
      "mcp__playwright__browser_console_messages",
      "mcp__playwright__browser_network_requests",
      "mcp__playwright__browser_tab_list",
      "mcp__playwright__browser_tab_new",
      "mcp__playwright__browser_tab_select",
      "mcp__playwright__browser_tab_close",
      "mcp__playwright__browser_close",
      "mcp__playwright__browser_resize",
      "mcp__playwright__browser_install"
    ]
  }
}
```

## Best Practices

### 1. Prefer browser_snapshot over browser_take_screenshot

- More semantic information available
- Better for understanding page state
- Accessibility information included

### 2. Use Targeted Screenshots

- Element-specific screenshots for focused validation
- Full-page screenshots for layout validation
- Multiple device sizes for responsive testing

### 3. Wait Strategies

- Use browser_wait_for for dynamic content
- Wait for specific text/elements rather than arbitrary timeouts
- Validate state changes after interactions

### 4. Error Handling

- Monitor console_messages for JavaScript errors
- Use network_requests to detect API failures
- Handle dialogs appropriately with browser_handle_dialog

### 5. State Management

- Start each test from known state
- Use navigation to reset application state
- Clean up browser tabs between tests

## Integration with Existing Workflows

### Visual Validation Workflow Enhancement

Extend `workflows/visual-validation.md`:

```markdown
## Playwright-Enhanced Visual Validation

1. **Baseline Capture**: browser_take_screenshot before changes
2. **Implementation**: Make code changes
3. **Validation Capture**: browser_take_screenshot after changes
4. **Comparison**: Visual diff analysis
5. **Documentation**: Capture final screenshots for records

Automation: Script-driven visual regression testing
```

### Framework Commands Enhancement

Update existing commands to include browser testing:

- `feature-planning`: Include UI testing requirements
- `generate-prp`: Add browser automation specifications
- `execute-prp`: Include browser validation steps

## Technology Stack Adaptation

### Web Framework Integration

```markdown
## Framework-Specific Patterns

**React Applications**
- Component testing via navigation to Storybook
- State validation via browser_evaluate
- Hook testing through user interactions

**Vue Applications**
- Component isolation testing
- Reactive state validation
- Event handling verification

**Backend Applications**
- API documentation testing via browser automation
- Admin interface validation
- Health check page verification
```

## Troubleshooting & Common Issues

### 1. Browser Installation

- Use `browser_install` if browser not found
- Verify MCP server configuration
- Check permission settings

### 2. Element Selection

- Use browser_snapshot to understand page structure
- Prefer semantic selectors over brittle ones
- Wait for dynamic content to load

### 3. Network Issues

- Monitor browser_network_requests for API failures
- Handle slow network conditions with appropriate waits
- Validate API responses via browser evaluation

### 4. Cross-Platform Differences

- Account for OS-specific browser behaviors
- Test keyboard interactions across platforms
- Validate file upload behaviors

## Success Metrics

- **Zero Visual Regressions**: No unintended UI changes
- **Complete User Journey Coverage**: All critical paths tested
- **Accessibility Compliance**: All UI changes validated
- **Performance Maintained**: No browser-detected slowdowns
- **Cross-Device Compatibility**: Responsive design verified

## Future Enhancements

- **AI-Powered Visual Testing**: Automated visual difference detection
- **Cross-Browser Automation**: Multi-browser testing orchestration
- **Performance Monitoring**: Automated performance regression detection
- **Accessibility Automation**: Enhanced a11y testing capabilities
