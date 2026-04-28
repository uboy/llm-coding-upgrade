import re

class TemplateResolutionError(Exception):
    pass

def resolve_templates(mapping: dict[str, str]) -> dict[str, str]:
    result = {}
    for key in mapping:
        visited = set()
        result[key] = _resolve_value(mapping[key], mapping, visited)
    return result

def _resolve_value(value: str, mapping: dict[str, str], visited: set) -> str:
    pattern = r'\$\{([^}]+)\}|\$\$'
    def replacer(match):
        if match.group(2) is not None:
            return '$'
        content = match.group(1)
        if ':-' in content:
            var_name, default = content.split(':-', 1)
        else:
            var_name, default = content, None

        if var_name in visited:
            raise TemplateResolutionError("Cyclic reference detected")
        if var_name not in mapping:
            if default is None:
                raise TemplateResolutionError(f"Missing variable: {var_name}")
            return default

        visited.add(var_name)
        try:
            resolved = _resolve_value(mapping[var_name], mapping, visited)
        finally:
            visited.discard(var_name)

        if default is not None and resolved == "":
            return default
        return resolved

    return re.sub(pattern, replacer, value)