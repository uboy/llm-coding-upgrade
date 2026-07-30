import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from max_happiness import max_happiness


class MaxHappinessTests(unittest.TestCase):

    def test_example_case(self):
        self.assertEqual(max_happiness([1, -2, 3, 4, -5, 6], 3, 2), 10)

    def test_all_positive_basic(self):
        self.assertEqual(max_happiness([5, 5, 5, 5], 2, 1), 10)

    def test_k_zero_returns_zero(self):
        self.assertEqual(max_happiness([1, 2, 3], 0, 2), 0)

    def test_all_negative_returns_zero(self):
        self.assertEqual(max_happiness([-1, -2, -3], 2, 2), 0)

    def test_single_element_positive(self):
        self.assertEqual(max_happiness([42], 1, 2), 42)

    def test_single_element_negative(self):
        self.assertEqual(max_happiness([-5], 1, 2), 0)

    def test_gap_zero_limits_selections(self):
        self.assertEqual(max_happiness([10, 20, 30], 2, 0), 30)

    def test_large_gap_allows_more_selections(self):
        arr = [1, 2, 3, 4, 5]
        k = 3
        gap = 5
        expected = 1 + 3 + 5
        self.assertEqual(max_happiness(arr, k, gap), expected)

    def test_skip_negative_values_when_possible(self):
        arr = [10, -100, 20, -100, 30]
        k = 3
        gap = 5
        self.assertEqual(max_happiness(arr, k, gap), 60)

    def test_all_zeros(self):
        self.assertEqual(max_happiness([0, 0, 0], 3, 2), 0)

    def test_k_larger_than_possible(self):
        arr = [1, 2, 3, 4]
        k = 10
        gap = 1
        expected = 4 + 2
        self.assertEqual(max_happiness(arr, k, gap), expected)

    def test_strictly_decreasing(self):
        arr = [100, 90, 80, 70, 60]
        k = 3
        gap = 1
        self.assertEqual(max_happiness(arr, k, gap), 180)

    def test_large_array_performance(self):
        arr = list(range(1, 501))
        result = max_happiness(arr, 50, 3)
        self.assertGreater(result, 0)

    def test_gap_makes_difference(self):
        arr = [10, 0, 0, 0, 0, 0, 10]
        self.assertEqual(max_happiness(arr, 2, 1), 10)
        self.assertEqual(max_happiness(arr, 2, 4), 20)

    def test_must_skip_negative_even_with_gap(self):
        arr = [5, -1, -1, 5, -1, 5]
        k = 3
        gap = 2
        result = max_happiness(arr, k, gap)
        self.assertGreater(result, 0)


if __name__ == "__main__":
    unittest.main()
