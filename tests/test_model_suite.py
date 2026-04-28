import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts import model_suite


class SmokeStackTests(unittest.TestCase):
    def test_smoke_stack_retries_transient_error_then_succeeds(self) -> None:
        transient = subprocess.CalledProcessError(
            22,
            ["bash", "stack.sh", "smoke"],
            output="bad gateway\n",
            stderr="curl: (22) The requested URL returned error: 502\n",
        )
        success = subprocess.CompletedProcess(
            ["bash", "stack.sh", "smoke"],
            0,
            stdout='{"object":"list"}\n{"choices":[{"message":{"content":"ok"}}]}\n',
            stderr="",
        )

        with mock.patch.object(model_suite, "stack_command", return_value=(["bash", "stack.sh", "smoke"], {"A": "B"})), \
             mock.patch.object(model_suite, "run_command", side_effect=[transient, success]) as run_mock, \
             mock.patch.object(model_suite.time, "sleep") as sleep_mock:
            model_suite.smoke_stack(Path("/tmp/fake.env"), timeout_s=30, retry_delay_s=0)

        self.assertEqual(run_mock.call_count, 2)
        sleep_mock.assert_called_once_with(0)

    def test_smoke_stack_fails_fast_on_non_transient_error(self) -> None:
        fatal = subprocess.CalledProcessError(
            1,
            ["bash", "stack.sh", "smoke"],
            output="",
            stderr="Missing config file\n",
        )

        with mock.patch.object(model_suite, "stack_command", return_value=(["bash", "stack.sh", "smoke"], {"A": "B"})), \
             mock.patch.object(model_suite, "run_command", side_effect=fatal) as run_mock, \
             mock.patch.object(model_suite.time, "sleep") as sleep_mock:
            with self.assertRaises(subprocess.CalledProcessError):
                model_suite.smoke_stack(Path("/tmp/fake.env"), timeout_s=30, retry_delay_s=0)

        self.assertEqual(run_mock.call_count, 1)
        sleep_mock.assert_not_called()


class OpenCodeCommandTests(unittest.TestCase):
    def test_build_opencode_run_command_wraps_with_script_when_available(self) -> None:
        case_dir = Path("/tmp/case")
        title = "night-run"
        prompt = "solve it"

        with mock.patch.object(model_suite.os, "name", "posix"), \
             mock.patch.object(model_suite.shutil, "which", return_value="/usr/bin/script"), \
             mock.patch.dict(model_suite.os.environ, {}, clear=False):
            command = model_suite.build_opencode_run_command(case_dir, title, prompt)

        self.assertEqual(command[0:4], ["script", "-q", "-e", "-c"])
        self.assertEqual(command[-1], "/dev/null")
        inner = command[4]
        self.assertIn("opencode run", inner)
        self.assertIn("--dangerously-skip-permissions", inner)
        self.assertIn(str(case_dir), inner)
        self.assertIn(title, inner)
        self.assertNotIn("--print-logs", inner)

    def test_build_opencode_run_command_includes_print_logs_when_enabled(self) -> None:
        case_dir = Path("/tmp/case")
        title = "night-run"
        prompt = "solve it"

        with mock.patch.object(model_suite.os, "name", "posix"), \
             mock.patch.object(model_suite.shutil, "which", return_value="/usr/bin/script"), \
             mock.patch.dict(model_suite.os.environ, {"MODEL_SUITE_PRINT_LOGS": "true"}, clear=False):
            command = model_suite.build_opencode_run_command(case_dir, title, prompt)

        self.assertIn("--print-logs", command[4])

    def test_build_opencode_run_command_falls_back_without_script(self) -> None:
        case_dir = Path("/tmp/case")
        title = "night-run"
        prompt = "solve it"

        with mock.patch.object(model_suite.os, "name", "posix"), \
             mock.patch.object(model_suite.shutil, "which", return_value=None), \
             mock.patch.dict(model_suite.os.environ, {}, clear=False):
            command = model_suite.build_opencode_run_command(case_dir, title, prompt)

        self.assertEqual(command[0:2], ["opencode", "run"])
        self.assertNotIn("--print-logs", command)
        self.assertEqual(command[-1], prompt)


