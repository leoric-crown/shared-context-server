# Framework Integration Patterns

This guide provides established patterns for integrating with your primary framework, ensuring consistent architecture and maintainable code.

## Core Integration Principles

### Consistent Architecture
- Follow framework conventions for component organization
- Use framework-specific patterns for state management
- Leverage framework tools for dependency injection
- Maintain consistency with framework testing approaches

### Service Integration
- Use framework patterns for external service communication
- Implement proper error handling and fallback strategies
- Follow framework conventions for async operations
- Maintain consistent logging and monitoring patterns

## Common Integration Patterns

### Component Coordination
```python
# Example pattern - adapt to your framework
class ComponentCoordinator:
    def __init__(self, framework_context):
        self.context = framework_context
        self.components = {}
    
    async def coordinate_operation(self, operation_data):
        # Framework-specific coordination logic
        result = await self.context.process_operation(operation_data)
        return self.handle_result(result)
    
    def handle_result(self, result):
        # Framework-specific result handling
        return self.context.format_response(result)
```

### State Management
```python
# Example pattern - adapt to your framework
class StateManager:
    def __init__(self, framework_state):
        self.state = framework_state
    
    async def update_state(self, key, value):
        # Framework-specific state updates
        await self.state.update(key, value)
        self.notify_changes(key)
    
    def notify_changes(self, key):
        # Framework-specific change notification
        self.state.emit_change(key)
```

### Error Handling
```python
# Framework-agnostic error handling patterns
class ErrorHandler:
    def __init__(self, logger, framework_context):
        self.logger = logger
        self.context = framework_context
    
    async def handle_operation_error(self, error, context):
        # Log error with appropriate detail
        self.logger.error(f"Operation failed: {error}", extra=context)
        
        # Framework-specific error response
        return self.context.create_error_response(error)
```

## Data Handling Patterns

### Data Validation
```python
# Validation patterns using framework tools
def validate_input_data(data, schema):
    """Validate input using framework validation tools"""
    try:
        # Use framework-specific validation
        validated_data = framework.validate(data, schema)
        return validated_data, None
    except ValidationError as e:
        return None, str(e)
```

### Data Transformation
```python
# Consistent data transformation patterns
class DataTransformer:
    def __init__(self, framework_serializer):
        self.serializer = framework_serializer
    
    def transform_for_storage(self, data):
        """Transform data for storage using framework patterns"""
        return self.serializer.serialize(data)
    
    def transform_for_response(self, data):
        """Transform data for API response"""
        return self.serializer.format_response(data)
```

### Data Persistence
```python
# Framework-specific persistence patterns
class PersistenceManager:
    def __init__(self, framework_db):
        self.db = framework_db
    
    async def save_data(self, data):
        """Save data using framework persistence layer"""
        return await self.db.save(data)
    
    async def load_data(self, identifier):
        """Load data using framework query patterns"""
        return await self.db.find_by_id(identifier)
```

## Testing Integration

### Unit Testing Patterns
```python
# Framework-specific testing patterns
import pytest
from your_framework.testing import TestCase

class TestComponentIntegration(TestCase):
    def setUp(self):
        """Set up framework test environment"""
        self.framework_context = self.create_test_context()
        self.component = ComponentUnderTest(self.framework_context)
    
    async def test_component_operation(self):
        """Test component using framework testing tools"""
        result = await self.component.perform_operation("test_data")
        self.assert_framework_response(result, expected_format)
```

### Integration Testing
```python
# Integration testing with framework
class TestFrameworkIntegration:
    @pytest.fixture
    def framework_setup(self):
        """Set up complete framework environment"""
        return create_framework_test_environment()
    
    async def test_end_to_end_workflow(self, framework_setup):
        """Test complete workflow through framework"""
        workflow = Workflow(framework_setup)
        result = await workflow.execute_complete_flow()
        assert result.success
        assert result.data_preserved
```

## Performance Patterns

