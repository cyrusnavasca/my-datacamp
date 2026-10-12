import { describe, expect, it } from "vitest";
import { runPython } from "@/lib/runner";

describe("python runner", () => {
  it("echoes the last expression on run, not on submit", async () => {
    expect((await runPython({ mode: "run", code: "x = 2\nx * 21" })).stdout).toBe("42\n");
  });

  it("returns tracebacks limited to the learner's code", async () => {
    const r = await runPython({ mode: "run", code: "def f():\n    return 1/0\nf()" });
    expect(r.error).toContain("ZeroDivisionError");
    expect(r.error).toContain("return 1/0");
    expect(r.error).not.toContain("harness.py");
  });

  it("captures matplotlib figures", async () => {
    const r = await runPython({ mode: "run", code: "import matplotlib.pyplot as plt\nplt.plot([1, 2, 3])" });
    expect(r.images).toHaveLength(1);
  });

  it("compares pandas objects and gives feedback", async () => {
    const r = await runPython({
      mode: "submit",
      pre_code: "import pandas as pd",
      code: "s = pd.Series([1, 2, 4])",
      solution: "s = pd.Series([1, 2, 3])",
      tests: 'check_equal("s")',
    });
    expect(r.correct).toBe(false);
    expect(r.feedback).toContain("`s` is not quite right");
  });

  it("supports every test helper", async () => {
    const r = await runPython({
      mode: "submit",
      code: "import math\nv = math.sqrt(16)\nprint('v is', v)",
      solution: "import math\nv = math.sqrt(16)\nprint('v is', v)",
      tests: 'check_object("v")\ncheck_equal("v", 4.0)\ncheck_output_contains("v is")\ncheck_called("math.sqrt")\ncheck_called("sqrt")\ncheck_code_contains("import math")\nassert user["v"] == sol["v"]',
    });
    expect(r).toMatchObject({ correct: true });
  });

  it("uses the same random state for learner and solution, including setup code", async () => {
    const r = await runPython({
      mode: "submit",
      pre_code: "import numpy as np\ndata = np.random.rand(5)",
      code: "m = data.mean() + np.random.rand()",
      solution: "m = data.mean() + np.random.rand()",
      tests: 'check_equal("m")',
    });
    expect(r.correct).toBe(true);
  });

  it("reports a broken reference solution as a lesson bug", async () => {
    const r = await runPython({ mode: "submit", code: "x = 1", solution: "x = undefined_name", tests: 'check_equal("x")' });
    expect(r.feedback).toContain("lesson bug");
  });

  it("kills runaway code", async () => {
    const r = await runPython({ mode: "run", code: "while True: pass", timeoutSec: 2 });
    expect(r.timedOut).toBe(true);
  });
});
