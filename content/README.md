# Writing lessons

Everything the app teaches lives in this folder as YAML. The app reads it on
every page load, so a new or edited file shows up on refresh. No restart, no
database step.

After any change, run:

```bash
npm run content:check                      # all courses
npm run content:check -- <course-slug>     # one course
```

It validates every file, then runs every coding solution against its own tests
and checks that the untouched sample code does **not** pass. Fix every `✗`.
A `!` is a warning.

## Layout

```
content/
  tracks/<track>.yaml                         a path of courses, in order
  courses/<course>/course.yaml                course info + chapter outline
  courses/<course>/<chapter-id>/<lesson>.yaml one lesson = 3-6 exercises
  datasets/                                   CSV and other data files
```

A course has 4 chapters (at most 8). A chapter has 2-4 lessons. A lesson
starts with a `video` (slides), then 2-5 exercises that practise exactly what
the slides taught. To add a lesson: write the lesson file, then add its id to
the chapter's `lessons:` list in `course.yaml` (order matters).

Ids are lowercase-kebab-case. **Never rename an id that has been used**: progress
is stored against `course/chapter/lesson/exercise`.

## Exercise types

Every exercise has `id`, `type`, `title`, and an optional `xp` (defaults:
video 50, coding 100, mc 50, order/parsons/classify 50, sequential 100).
Text fields are Markdown, with `$inline$` and `$$block$$` math.

### video: lesson slides

```yaml
- id: intro
  type: video
  title: Why vectorise?
  slides: |
    # First slide
    Text, `code`, tables, $math$.

    ---

    ## Second slide
    Slides are separated by a line containing only ---
```

Aim for 3-6 slides, each one idea. Show code the learner will use next.

### coding: write code, run it, submit it

```yaml
- id: mean-height
  type: coding
  title: Average height
  context: |                       # 1-3 sentences of setup (<= ~780 chars)
    `heights` holds the heights of 1,000 players in cm.
  instructions:                    # 1-4 short, checkable steps
    - Import `numpy` as `np`.
    - Compute the mean of `heights` and store it in `avg`.
    - Print `avg`.
  hint: Use `np.mean()`.
  pre_code: |                      # hidden setup, runs before learner code AND solution
    import numpy as np
    heights = np.random.normal(180, 7, 1000)
  sample_code: |                   # what the editor starts with; ____ marks blanks
    import numpy as ____
    avg = ____
    print(____)
  solution: |
    import numpy as np
    avg = np.mean(heights)
    print(avg)
  tests: |                         # Python; first failing check's message is the feedback
    check_equal("avg")
    check_called("mean", msg="Use `np.mean()` to compute the average.")
    assert output.strip() == sol_output.strip(), "Print `avg`."
  success_msg: Great, that is the average height.
  timeout: 30                      # optional, seconds
```

Test helpers (all take an optional `msg=` to override the feedback):

| helper | passes when |
| --- | --- |
| `check_object("x")` | the learner defined `x` |
| `check_equal("x")` | learner's `x` equals the solution's `x` (numpy/pandas aware, float tolerance) |
| `check_equal("x", 42, tol=1e-6)` | learner's `x` equals 42 |
| `check_output_contains("text")` | the learner printed `text` |
| `check_called("np.mean")` | the code calls it (`"mean"` matches `np.mean`, `x.mean`, ...) |
| `check_code_contains("snippet")` | the source contains the snippet |
| `assert cond, "message"` | anything else; you also get `user`, `sol` (namespaces), `output`, `sol_output`, `code` |

Random numbers are seeded (`random` and `numpy` seed 42) the same way for the
learner and the solution, so `check_equal` works on random data.
Plots: anything drawn with matplotlib shows in a Plots tab automatically.
Data files: put them in `content/datasets/`; code runs with that folder as the
working directory, so `pd.read_csv("file.csv")` works. `DATA_DIR` holds the path.

### mc: multiple choice

```yaml
- id: which-type
  type: mc
  title: What type is it?
  question: After `x = 10 / 2`, what is `type(x)`?
  context: Optional extra text.
  pre_code: |          # optional: adds a console with this code already run
    x = 10 / 2
  options:             # 2-6; exactly one has correct: true; every option gets feedback
    - text: "`int`"
      feedback: Why this is wrong, and what to check.
    - text: "`float`"
      correct: true
      feedback: Why this is right.
  hint: Run `type(x)` in the console.
```

### order: put items in sequence

```yaml
- id: ml-workflow
  type: order
  title: The modelling workflow
  prompt: Order the steps of a supervised learning workflow.
  hint: You cannot evaluate a model you have not trained.
  items: [Split the data, Fit the model, Predict on the test set, Score the predictions]  # correct order
```

### parsons: arrange (and indent) lines of code

```yaml
- id: loop-sum
  type: parsons
  title: Sum the even numbers
  prompt: Arrange the lines so `total` ends up as the sum of the even numbers.
  hint: The `if` goes inside the loop.
  lines:               # correct order; indentation (multiples of 4 spaces) is part of the answer
    - "total = 0"
    - "for n in numbers:"
    - "    if n % 2 == 0:"
    - "        total += n"
```

### classify: sort items into groups

```yaml
- id: sup-vs-unsup
  type: classify
  title: Supervised or not?
  prompt: Sort each task.
  hint: Is there a label to predict?
  zones: [Supervised, Unsupervised]     # 2-4 groups
  items:                                # unique texts
    - { text: Predict house prices, zone: Supervised }
    - { text: Group customers by behaviour, zone: Unsupervised }
```

### sequential: several steps on one context

Each step runs after the **solutions** of the steps before it, so step 2 can
use variables from step 1.

```yaml
- id: clean-and-model
  type: sequential
  title: Clean, then model
  context: The `df` DataFrame has house sales.
  pre_code: |
    import pandas as pd
    df = pd.read_csv("houses.csv")
  steps:               # 2-6 steps, each like a mini coding exercise
    - instructions: [Drop rows with missing prices into `clean`.]
      hint: "`df.dropna(subset=[...])`"
      sample_code: "clean = ____"
      solution: "clean = df.dropna(subset=['price'])"
      tests: check_equal("clean")
    - instructions: [Store the mean price of `clean` in `avg`.]
      hint: "`clean['price'].mean()`"
      sample_code: "avg = ____"
      solution: "avg = clean['price'].mean()"
      tests: check_equal("avg")
```

## Libraries

The runner uses `.venv` (see `runner/requirements.txt`: numpy, pandas,
matplotlib, scikit-learn, scipy). The AI Engineering track needs
`runner/requirements-ai.txt` (torch, transformers, anthropic). List what a
course needs in `course.yaml` under `requires:` and `content:check` warns
when it is not installed. Exercises must not need network access or API
keys; for LLM API lessons, give the learner a fake client in `pre_code` that
returns canned responses, and teach the real call in the slides.

## Quality bar

- Original wording and examples. Do not copy text, code or datasets from DataCamp or any other course.
- One concept per exercise. Instructions are concrete enough that the tests feel fair.
- Feedback says what is wrong **and** where to look.
- `sample_code` must fail the tests; the solution must pass. `content:check` enforces both.
- Data: generate it in `pre_code` with a seed, or add a small file (< 1 MB) to `datasets/`.