class ExportSessionTests(unittest.TestCase):
    def test_export_session_retries_after_transient_json_error(self) -> None:
        broken = subprocess.CompletedProcess(["opencode", "export", "ses_x"], 0, stdout='{"info": {"id": 1},', stderr="")
        good = subprocess.CompletedProcess(["opencode", "export", "ses_x"], 0, stdout='{"info": {"id": 1}}', stderr="")

        with mock.patch.object(model_suite, "run_command", side_effect=[broken, good]) as run_mock, \
             mock.patch.object(model_suite.time, "sleep") as sleep_mock:
            result = model_suite.export_session("ses_x", attempts=2, retry_delay_s=0)

        self.assertEqual(result, {"info": {"id": 1}})
        self.assertEqual(run_mock.call_count, 2)
        sleep_mock.assert_called_once_with(0)


class VisibleAndHiddenFailureHandlingTests(unittest.TestCase):
    def test_run_visible_tests_uses_zero_exit_for_custom_command(self) -> None:
        completed = subprocess.CompletedProcess(
            ["bash", "tests/run.sh"],
            0,
            stdout="compiled and ran\n",
            stderr="",
        )

        with mock.patch.object(model_suite, "run_command", return_value=completed):
            result = model_suite.run_visible_tests(Path("/tmp/case"), command=["bash", "tests/run.sh"])

        self.assertTrue(result["passed"])
        self.assertEqual(result["command"], ["bash", "tests/run.sh"])

    def test_run_visible_tests_records_failed_output_without_raising(self) -> None:
        failure = subprocess.CalledProcessError(
            1,
            ["python3", "-m", "unittest"],
            output="FAIL: test_example\n",
            stderr="AssertionError\n",
        )

        with mock.patch.object(model_suite, "run_command", side_effect=failure):
            result = model_suite.run_visible_tests(Path("/tmp/case"))

        self.assertFalse(result["passed"])
        self.assertEqual(result["returncode"], 1)
        self.assertIn("FAIL: test_example", result["output"])
        self.assertIn("AssertionError", result["output"])

    def test_evaluate_case_converts_hidden_check_exception_into_failed_result(self) -> None:
        case = {
            "id": "case02_env_template",
            "fixture": "case02_env_template",
            "solution_file": "env_template.py",
            "timeout_seconds": 300,
            "prompt": "solve",
            "hidden_check": "env_template_default_on_resolved_empty",
        }
        run_root = Path("/tmp/run-root")
        exported_session = {
            "messages": [
                {
                    "info": {
                        "role": "assistant",
                        "time": {"created": 1000, "completed": 2000},
                        "tokens": {"input": 10, "output": 5, "cache": {"read": 0}},
                    },
                    "parts": [{"type": "text", "text": "done"}],
                }
            ]
        }

        with mock.patch.object(model_suite, "copy_fixture"), \
             mock.patch.object(model_suite, "sha256_file", return_value="abc"), \
             mock.patch.object(model_suite, "opencode_run", return_value="ses_x"), \
             mock.patch.object(model_suite, "export_session", return_value=exported_session), \
             mock.patch.object(model_suite, "run_visible_tests", return_value={"passed": True, "output": "OK", "returncode": 0}), \
             mock.patch.dict(model_suite.HIDDEN_CHECKS, {"env_template_default_on_resolved_empty": mock.Mock(side_effect=ValueError("boom"))}, clear=False), \
             mock.patch.object(Path, "rglob", return_value=[]), \
             mock.patch.object(Path, "write_text"):
            result = model_suite.evaluate_case(run_root, "model-x", case)

        self.assertTrue(result["visible_tests"]["passed"])
        self.assertFalse(result["hidden_check"]["passed"])
        self.assertIn("ValueError", result["hidden_check"]["details"][0])
        self.assertFalse(result["formal_solution"])

    def test_evaluate_case_without_hidden_check_marks_formal_solution_from_visible(self) -> None:
        case = {
            "id": "case05_cpp_lru_cache",
            "fixture": "case05_cpp_lru_cache",
            "solution_file": "lru_cache.hpp",
            "timeout_seconds": 300,
            "prompt": "solve",
            "test_command": ["bash", "tests/run.sh"],
        }
        run_root = Path("/tmp/run-root")
        exported_session = {
            "messages": [
                {
                    "info": {
                        "role": "assistant",
                        "time": {"created": 1000, "completed": 2000},
                        "tokens": {"input": 10, "output": 5, "cache": {"read": 0}},
                    },
                    "parts": [{"type": "text", "text": "done"}],
                }
            ]
        }

        with mock.patch.object(model_suite, "copy_fixture"), \
             mock.patch.object(model_suite, "sha256_file", return_value="abc"), \
             mock.patch.object(model_suite, "opencode_run", return_value="ses_x"), \
             mock.patch.object(model_suite, "export_session", return_value=exported_session), \
             mock.patch.object(model_suite, "run_visible_tests", return_value={"passed": True, "output": "", "returncode": 0, "command": ["bash", "tests/run.sh"]}), \
             mock.patch.object(Path, "rglob", return_value=[]), \
             mock.patch.object(Path, "write_text"):
            result = model_suite.evaluate_case(run_root, "model-x", case)

        self.assertTrue(result["hidden_check"]["passed"])
        self.assertTrue(result["hidden_check"]["skipped"])
        self.assertTrue(result["formal_solution"])


