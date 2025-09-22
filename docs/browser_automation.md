# Browser Automation System

The AI-Powered Migration Validation System includes a robust browser automation engine that integrates Playwright and browser-use for comprehensive behavioral validation of migrated web applications.

## Architecture Overview

The browser automation system consists of several key components:

### Core Components

1. **BrowserAutomationEngine** - Main automation engine using Playwright
2. **BrowserTool** - CrewAI tool integration for agent-based automation
3. **BrowserAction** - Structured action definitions
4. **BrowserSession** - Session management and tracking

### Integration Points

- **CrewAI Agents** - Source exploration and target execution agents
- **Playwright** - Core browser automation and control
- **browser-use** - Intelligent AI-powered browser interactions
- **Validation Pipeline** - Behavioral comparison and reporting

## Key Features

### 🎯 Intelligent Browser Control

- **Multi-browser Support** - Chromium, Firefox, and WebKit
- **Headless Operation** - Production-ready headless browser execution
- **AI-Enhanced Interactions** - browser-use integration for intelligent actions
- **Session Management** - Structured session tracking and persistence

### 🔧 Comprehensive Action Types

| Action Type | Purpose | Example Usage |
|-------------|---------|---------------|
| `navigate` | Page navigation | `navigate:https://example.com` |
| `click` | Element interaction | `click:button#submit` |
| `fill` | Form field input | `fill:input[name="email"]:test@example.com` |
| `submit` | Form submission | `submit:form#login` |
| `wait` | Timing control | `wait:selector` or `wait::2000` |
| `capture` | Screenshot generation | `capture` or `capture:selector` |
| `evaluate` | JavaScript execution | `evaluate:document.title` |
| `intelligent` | AI-powered interaction | `intelligent:description` |
| `authenticate` | Login automation | `authenticate:user:pass:url` |
| `capture_state` | Page state extraction | `capture_state` |
| `scenario` | Pre-defined workflows | `scenario:login:user:pass:url` |

### 📊 State Capture & Comparison

- **Comprehensive Page State** - Forms, elements, messages, metrics
- **Visual Documentation** - Automated screenshot capture
- **Behavioral Tracking** - User interaction patterns and timing
- **Discrepancy Detection** - Automated comparison and validation

## Usage Examples

### Basic Browser Automation

```python
from src.behavioral.browser_automation import BrowserAutomationEngine, BrowserAction

# Initialize browser automation
async with BrowserAutomationEngine() as engine:
    # Start session
    session_id = await engine.start_session("https://example.com")

    # Execute actions
    action = BrowserAction(
        action_type="navigate",
        target="https://example.com/login",
        description="Navigate to login page"
    )

    result = await engine.execute_action(action)

    # Capture page state
    state = await engine.capture_page_state()

    # End session
    session = await engine.end_session()
```

### CrewAI Tool Integration

```python
from src.behavioral.crews import BrowserTool

# Initialize browser tool
tool = BrowserTool()

# Execute actions through tool interface
result = tool._run("navigate:https://example.com")
result = tool._run("fill:input[name='username']:testuser")
result = tool._run("click:button[type='submit']")
result = tool._run("capture_state")
```

### Pre-defined Scenarios

```python
from src.behavioral.browser_automation import (
    create_login_scenario,
    create_form_submission_scenario
)

# Create login scenario
login_actions = create_login_scenario(
    username="testuser",
    password="testpass",
    login_url="https://example.com/login"
)

# Create form submission scenario
form_data = {"name": "John Doe", "email": "john@example.com"}
form_actions = create_form_submission_scenario("#contact-form", form_data)

# Execute scenarios
async with BrowserAutomationEngine() as engine:
    await engine.start_session("https://example.com")

    login_results = await engine.execute_scenario("login", login_actions)
    form_results = await engine.execute_scenario("contact", form_actions)
```

## Migration Validation Workflow

### 1. Source System Exploration

The SourceExplorerAgent uses the browser automation system to:

- Navigate through the source system
- Execute predefined behavioral scenarios
- Capture page states and screenshots
- Document user interaction patterns
- Test error conditions and edge cases

### 2. Target System Execution

The TargetExecutorAgent replicates the exact same actions:

- Follows identical navigation patterns
- Uses same input data and selectors
- Captures parallel documentation
- Measures performance characteristics
- Tests identical error scenarios

### 3. Behavioral Comparison

The ComparisonJudgeAgent analyzes the captured data:

