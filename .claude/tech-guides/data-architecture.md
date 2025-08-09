# Data Architecture Patterns

[ADAPT: This guide establishes patterns for data handling based on detected project architecture and data requirements.]

## Core Data Principles

### [ADAPT: Data Preservation - include if data persistence or transformation detected]
- **Never lose original data** - [ADAPT: Relevant if data transformation or processing detected]
- **Additive changes** - [ADAPT: Include if data modification workflows detected]
- **Change tracking** - [ADAPT: Include if audit trails or versioning detected]
- **Rollback capability** - [ADAPT: Include if data recovery requirements detected]

### Data Consistency
- **UTC timestamps** - [ADAPT: Include if time-based functionality detected]
- **Consistent data types** - [ADAPT: Types based on detected language and data patterns]
- **Validation at boundaries** - [ADAPT: Validation patterns based on detected input handling]
- **Transaction boundaries** - [ADAPT: Include if database or transactional operations detected]

## Data Models

# [ADAPT: Base Data Models - replace with language-appropriate patterns]

```python
# [ADAPT: Imports based on detected language and data handling libraries]
from datetime import datetime, timezone
from dataclasses import dataclass  # [ADAPT: Or Pydantic, attrs, etc. based on detected patterns]
from typing import Optional, Dict, Any

@dataclass
class BaseDataModel:  # [ADAPT: Use detected naming patterns and base class structure]
    """[ADAPT: Base model description based on detected data patterns]"""
    id: str
    # [ADAPT: Include timestamp fields only if time-based functionality detected]
    created_at: datetime
    updated_at: Optional[datetime] = None
    # [ADAPT: Metadata field based on detected extensibility patterns]
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        # [ADAPT: Initialization logic based on detected patterns]
        if self.metadata is None:
            self.metadata = {}
        
        # [ADAPT: UTC timestamp handling - include only if time functionality detected]
        if self.created_at.tzinfo is None:
            self.created_at = self.created_at.replace(tzinfo=timezone.utc)
        
        if self.updated_at and self.updated_at.tzinfo is None:
            self.updated_at = self.updated_at.replace(tzinfo=timezone.utc)
```

### Data Preservation Models
```python
@dataclass
class DataWithHistory:
    """Data model that preserves change history"""
    current_data: Dict[str, Any]
    original_data: Dict[str, Any]
    change_history: List[Dict[str, Any]]
    
    def add_change(self, change_type: str, changes: Dict[str, Any], author: str = None):
        """Add a change to the history"""
        change_record = {
            "timestamp": datetime.now(timezone.utc),
            "change_type": change_type,
            "changes": changes,
            "author": author,
            "previous_state": self.current_data.copy()
        }
        self.change_history.append(change_record)
    
    def rollback_to_version(self, version_index: int):
        """Rollback to a specific version in history"""
        if 0 <= version_index < len(self.change_history):
            target_state = self.change_history[version_index]["previous_state"]
            self.current_data = target_state.copy()
            return True
        return False
```

### Validation Models
```python
from typing import Union, List
from enum import Enum

class ValidationResult:
    """Result of data validation operations"""
    def __init__(self, is_valid: bool, errors: List[str] = None, warnings: List[str] = None):
        self.is_valid = is_valid
        self.errors = errors or []
        self.warnings = warnings or []
    
    def add_error(self, error: str):
        """Add validation error"""
        self.errors.append(error)
        self.is_valid = False
    
    def add_warning(self, warning: str):
        """Add validation warning"""
        self.warnings.append(warning)

def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> ValidationResult:
    """Validate that required fields are present"""
    result = ValidationResult(True)
    
    for field in required_fields:
        if field not in data or data[field] is None:
            result.add_error(f"Required field '{field}' is missing")
    
    return result
```

## Data Persistence Patterns

### File-Based Persistence
```python
import json
import os
from pathlib import Path
from typing import Optional

class FileDataPersistence:
    """File-based data persistence with atomic operations"""
    
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def save_data(self, identifier: str, data: Dict[str, Any]) -> bool:
        """Save data with atomic write operation"""
        file_path = self.base_path / f"{identifier}.json"
        temp_path = self.base_path / f"{identifier}.json.tmp"
        
        try:
            # Write to temporary file first
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=self._json_serializer)
            
            # Atomic move to final location
            temp_path.replace(file_path)
            return True
            
        except Exception as e:
            # Clean up temp file if it exists
            if temp_path.exists():
                temp_path.unlink()
            raise e
    
    def load_data(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Load data from file"""
        file_path = self.base_path / f"{identifier}.json"
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return None
    
    def _json_serializer(self, obj):
        """Custom JSON serializer for datetime objects"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")
```

