import copy

class JsonPatchError(Exception):
    pass

def parse_json_pointer(pointer):
    if pointer == '':
        return []
    if not pointer.startswith('/'):
        raise JsonPatchError("Invalid JSON Pointer")
    parts = pointer.split('/')[1:]
    result = []
    for part in parts:
        part = part.replace('~1', '/').replace('~0', '~')
        result.append(part)
    return result

def resolve_path(document, parts):
    current = document
    for part in parts:
        if isinstance(current, list):
            try:
                index = int(part)
            except ValueError:
                raise JsonPatchError(f"Invalid index: {part}")
            if index < 0 or index >= len(current):
                raise JsonPatchError(f"Index out of range: {index}")
            current = current[index]
        elif isinstance(current, dict):
            if part not in current:
                raise JsonPatchError(f"Key not found: {part}")
            current = current[part]
        else:
            raise JsonPatchError("Invalid path")
    return current

def apply_patch(document, operations):
    document = copy.deepcopy(document)
    for op in operations:
        if not isinstance(op, dict):
            raise JsonPatchError("Invalid operation")
        if 'op' not in op or 'path' not in op:
            raise JsonPatchError("Operation must have 'op' and 'path'")
        
        op_type = op['op']
        path = op['path']
        value = op.get('value')
        
        parts = parse_json_pointer(path)
        
        if op_type == 'add':
            if not parts:
                raise JsonPatchError("Cannot add at root")
            try:
                current = resolve_path(document, parts[:-1])
                last = parts[-1]
                if isinstance(current, list):
                    if last == '-':
                        current.append(value)
                    else:
                        try:
                            index = int(last)
                        except ValueError:
                            raise JsonPatchError(f"Invalid index: {last}")
                        if index < 0 or index > len(current):
                            raise JsonPatchError(f"Index out of range: {index}")
                        current.insert(index, value)
                elif isinstance(current, dict):
                    current[last] = value
                else:
                    raise JsonPatchError("Invalid path")
            except JsonPatchError:
                raise
        elif op_type == 'remove':
            try:
                current = resolve_path(document, parts[:-1])
                last = parts[-1]
                if isinstance(current, list):
                    try:
                        index = int(last)
                    except ValueError:
                        raise JsonPatchError(f"Invalid index: {last}")
                    if index < 0 or index >= len(current):
                        raise JsonPatchError(f"Index out of range: {index}")
                    del current[index]
                elif isinstance(current, dict):
                    if last not in current:
                        raise JsonPatchError(f"Key not found: {last}")
                    del current[last]
                else:
                    raise JsonPatchError("Invalid path")
            except JsonPatchError:
                raise
        elif op_type == 'replace':
            try:
                current = resolve_path(document, parts[:-1])
                last = parts[-1]
                if isinstance(current, list):
                    try:
                        index = int(last)
                    except ValueError:
                        raise JsonPatchError(f"Invalid index: {last}")
                    if index < 0 or index >= len(current):
                        raise JsonPatchError(f"Index out of range: {index}")
                    current[index] = value
                elif isinstance(current, dict):
                    if last not in current:
                        raise JsonPatchError(f"Key not found: {last}")
                    current[last] = value
                else:
                    raise JsonPatchError("Invalid path")
            except JsonPatchError:
                raise
        elif op_type == 'test':
            try:
                current = resolve_path(document, parts)
                if current != value:
                    raise JsonPatchError("Test failed")
            except JsonPatchError:
                raise
        else:
            raise JsonPatchError(f"Unknown operation: {op_type}")
            
    return document