- Compares page states for structural differences
- Analyzes screenshots for visual consistency
- Evaluates performance metrics
- Identifies behavioral discrepancies
- Generates validation reports

## Advanced Features

### Authentication Support

```python
# Built-in authentication
success = await engine.authenticate(
    username="testuser",
    password="testpass",
    login_url="https://example.com/login"
)

# Custom selectors
success = await engine.authenticate(
    username="testuser",
    password="testpass",
    username_selector="input#email",
    password_selector="input#password",
    submit_selector="button.login-btn"
)
```

### State Comparison

```python
# Capture states from both systems
source_state = await source_engine.capture_page_state()
target_state = await target_engine.capture_page_state()

# Compare and identify discrepancies
discrepancies = await engine.compare_page_states(source_state, target_state)

# Analyze discrepancies
for disc in discrepancies:
    print(f"{disc.severity}: {disc.description}")
    print(f"Recommendation: {disc.recommendation}")
```

### Performance Monitoring

```python
# Action-level timing
result = await engine.execute_action(action)
print(f"Execution time: {result.execution_time:.2f}s")

# Session-level metrics
session = await engine.end_session()
print(f"Total duration: {session.duration:.1f}s")
print(f"Actions executed: {len(session.actions)}")
```

## Configuration Options

### Browser Engine Configuration

```python
engine = BrowserAutomationEngine(
    headless=True,          # Run in headless mode
    slow_mo=100,           # Slow down operations (ms)
    timeout=30000          # Default timeout (ms)
)

# Browser-specific options
await engine.initialize(browser_type="chromium")  # or "firefox", "webkit"
```

### Context Configuration

- **Viewport Size** - 1920x1080 default
- **Security Settings** - Ignore HTTPS errors
- **JavaScript** - Enabled by default
- **Downloads** - Accepted automatically
- **Video Recording** - Optional for debugging

## Error Handling & Resilience

### Graceful Degradation

- Fallback when browser-use is unavailable
- Automatic retry for network-related failures
- Comprehensive error logging and reporting
- Resource cleanup on failures

### Production Considerations

- **Resource Management** - Automatic cleanup of browser instances
- **Memory Optimization** - Efficient screenshot and state management
- **Concurrency** - Support for parallel browser sessions
- **Error Recovery** - Robust error handling and reporting

## Testing & Validation

### Test Suite

Run the browser automation tests:

```bash
# Run specific browser automation tests
pytest tests/test_browser_automation.py -v

# Run demo script
python tests/test_browser_automation.py
```

### Demo Script

The included demo script (`tests/test_browser_automation.py`) demonstrates:

- Browser initialization and configuration
- Basic navigation and interaction
- Form submission testing
- State capture and screenshot generation
- Session management and cleanup

## Troubleshooting

### Common Issues

1. **Browser Not Available**
   - Install Playwright browsers: `playwright install`
   - Check system dependencies

2. **Network Timeouts**
   - Increase timeout values
   - Check network connectivity
   - Verify target URLs are accessible

3. **Element Not Found**
   - Verify CSS selectors
   - Add wait conditions
   - Check for dynamic content loading

4. **Performance Issues**
   - Use headless mode in production
   - Optimize screenshot capture frequency
   - Implement proper session cleanup

### Debug Mode

Enable debug logging:

```python
import structlog
structlog.configure(level="DEBUG")

# Run with verbose browser output
engine = BrowserAutomationEngine(headless=False, slow_mo=1000)
```

## Integration with CrewAI

The browser automation system seamlessly integrates with the CrewAI agent framework:

### Agent Configuration

```python
class SourceExplorerAgent:
    def __init__(self, llm_service: LLMService):
        self.browser_tool = BrowserTool()

        self.agent = Agent(
            role="Source System Explorer",
            tools=[self.browser_tool],
            # ... other configuration
        )
```

### Task Execution

```python
def create_exploration_task(self, source_url: str, scenarios: List[str]) -> Task:
    return Task(
        description=f"""
        Use the browser_tool to systematically test each scenario:

        1. START SESSION: Use "session:start:{source_url}"
        2. NAVIGATE: Use "navigate:{source_url}"
        3. CAPTURE STATE: Use "capture_state"

        For each scenario:
        - Use "click:selector", "fill:selector:value"
        - Use "capture" for screenshots
        - Use "scenario:login:user:pass:url" for authentication
        """,
        agent=self.agent
    )
```

This comprehensive browser automation system provides the foundation for robust behavioral validation in the AI-Powered Migration Validation System, enabling precise comparison between source and target systems through automated browser testing.