### Backup and Recovery
```python
class DataBackupManager:
    """Manage data backups and recovery"""
    
    def __init__(self, data_path: str, backup_path: str):
        self.data_path = Path(data_path)
        self.backup_path = Path(backup_path)
        self.backup_path.mkdir(parents=True, exist_ok=True)
    
    def create_backup(self, backup_name: str = None) -> str:
        """Create a backup of current data"""
        if backup_name is None:
            backup_name = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        
        backup_dir = self.backup_path / backup_name
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy all data files to backup
        for data_file in self.data_path.glob("*.json"):
            backup_file = backup_dir / data_file.name
            backup_file.write_bytes(data_file.read_bytes())
        
        return backup_name
    
    def restore_backup(self, backup_name: str) -> bool:
        """Restore data from backup"""
        backup_dir = self.backup_path / backup_name
        
        if not backup_dir.exists():
            return False
        
        try:
            # Clear current data
            for data_file in self.data_path.glob("*.json"):
                data_file.unlink()
            
            # Restore from backup
            for backup_file in backup_dir.glob("*.json"):
                data_file = self.data_path / backup_file.name
                data_file.write_bytes(backup_file.read_bytes())
            
            return True
        except Exception:
            return False
```

## Data Transformation Patterns

### Safe Data Transformation
```python
class DataTransformer:
    """Transform data while preserving original"""
    
    def __init__(self, preserve_original: bool = True):
        self.preserve_original = preserve_original
    
    def transform_data(self, data: Dict[str, Any], transformations: List[callable]) -> Dict[str, Any]:
        """Apply transformations while preserving original data"""
        if self.preserve_original:
            # Create preserved version
            preserved_data = {
                "original_data": data.copy(),
                "transformed_data": data.copy(),
                "transformations_applied": [],
                "transformation_metadata": {
                    "timestamp": datetime.now(timezone.utc),
                    "transformation_count": len(transformations)
                }
            }
            
            working_data = preserved_data["transformed_data"]
        else:
            working_data = data.copy()
        
        # Apply transformations
        for i, transformation in enumerate(transformations):
            try:
                working_data = transformation(working_data)
                if self.preserve_original:
                    preserved_data["transformations_applied"].append({
                        "step": i + 1,
                        "transformation": transformation.__name__,
                        "timestamp": datetime.now(timezone.utc)
                    })
            except Exception as e:
                if self.preserve_original:
                    preserved_data["transformation_error"] = {
                        "step": i + 1,
                        "transformation": transformation.__name__,
                        "error": str(e),
                        "timestamp": datetime.now(timezone.utc)
                    }
                raise e
        
        return preserved_data if self.preserve_original else working_data
```

### Data Migration Patterns
```python
class DataMigration:
    """Handle data format migrations"""
    
    def __init__(self, version_tracker: str):
        self.version_tracker = version_tracker
        self.migrations = {}
    
    def register_migration(self, from_version: str, to_version: str, migration_func: callable):
        """Register a migration function"""
        self.migrations[(from_version, to_version)] = migration_func
    
    def migrate_data(self, data: Dict[str, Any], target_version: str) -> Dict[str, Any]:
        """Migrate data to target version"""
        current_version = data.get(self.version_tracker, "1.0.0")
        
        if current_version == target_version:
            return data
        
        # Find migration path
        migration_key = (current_version, target_version)
        
        if migration_key not in self.migrations:
            raise ValueError(f"No migration path from {current_version} to {target_version}")
        
        # Apply migration
        migration_func = self.migrations[migration_key]
        migrated_data = migration_func(data.copy())
        
        # Update version
        migrated_data[self.version_tracker] = target_version
        migrated_data["migration_history"] = data.get("migration_history", [])
        migrated_data["migration_history"].append({
            "from_version": current_version,
            "to_version": target_version,
            "timestamp": datetime.now(timezone.utc)
        })
        
        return migrated_data
```

## Data Quality Patterns

