"""Runs learner code for my-datacamp and checks it.

Reads one JSON request on stdin, writes one JSON result as the last line of
stdout, after the RESULT_MARKER. Started fresh for every run by src/lib/runner.ts.

Request:
  mode       "run" | "submit"
  pre_code   setup code, run before both learner code and solution (not shown)
  code       the learner's code
  solution   reference solution (submit only)
  tests      Python test code (submit only), see TEST HELPERS below
  data_dir   folder with datasets, exposed as DATA_DIR

Result:
  stdout, error (formatted traceback or null), images (base64 PNGs),
  and for submit: correct (bool), feedback (str)

TEST HELPERS (available inside `tests`):
  user, sol                 the learner's and the solution's namespaces (dicts)
  output, sol_output        what each printed
  code                      the learner's source code
  check_object(name)        variable must exist
  check_equal(name, expected=<solution's value>, tol=1e-6)
  check_output_contains(text)
  check_called(func_name)   the learner's code calls func_name (e.g. "mean" or "np.mean")
  check_code_contains(snippet)
  assert cond, "message"    any failing assert's message becomes the feedback
"""

import ast
import base64
import contextlib
import io
import json
import linecache
import os
import random
import sys
import traceback

RESULT_MARKER = "\x00__MYDC_RESULT__\x00"
MISSING = object()
MAX_OUTPUT = 20_000


class TestFailure(Exception):
    pass


def setup_env(data_dir):
    os.environ.setdefault("MPLBACKEND", "Agg")
    os.environ.setdefault("HF_HUB_OFFLINE", "1")  # exercises never download models
    # runner/ on the path so exercises can `import aikit` and `from kits.<course> import ...`
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.insert(0, here)
    if data_dir and os.path.isdir(data_dir):
        os.chdir(data_dir)


def seed():
    """Same random state for learner and solution, before setup and before their code."""
    random.seed(42)
    try:
        import numpy as np
    except ImportError:
        return
    np.random.seed(42)
    torch = sys.modules.get("torch")
    if torch is not None:  # only when an exercise already imported it: importing torch is slow
        torch.manual_seed(42)


def fresh_ns(data_dir):
    return {"__name__": "__main__", "DATA_DIR": data_dir}


def format_error(exc, filename):
    """Traceback limited to the learner's own code."""
    tb = traceback.extract_tb(exc.__traceback__)
    frames = [f for f in tb if f.filename == filename]
    lines = []
    if frames:
        lines.append("Traceback (most recent call last):\n")
        lines.extend(traceback.format_list(frames))
    lines.extend(traceback.format_exception_only(type(exc), exc))
    return "".join(lines).rstrip()


def run_source(src, ns, filename, echo_last=False):
    """Exec src in ns; capture stdout+stderr. Returns (output, error)."""
    buf = io.StringIO()
    err = None
    # Register the source so tracebacks can show the offending line.
    linecache.cache[filename] = (len(src), None, src.splitlines(True), filename)
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
        try:
            tree = ast.parse(src, filename=filename)
            last = None
            if echo_last and tree.body and isinstance(tree.body[-1], ast.Expr):
                last = ast.Expression(tree.body.pop().value)
            exec(compile(tree, filename, "exec"), ns)
            if last is not None:
                value = eval(compile(last, filename, "eval"), ns)
                if value is not None:
                    print(repr(value))
        except SyntaxError as e:
            err = "".join(traceback.format_exception_only(type(e), e)).rstrip()
        except BaseException as e:  # noqa: BLE001 - learner code can raise anything, incl. SystemExit
            err = format_error(e, filename)
    out = buf.getvalue()
    if len(out) > MAX_OUTPUT:
        out = out[:MAX_OUTPUT] + "\n... output truncated ..."
    return out, err


def grab_figures():
    plt = sys.modules.get("matplotlib.pyplot")
    if plt is None:
        return []
    images = []
    for num in plt.get_fignums():
        fig = plt.figure(num)
        b = io.BytesIO()
        fig.savefig(b, format="png", dpi=110, bbox_inches="tight")
        images.append(base64.b64encode(b.getvalue()).decode())
    plt.close("all")
    return images


def values_equal(a, b, tol):
    np = sys.modules.get("numpy")
    pd = sys.modules.get("pandas")
    if pd is not None and isinstance(a, (pd.DataFrame, pd.Series)):
        try:
            if isinstance(a, pd.DataFrame):
                pd.testing.assert_frame_equal(a, b, check_exact=False, atol=tol)
            else:
                pd.testing.assert_series_equal(a, b, check_exact=False, atol=tol)
            return True
        except (AssertionError, TypeError, ValueError):
            return False
    torch = sys.modules.get("torch")
    if torch is not None and (isinstance(a, torch.Tensor) or isinstance(b, torch.Tensor)):
        try:
            ta, tb = torch.as_tensor(a).detach().double(), torch.as_tensor(b).detach().double()
            return ta.shape == tb.shape and bool(torch.allclose(ta, tb, atol=tol, equal_nan=True))
        except (TypeError, RuntimeError, ValueError):
            return False
    if np is not None and isinstance(a, np.ndarray):
        try:
            return a.shape == np.shape(b) and bool(np.allclose(a, b, atol=tol, equal_nan=True))
        except TypeError:
            return bool((a == b).all())
    if isinstance(a, float) or isinstance(b, float):
        try:
            return abs(float(a) - float(b)) <= tol * max(1.0, abs(float(b)))
        except (TypeError, ValueError):
            return False
    try:
        return bool(a == b)
    except Exception:  # noqa: BLE001
        return False


