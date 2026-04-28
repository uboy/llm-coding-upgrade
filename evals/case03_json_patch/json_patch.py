import copy
import re


class JsonPatchError(Exception):
    """Raised when a JSON patch operation fails."""
    pass


def _unescape_pointer(pointer):
    """Unescape JSON Pointer string according to RFC 6901."""
    return pointer.replace('~1', '/').replace('~0', '~')


def _get_by_path(document, path):
    """Get a value from document using JSON Pointer path."""
    if path == '':
        return document
    
    if not path.startswith('/'):
        raise JsonPatchError(f"Invalid path: {path}")
    
    parts = path[1:].split('/')
    current = document
    
    for part in parts:
        part = _unescape_pointer(part)
        
        if isinstance(current, dict):
            if part not in current:
                raise JsonPatchError(f"Path not found: {path}")
            current = current[part]
        elif isinstance(current, list):
            try:
                index = int(part)
                if index < 0 or index >= len(current):
                    raise JsonPatchError(f"Path not found: {path}")
                current = current[index]
            except ValueError:
                raise JsonPatchError(f"Invalid list index: {part}")
        else:
            raise JsonPatchError(f"Cannot navigate into primitive: {path}")
    
    return current


def _set_by_path(document, path, value):
    """Set a value in document using JSON Pointer path."""
    if path == '':
        return value
    
    if not path.startswith('/'):
        raise JsonPatchError(f"Invalid path: {path}")
    
    parts = path[1:].split('/')
    current = document
    
    for i, part in enumerate(parts[:-1]):
        part = _unescape_pointer(part)
        
        if isinstance(current, dict):
            if part not in current:
                raise JsonPatchError(f"Path not found: {path}")
            current = current[part]
        elif isinstance(current, list):
            try:
                index = int(part)
                if index < 0 or index >= len(current):
                    raise JsonPatchError(f"Path not found: {path}")
                current = current[index]
            except ValueError:
                raise JsonPatchError(f"Invalid list index: {part}")
        else:
            raise JsonPatchError(f"Cannot navigate into primitive: {path}")
    
    last_part = _unescape_pointer(parts[-1])
    
    if isinstance(current, dict):
        current[last_part] = value
    elif isinstance(current, list):
        if last_part == '-':
            current.append(value)
        else:
            try:
                index = int(last_part)
                current.insert(index, value)
            except ValueError:
                raise JsonPatchError(f"Invalid list index: {last_part}")
    else:
        raise JsonPatchError(f"Cannot set on primitive: {path}")


def _deep_equal(a, b):
    """Check deep equality between two values."""
    if type(a) != type(b):
        return False
    
    if isinstance(a, dict):
        if len(a) != len(b):
            return False
        for key in a:
            if key not in b or not _deep_equal(a[key], b[key]):
                return False
        return True
    
    if isinstance(a, list):
        if len(a) != len(b):
            return False
        for i in range(len(a)):
            if not _deep_equal(a[i], b[i]):
                return False
        return True
    
    return a == b


def apply_patch(document, operations):
    """Apply JSON Patch operations to a document.
    
    Args:
        document: The document to patch (will not be modified)
        operations: List of patch operations
        
    Returns:
        A new patched document
        
    Raises:
        JsonPatchError: If an operation fails
    """
    result = copy.deepcopy(document)
    
    for op in operations:
        op_type = op.get('op')
        path = op.get('path')
        
        if op_type is None or path is None:
            raise JsonPatchError("Invalid operation: missing 'op' or 'path'")
        
        if op_type == 'add':
            value = op.get('value')
            if value is None:
                raise JsonPatchError("Invalid add operation: missing 'value'")
            _set_by_path(result, path, value)
            
        elif op_type == 'remove':
            if not path.startswith('/'):
                raise JsonPatchError(f"Invalid path: {path}")
            
            parts = path[1:].split('/')
            if len(parts) == 0:
                raise JsonPatchError("Cannot remove root")
            
            current = result
            for i, part in enumerate(parts[:-1]):
                part = _unescape_pointer(part)
                if isinstance(current, dict):
                    if part not in current:
                        raise JsonPatchError(f"Path not found: {path}")
                    current = current[part]
                elif isinstance(current, list):
                    try:
                        index = int(part)
                        if index < 0 or index >= len(current):
                            raise JsonPatchError(f"Path not found: {path}")
                        current = current[index]
                    except ValueError:
                        raise JsonPatchError(f"Invalid list index: {part}")
                else:
                    raise JsonPatchError(f"Cannot navigate into primitive: {path}")
            
            last_part = _unescape_pointer(parts[-1])
            if isinstance(current, dict):
                if last_part not in current:
                    raise JsonPatchError(f"Path not found: {path}")
                del current[last_part]
            elif isinstance(current, list):
                if last_part == '-':
                    if len(current) == 0:
                        raise JsonPatchError("Cannot remove from empty list")
                    current.pop()
                else:
                    try:
                        index = int(last_part)
                        if index < 0 or index >= len(current):
                            raise JsonPatchError(f"Path not found: {path}")
                        current.pop(index)
                    except ValueError:
                        raise JsonPatchError(f"Invalid list index: {last_part}")
            else:
                raise JsonPatchError(f"Cannot remove from primitive: {path}")
                
        elif op_type == 'replace':
            value = op.get('value')
            if value is None:
                raise JsonPatchError("Invalid replace operation: missing 'value'")
            _set_by_path(result, path, value)
            
        elif op_type == 'test':
            expected = op.get('value')
            if expected is None:
                raise JsonPatchError("Invalid test operation: missing 'value'")
            actual = _get_by_path(result, path)
            if not _deep_equal(actual, expected):
                raise JsonPatchError(f"Test failed: expected {expected}, got {actual}")
                
        else:
            raise JsonPatchError(f"Unknown operation: {op_type}")
    
    return result