class StackEnvGenerationTests(unittest.TestCase):
    def test_stack_env_for_model_uses_common_root_for_alternate_storage(self) -> None:
        model = {
            "runtime": {
                "ctx_size": 131072,
                "parallel": 1,
                "tensor_split": "1,1,1",
                "split_mode": "layer",
                "gpu_layers": 100,
                "fit": "on",
            }
        }
        base_values = {
            "LLAMA_MODELS_HOST_DIR": "/data/shared/<user>/models",
            "LLAMA_MODEL_PATH": "/models/old.gguf",
            "PROXY_REAL_MODEL": "old.gguf",
            "LLAMA_CTX_SIZE": "1",
            "LLAMA_PARALLEL": "1",
            "LLAMA_TENSOR_SPLIT": "1,1,1",
            "LLAMA_SPLIT_MODE": "layer",
            "LLAMA_GPU_LAYERS": "100",
            "LLAMA_FIT": "on",
        }
        captured: dict[str, str] = {}

        def capture_env(path: Path, values: dict[str, str]) -> None:
            captured.update(values)

        with mock.patch.object(model_suite, "parse_env_file", return_value=base_values), \
             mock.patch.object(model_suite, "write_env_file", side_effect=capture_env), \
             mock.patch.object(model_suite, "base_stack_env_path", return_value=Path("/tmp/base.env")):
            model_suite.stack_env_for_model(
                model,
                Path("/data/shared/<user>/models/Qwen3-Coder-Next-GGUF/Qwen3-Coder-Next-Q4_K_M/Qwen3-Coder-Next-Q4_K_M-00001-of-00004.gguf"),
                Path("/tmp/out.env"),
            )

        self.assertEqual(captured["LLAMA_MODELS_HOST_DIR"], "/data/shared")
        self.assertEqual(
            captured["LLAMA_MODEL_PATH"],
            "/models/<user>/models/Qwen3-Coder-Next-GGUF/Qwen3-Coder-Next-Q4_K_M/Qwen3-Coder-Next-Q4_K_M-00001-of-00004.gguf",
        )