def short(v, n=120):
    s = repr(v)
    return s if len(s) <= n else s[: n - 3] + "..."


def make_helpers(user, sol, output, code):
    try:
        tree = ast.parse(code)
    except SyntaxError:
        tree = ast.Module(body=[], type_ignores=[])

    def call_names():
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                parts = []
                f = node.func
                while isinstance(f, ast.Attribute):
                    parts.append(f.attr)
                    f = f.value
                if isinstance(f, ast.Name):
                    parts.append(f.id)
                parts.reverse()
                for i in range(len(parts)):
                    names.add(".".join(parts[i:]))
        return names

    def check_object(name, msg=None):
        if name not in user:
            raise TestFailure(msg or f"Did you define `{name}`? It does not exist yet.")
        return user[name]

    def check_equal(name, expected=MISSING, tol=1e-6, msg=None):
        value = check_object(name)
        if expected is MISSING:
            if name not in sol:
                raise TestFailure(f"(lesson bug) the solution does not define `{name}`.")
            expected = sol[name]
        if not values_equal(value, expected, tol):
            raise TestFailure(msg or f"`{name}` is not quite right. Expected {short(expected)}, got {short(value)}.")
        return True

    def check_output_contains(text, msg=None):
        if str(text) not in output:
            raise TestFailure(msg or f"Your output should contain `{text}`. Did you print it?")
        return True

    def check_called(func_name, msg=None):
        if func_name not in call_names():
            raise TestFailure(msg or f"Use `{func_name}()` in your code.")
        return True

    def check_code_contains(snippet, msg=None):
        if snippet not in code:
            raise TestFailure(msg or f"Your code should contain `{snippet}`.")
        return True

    return {
        "check_object": check_object,
        "check_equal": check_equal,
        "check_output_contains": check_output_contains,
        "check_called": check_called,
        "check_code_contains": check_code_contains,
    }


def main():
    req = json.loads(sys.stdin.read())
    data_dir = req.get("data_dir") or ""
    setup_env(data_dir)
    mode = req.get("mode", "run")
    pre = req.get("pre_code") or ""
    code = req.get("code") or ""
    result = {"stdout": "", "error": None, "images": []}

    if "torch" in pre + code + (req.get("solution") or ""):
        import torch  # noqa: F401  imported up front so seed() also seeds torch for pre_code
    user = fresh_ns(data_dir)
    seed()
    if pre.strip():
        _, pre_err = run_source(pre, user, "<setup>")
        if pre_err:
            result["error"] = "(lesson bug) setup code failed:\n" + pre_err
            emit(result, mode)
            return
    seed()
    out, err = run_source(code, user, "<script.py>", echo_last=(mode == "run"))
    result["stdout"], result["error"] = out, err
    result["images"] = grab_figures()

    if mode == "submit":
        if err:
            result["correct"] = False
            if "____" in code and "NameError" in err:
                result["feedback"] = "Fill in the `____` blanks before you submit."
            else:
                result["feedback"] = "Your code raised an error (see the console). Fix it and submit again."
        else:
            result.update(check(req, user, out, code, data_dir))
    emit(result, mode)


def check(req, user, out, code, data_dir):
    sol = fresh_ns(data_dir)
    pre = req.get("pre_code") or ""
    seed()
    if pre.strip():
        run_source(pre, sol, "<setup>")
    seed()
    sol_out, sol_err = run_source(req.get("solution") or "", sol, "<solution>")
    grab_figures()
    if sol_err:
        return {"correct": False, "feedback": "(lesson bug) the reference solution failed:\n" + sol_err}

    env = {"user": user, "sol": sol, "output": out, "sol_output": sol_out, "code": code}
    env.update(make_helpers(user, sol, out, code))
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            exec(compile(req.get("tests") or "", "<tests>", "exec"), env)
    except (TestFailure, AssertionError) as e:
        return {"correct": False, "feedback": str(e) or "Not quite. Check the instructions again."}
    except Exception as e:  # noqa: BLE001
        return {"correct": False, "feedback": "Check failed: " + "".join(traceback.format_exception_only(type(e), e)).strip()}
    return {"correct": True, "feedback": ""}


def emit(result, mode):
    sys.stdout.write("\n" + RESULT_MARKER + json.dumps(result) + "\n")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
