import copy


class JsonPatchError(Exception):
    pass


def _unescape_token(token):
    return token.replace("~1", "/").replace("~0", "~")


def _parse_path(path):
    if not path.startswith("/"):
        raise JsonPatchError(f"Invalid path: {path}")
    if path == "/":
        return [""]
    tokens = path[1:].split("/")
    return [_unescape_token(t) for t in tokens]


def _resolve_parent(doc, tokens):
    current = doc
    for token in tokens[:-1]:
        if isinstance(current, list):
            if not token.isdigit():
                raise JsonPatchError(f"Invalid list index: {token}")
            idx = int(token)
            if idx < 0 or idx >= len(current):
                raise JsonPatchError(f"Index out of range: {idx}")
            current = current[idx]
        elif isinstance(current, dict):
            if token not in current:
                raise JsonPatchError(f"Key not found: {token}")
            current = current[token]
        else:
            raise JsonPatchError("Cannot traverse non-container")
    return current, tokens[-1]


def apply_patch(document, operations):
    doc = copy.deepcopy(document)

    for op_dict in operations:
        op = op_dict.get("op")
        path = op_dict.get("path")

        if op not in ("add", "remove", "replace", "test"):
            raise JsonPatchError(f"Unknown operation: {op}")

        tokens = _parse_path(path)

        if op == "test":
            parent, key = _resolve_parent(doc, tokens)
            if isinstance(parent, list):
                if not key.isdigit():
                    raise JsonPatchError(f"Invalid list index: {key}")
                idx = int(key)
                if idx < 0 or idx >= len(parent):
                    raise JsonPatchError(f"Index out of range: {idx}")
                actual = parent[idx]
            elif isinstance(parent, dict):
                if key not in parent:
                    raise JsonPatchError(f"Key not found: {key}")
                actual = parent[key]
            else:
                raise JsonPatchError("Cannot test non-container")
            if actual != op_dict.get("value"):
                raise JsonPatchError("Test failed")

        elif op == "remove":
            parent, key = _resolve_parent(doc, tokens)
            if isinstance(parent, list):
                if not key.isdigit():
                    raise JsonPatchError(f"Invalid list index: {key}")
                idx = int(key)
                if idx < 0 or idx >= len(parent):
                    raise JsonPatchError(f"Index out of range: {idx}")
                del parent[idx]
            elif isinstance(parent, dict):
                if key not in parent:
                    raise JsonPatchError(f"Key not found: {key}")
                del parent[key]
            else:
                raise JsonPatchError("Cannot remove from non-container")

        elif op == "replace":
            parent, key = _resolve_parent(doc, tokens)
            if isinstance(parent, list):
                if not key.isdigit():
                    raise JsonPatchError(f"Invalid list index: {key}")
                idx = int(key)
                if idx < 0 or idx >= len(parent):
                    raise JsonPatchError(f"Index out of range: {idx}")
                parent[idx] = copy.deepcopy(op_dict["value"])
            elif isinstance(parent, dict):
                if key not in parent:
                    raise JsonPatchError(f"Key not found: {key}")
                parent[key] = copy.deepcopy(op_dict["value"])
            else:
                raise JsonPatchError("Cannot replace in non-container")

        elif op == "add":
            parent, key = _resolve_parent(doc, tokens)
            if isinstance(parent, list):
                if key == "-":
                    parent.append(copy.deepcopy(op_dict["value"]))
                else:
                    if not key.isdigit():
                        raise JsonPatchError(f"Invalid list index: {key}")
                    idx = int(key)
                    if idx < 0 or idx > len(parent):
                        raise JsonPatchError(f"Index out of range: {idx}")
                    parent.insert(idx, copy.deepcopy(op_dict["value"]))
            elif isinstance(parent, dict):
                parent[key] = copy.deepcopy(op_dict["value"])
            else:
                raise JsonPatchError("Cannot add to non-container")

    return doc
