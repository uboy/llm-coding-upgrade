import re


class TemplateResolutionError(Exception):
    """Raised when template resolution fails."""
    pass


def resolve_templates(mapping: dict[str, str]) -> dict[str, str]:
    result = dict(mapping)
    resolved = {}
    
    def resolve_value(key, visited):
        if key in resolved:
            return resolved[key]
        if key in visited:
            raise TemplateResolutionError(f"Cyclic reference detected for key '{key}'")
        
        value = result.get(key)
        if value is None:
            raise TemplateResolutionError(f"Unresolved reference: '{key}'")
        
        visited.add(key)
        resolved_value = _resolve_string(value, visited, key)
        visited.remove(key)
        
        resolved[key] = resolved_value
        return resolved_value
    
    def _resolve_string(value, visited, current_key):
        result_parts = []
        i = 0
        while i < len(value):
            if i < len(value) - 1 and value[i] == '$' and value[i + 1] == '$':
                result_parts.append('$')
                i += 2
            elif value[i] == '$':
                match = re.match(r'\$\{([^}]+)\}', value[i:])
                if match:
                    expr = match.group(1)
                    i += len(match.group(0))
                    
                    if ':-' in expr:
                        var_name, default = expr.split(':-', 1)
                        if var_name in result and result[var_name]:
                            sub_value = resolve_value(var_name, visited)
                            result_parts.append(sub_value)
                        else:
                            result_parts.append(default)
                    else:
                        var_name = expr
                        if var_name not in result:
                            raise TemplateResolutionError(f"Unresolved reference: '{var_name}'")
                        sub_value = resolve_value(var_name, visited)
                        result_parts.append(sub_value)
                else:
                    result_parts.append(value[i])
                    i += 1
            else:
                result_parts.append(value[i])
                i += 1
        
        return ''.join(result_parts)
    
    for key in result:
        resolve_value(key, set())
    
    return resolved
