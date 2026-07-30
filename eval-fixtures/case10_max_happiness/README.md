# Case 10: Maximum Happiness — Constrained DP (LiveCodeBench Style)

Implement `max_happiness.py` so that the test suite passes.

## Problem

You are given an array `happiness` of `n` integers and a limit `k` (0 ≤ k ≤ n).

You need to select a **subset of indices** (possibly empty) such that:

1. **At most `k` indices** are selected.
2. **No two selected indices are adjacent** (if `i` is selected, `i-1` and `i+1` cannot be selected).
3. **Skips are limited**: between two selected indices, there can be at most `gap` unselected indices. For example, if `gap = 2`, and you select index `i`, the next selected index must be at index `i+2` or `i+3` (one or two positions gap), but not `i+4` or later.

The goal: **maximize the sum** of `happiness[i]` for selected indices. If no valid selection exists (e.g., `k=0` or impossible configuration), return `0`.

### Formal Definition

Given array `A[0..n-1]`, choose indices `i_0 < i_1 < ... < i_{m-1}` where `m <= k` such that:
- For all `j`: `i_{j+1} - i_j - 1 <= gap` (at most `gap` elements between selections)
- For all `j`: `i_{j+1} - i_j >= 2` (no adjacent selections)
- Maximize `sum(A[i_j])`

### Examples

```
happiness = [1, -2, 3, 4, -5, 6], k = 3, gap = 2
Best: select indices 0 (1), 2 (3), 5 (6)
  - 2 is not adjacent to 0 ✓
  - 5 - 2 - 1 = 2 <= gap ✓
  - 5 - 2 >= 2 ✓
Sum = 1 + 3 + 6 = 10
```

```
happiness = [5, 5, 5, 5], k = 2, gap = 1
Option A: indices 0+2 = 10, indices 1+3 = 10
Option B: indices 0+3 → 3-0-1=2 > gap=1 ✗
Best = 10
```

```
happiness = [-1, -2, -3], k = 2, gap = 2
Best: 0 (select nothing)
```

## Requirements

Export a function:
```python
def max_happiness(happiness: list[int], k: int, gap: int) -> int:
    """Return maximum sum achievable under the constraints, or 0 if none."""
```

## Complexity

The function should handle `n` up to **500** and `k` up to **50** within reasonable time (< 5 seconds on modern hardware). An O(n * k * gap) DP solution is expected.

## Edge Cases

- `k = 0`: return 0
- `gap = 0`: only allow adjacent selections? Wait, constraint says no adjacent selections AND gap >= 0. If gap = 0, the next selection must be at distance exactly 2 (one gap = 0 unselected elements between? No, gap means unselected elements BETWEEN, so with gap=0, between selections there are 0 unselected elements, which means adjacent — but adjacent is forbidden. So gap=0 with no-adjacent means no valid pair of selections exists; you can select at most 1 element).
- All negative values: return 0 (select nothing)
- Single element array with k >= 1, gap >= 0: return max(0, happiness[0])
- `k` larger than possible: return max valid sum given adjacency constraint

## Constraints

- Use only the Python standard library.
- Do not modify tests.
- Keep the implementation in a single file: `max_happiness.py`.