class HiddenCheckCompatibilityTests(unittest.TestCase):
    def test_hidden_check_ttl_cache_does_not_require_private_cache_attribute(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case_dir = Path(tmp)
            (case_dir / "ttl_cache.py").write_text(
                "\n".join(
                    [
                        "from collections import OrderedDict",
                        "",
                        "class TTLCache:",
                        "    def __init__(self, maxsize, ttl_seconds, now_func):",
                        "        self.maxsize = maxsize",
                        "        self.ttl_seconds = ttl_seconds",
                        "        self.now_func = now_func",
                        "        self.store = OrderedDict()",
                        "",
                        "    def _expire(self):",
                        "        now = self.now_func()",
                        "        expired = [k for k, (_, exp) in self.store.items() if exp <= now]",
                        "        for key in expired:",
                        "            del self.store[key]",
                        "",
                        "    def set(self, key, value, ttl_seconds=None):",
                        "        self._expire()",
                        "        if key in self.store:",
                        "            del self.store[key]",
                        "        elif len(self.store) >= self.maxsize:",
                        "            self.store.popitem(last=False)",
                        "        ttl = self.ttl_seconds if ttl_seconds is None else ttl_seconds",
                        "        self.store[key] = (value, self.now_func() + ttl)",
                        "",
                        "    def get(self, key):",
                        "        self._expire()",
                        "        if key not in self.store:",
                        "            return None",
                        "        value, exp = self.store.pop(key)",
                        "        self.store[key] = (value, exp)",
                        "        return value",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            result = model_suite.hidden_check_ttl_cache(case_dir)

        self.assertTrue(result["passed"])
        self.assertEqual(result["details"], {"a": 1, "b": None, "c": 3})

    def test_hidden_check_rate_limiter_validates_boundary_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            case_dir = Path(tmp)
            (case_dir / "rate_limiter.py").write_text(
                "\n".join(
                    [
                        "from collections import defaultdict, deque",
                        "import time",
                        "",
                        "class SlidingWindowRateLimiter:",
                        "    def __init__(self, max_requests, window_seconds, now_func=None):",
                        "        if max_requests <= 0 or window_seconds <= 0:",
                        "            raise ValueError('invalid configuration')",
                        "        self.max_requests = max_requests",
                        "        self.window_seconds = window_seconds",
                        "        self.now_func = now_func or time.monotonic",
                        "        self.requests = defaultdict(deque)",
                        "",
                        "    def allow(self, user_id):",
                        "        now = self.now_func()",
                        "        window_start = now - self.window_seconds",
                        "        bucket = self.requests[user_id]",
                        "        while bucket and bucket[0] <= window_start:",
                        "            bucket.popleft()",
                        "        if len(bucket) >= self.max_requests:",
                        "            return False",
                        "        bucket.append(now)",
                        "        return True",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            result = model_suite.hidden_check_rate_limiter(case_dir)

        self.assertTrue(result["passed"])
        self.assertEqual(
            result["details"],
            {"first": True, "second": True, "third": True, "fourth": False, "other_user": True},
        )


class ModelSuiteResilienceTests(unittest.TestCase):
    def test_run_model_suite_records_model_error_and_continues(self) -> None:
        models = [
            {"id": "bad-model", "label": "Bad", "path_glob": "x", "local_dir": "/tmp", "hf_repo": "r", "hf_include": "i"},
            {"id": "good-model", "label": "Good", "path_glob": "y", "local_dir": "/tmp", "hf_repo": "r", "hf_include": "i"},
        ]
        run_id = "run-test"
        good_gguf = Path("/tmp/good.gguf")
        good_env = Path("/tmp/good.env")
        case_result = {
            "id": "case01",
            "visible_tests": {"passed": True},
            "hidden_check": {"passed": True},
            "metrics": {"wall_s": 1.0, "turns": 1},
        }

        with mock.patch.object(model_suite, "resolve_gguf_on_host", side_effect=[None, good_gguf]), \
             mock.patch.object(model_suite, "stack_env_for_model", return_value=good_env), \
             mock.patch.object(model_suite, "restart_stack"), \
             mock.patch.object(model_suite, "smoke_stack"), \
             mock.patch.object(model_suite, "run_direct_benchmarks", return_value=[]), \
             mock.patch.object(model_suite, "evaluate_case", return_value=case_result), \
             mock.patch.object(model_suite, "restore_base_stack"), \
             mock.patch.object(model_suite, "compare_results", return_value=(Path("/tmp/summary.json"), Path("/tmp/summary.md"))):
            result = model_suite.run_model_suite(models, run_id=run_id, install_missing=False, restore_base=True)

        self.assertEqual(len(result["models"]), 2)
        self.assertIn("error", result["models"][0])
        self.assertEqual(result["models"][1]["id"], "good-model")
