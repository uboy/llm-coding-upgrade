# Case 03: JSON Patch Subset

Implement `json_patch.py` so that the test suite passes.

Requirements:

- Export a function `apply_patch(document, operations)`.
- Export an exception class `JsonPatchError`.
- Supported operations:
  - `add`
  - `remove`
  - `replace`
  - `test`
- Paths use JSON Pointer escaping rules:
  - `~1` means `/`
  - `~0` means `~`
- Behavior:
  - return a deep-copied patched document;
  - never mutate the input document;
  - `add` supports list insertion by index and `-` for append;
  - invalid operations or invalid paths raise `JsonPatchError`;
  - `test` compares deep equality and raises `JsonPatchError` on mismatch.

Constraints:

- Use only the Python standard library.
- Do not modify tests.
- Keep the implementation in a single file: `json_patch.py`.
