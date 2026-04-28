import unittest

from json_patch import JsonPatchError, apply_patch


class JsonPatchTests(unittest.TestCase):
    def test_replace_nested_key(self):
        original = {"user": {"name": "Ann", "role": "dev"}}
        result = apply_patch(original, [{"op": "replace", "path": "/user/role", "value": "lead"}])
        self.assertEqual(result["user"]["role"], "lead")
        self.assertEqual(original["user"]["role"], "dev")

    def test_add_append_to_list(self):
        original = {"items": [1, 2]}
        result = apply_patch(original, [{"op": "add", "path": "/items/-", "value": 3}])
        self.assertEqual(result["items"], [1, 2, 3])

    def test_add_insert_into_list(self):
        original = {"items": [1, 3]}
        result = apply_patch(original, [{"op": "add", "path": "/items/1", "value": 2}])
        self.assertEqual(result["items"], [1, 2, 3])

    def test_remove_list_item(self):
        original = {"items": ["a", "b", "c"]}
        result = apply_patch(original, [{"op": "remove", "path": "/items/1"}])
        self.assertEqual(result["items"], ["a", "c"])

    def test_test_operation_success(self):
        original = {"enabled": True}
        result = apply_patch(
            original,
            [
                {"op": "test", "path": "/enabled", "value": True},
                {"op": "replace", "path": "/enabled", "value": False},
            ],
        )
        self.assertFalse(result["enabled"])

    def test_test_operation_failure_raises(self):
        with self.assertRaises(JsonPatchError):
            apply_patch({"enabled": True}, [{"op": "test", "path": "/enabled", "value": False}])

    def test_escaped_pointer_tokens(self):
        original = {"a/b": {"~key": 1}}
        result = apply_patch(original, [{"op": "replace", "path": "/a~1b/~0key", "value": 2}])
        self.assertEqual(result["a/b"]["~key"], 2)

    def test_invalid_path_raises(self):
        with self.assertRaises(JsonPatchError):
            apply_patch({"items": [1]}, [{"op": "remove", "path": "/items/4"}])


if __name__ == "__main__":
    unittest.main()