### Data Validation Pipeline
```python
class DataValidationPipeline:
    """Pipeline for comprehensive data validation"""
    
    def __init__(self):
        self.validators = []
    
    def add_validator(self, validator: callable, name: str = None):
        """Add a validator to the pipeline"""
        self.validators.append({
            "validator": validator,
            "name": name or validator.__name__
        })
    
    def validate(self, data: Dict[str, Any]) -> ValidationResult:
        """Run data through validation pipeline"""
        overall_result = ValidationResult(True)
        
        for validator_info in self.validators:
            validator = validator_info["validator"]
            name = validator_info["name"]
            
            try:
                result = validator(data)
                if isinstance(result, ValidationResult):
                    if not result.is_valid:
                        overall_result.is_valid = False
                    overall_result.errors.extend([f"{name}: {error}" for error in result.errors])
                    overall_result.warnings.extend([f"{name}: {warning}" for warning in result.warnings])
                elif result is False:
                    overall_result.add_error(f"{name}: Validation failed")
            except Exception as e:
                overall_result.add_error(f"{name}: Validation error - {str(e)}")
        
        return overall_result
```

### Data Integrity Checks
```python
class DataIntegrityChecker:
    """Check data integrity and consistency"""
    
    def check_referential_integrity(self, data: Dict[str, Any], references: Dict[str, str]) -> ValidationResult:
        """Check that referenced IDs exist"""
        result = ValidationResult(True)
        
        for field, reference_type in references.items():
            if field in data and data[field] is not None:
                reference_id = data[field]
                if not self._reference_exists(reference_id, reference_type):
                    result.add_error(f"Reference {field} points to non-existent {reference_type}: {reference_id}")
        
        return result
    
    def check_data_consistency(self, data: Dict[str, Any], consistency_rules: List[callable]) -> ValidationResult:
        """Check data consistency rules"""
        result = ValidationResult(True)
        
        for rule in consistency_rules:
            try:
                if not rule(data):
                    result.add_error(f"Consistency rule failed: {rule.__name__}")
            except Exception as e:
                result.add_error(f"Consistency check error in {rule.__name__}: {str(e)}")
        
        return result
    
    def _reference_exists(self, reference_id: str, reference_type: str) -> bool:
        """Check if a reference exists (implement based on your storage)"""
        # Implementation depends on your data storage system
        pass
```

## Performance Optimization

### Data Caching Patterns
```python
from functools import lru_cache
from typing import Hashable

class DataCache:
    """Simple data caching with TTL support"""
    
    def __init__(self, max_size: int = 128, ttl_seconds: int = 300):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache = {}
        self.timestamps = {}
    
    def get(self, key: Hashable) -> Optional[Any]:
        """Get cached data if still valid"""
        if key not in self.cache:
            return None
        
        # Check TTL
        if self._is_expired(key):
            self._evict(key)
            return None
        
        return self.cache[key]
    
    def set(self, key: Hashable, value: Any):
        """Cache data with timestamp"""
        # Evict old entries if at capacity
        if len(self.cache) >= self.max_size:
            self._evict_oldest()
        
        self.cache[key] = value
        self.timestamps[key] = datetime.now(timezone.utc)
    
    def _is_expired(self, key: Hashable) -> bool:
        """Check if cache entry is expired"""
        timestamp = self.timestamps.get(key)
        if not timestamp:
            return True
        
        age = (datetime.now(timezone.utc) - timestamp).total_seconds()
        return age > self.ttl_seconds
    
    def _evict(self, key: Hashable):
        """Remove entry from cache"""
        self.cache.pop(key, None)
        self.timestamps.pop(key, None)
    
    def _evict_oldest(self):
        """Evict oldest cache entry"""
        if not self.timestamps:
            return
        
        oldest_key = min(self.timestamps.keys(), key=lambda k: self.timestamps[k])
        self._evict(oldest_key)
```

## Success Criteria

### Data Integrity Success
- All data operations preserve original information
- Change history is maintained for all modifications
- Data validation prevents corruption at entry points
- Recovery mechanisms work reliably

### Performance Success
- Data operations complete within acceptable timeframes
- Caching reduces redundant data access
- File operations are atomic and safe
- Memory usage remains reasonable for typical workloads

### Maintainability Success
- Data models are clear and well-documented
- Migration paths exist for schema changes
- Validation rules are comprehensive and maintainable
- Error handling provides useful feedback

Remember: **Data is the most valuable asset in any system**. Prioritize data preservation and integrity over performance optimizations. Always maintain the ability to recover from errors and rollback problematic changes.