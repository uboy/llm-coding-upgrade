# Case 02: Template Resolver

Implement `env_template.py` so that the test suite passes.

Requirements:

- Export a function `resolve_templates(mapping: dict[str, str]) -> dict[str, str]`.
- Export an exception class `TemplateResolutionError`.
- Template syntax:
  - `${NAME}`: substitute the referenced key from the same mapping;
  - `${NAME:-default}`: use `default` when `NAME` is missing or resolves to an empty string;
  - `$$`: escape to a single `$`.
- Resolution rules:
  - values may reference other values recursively;
  - references are resolved only from the provided mapping, not from process environment variables;
  - cyclic references must raise `TemplateResolutionError`;
  - unresolved required references must raise `TemplateResolutionError`;
  - the returned dict must preserve the original keys and not mutate the input mapping.

Constraints:

- Use only the Python standard library.
- Do not modify tests.
- Keep the implementation in a single file: `env_template.py`.