### Async Operations
```python
# Framework-specific async patterns
class AsyncOperationManager:
    def __init__(self, framework_async):
        self.async_manager = framework_async
    
    async def coordinate_async_operations(self, operations):
        """Coordinate multiple async operations efficiently"""
        tasks = [self.async_manager.create_task(op) for op in operations]
        results = await self.async_manager.gather(*tasks)
        return self.process_results(results)
```

### Caching Strategies
```python
# Framework-integrated caching
class CacheManager:
    def __init__(self, framework_cache):
        self.cache = framework_cache
    
    async def get_or_compute(self, key, compute_func):
        """Get from cache or compute and store"""
        cached_value = await self.cache.get(key)
        if cached_value is not None:
            return cached_value
        
        computed_value = await compute_func()
        await self.cache.set(key, computed_value)
        return computed_value
```

## Configuration Management

### Environment Configuration
```python
# Framework-specific configuration patterns
class ConfigManager:
    def __init__(self, framework_config):
        self.config = framework_config
    
    def get_database_url(self):
        """Get database URL from framework configuration"""
        return self.config.get('DATABASE_URL', 'sqlite:///default.db')
    
    def get_external_service_config(self, service_name):
        """Get external service configuration"""
        return self.config.get_service_config(service_name)
```

### Feature Flags
```python
# Framework-integrated feature management
class FeatureManager:
    def __init__(self, framework_features):
        self.features = framework_features
    
    def is_feature_enabled(self, feature_name):
        """Check if feature is enabled using framework feature flags"""
        return self.features.is_enabled(feature_name)
```

## Security Integration

### Authentication Patterns
```python
# Framework authentication integration
class AuthManager:
    def __init__(self, framework_auth):
        self.auth = framework_auth
    
    async def authenticate_request(self, request):
        """Authenticate request using framework auth system"""
        return await self.auth.verify_request(request)
    
    def require_permission(self, permission):
        """Decorator for permission-based access control"""
        return self.auth.require_permission(permission)
```

### Input Sanitization
```python
# Framework security patterns
class SecurityManager:
    def __init__(self, framework_security):
        self.security = framework_security
    
    def sanitize_input(self, user_input):
        """Sanitize user input using framework security tools"""
        return self.security.sanitize(user_input)
    
    def validate_csrf(self, request):
        """Validate CSRF token using framework protection"""
        return self.security.validate_csrf_token(request)
```

## Monitoring and Logging

### Structured Logging
```python
# Framework-integrated logging
import logging
from your_framework.logging import FrameworkLogger

class ApplicationLogger:
    def __init__(self):
        self.logger = FrameworkLogger(__name__)
    
    def log_operation(self, operation_name, context):
        """Log operation with structured context"""
        self.logger.info(
            f"Operation: {operation_name}",
            extra={
                'operation': operation_name,
                'context': context,
                'timestamp': datetime.now(timezone.utc)
            }
        )
```

### Metrics Collection
```python
# Framework metrics integration
class MetricsCollector:
    def __init__(self, framework_metrics):
        self.metrics = framework_metrics
    
    def record_operation_time(self, operation_name, duration):
        """Record operation timing using framework metrics"""
        self.metrics.timing(f'operation.{operation_name}', duration)
    
    def increment_counter(self, counter_name):
        """Increment counter using framework metrics"""
        self.metrics.increment(counter_name)
```

## Success Criteria

### Framework Integration Success
- All components use framework-specific patterns consistently
- Error handling follows framework conventions
- Testing uses framework testing tools effectively
- Configuration is managed through framework systems

### Code Quality Success
- Framework best practices are followed throughout
- No framework anti-patterns are used
- Framework features are used appropriately
- Performance is optimized using framework tools

### Maintainability Success
- Code is organized according to framework conventions
- Framework updates can be applied easily
- New developers can understand the codebase quickly
- Framework documentation patterns are followed

Remember: **Consistency with framework patterns is more important than clever solutions**. Follow established conventions, use framework tools appropriately, and maintain consistency across the entire codebase.