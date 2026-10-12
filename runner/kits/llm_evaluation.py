"""Helpers for the llm-evaluation course.

Import in pre_code:  from kits.llm_evaluation import ...

Everything here is deterministic: the same call gives the same result in every
process, so `check_equal` works and thresholds are stable.

The ORBIT system under test
    Retriever(k, titles)        top-k handbook search with aikit.embed
    orbit_model()               ORBIT's answering model: aikit.grounded() whose
                                eagerness depends on the system prompt (see below)
    Orbit(...)                  retrieval + prompt + model; .answer(question) -> dict
    VERSIONS                    v1 (k=1), v2 (k=3, titles, citations), v3 (v2 + an
                                "always answer" prompt), v4 (v3 + a refusal clause)
    make_orbit(version, **kw)   an Orbit for a version, with overrides (e.g. k=5)
    run_orbit(version)          DataFrame of answers to all 45 Helios questions

Labels and data
    questions_df()              the 45 Helios questions as a DataFrame
    KEY_FACTS                   what a human checks for in each answer
    human_label(qid, answer)    the crew's verdict (1 = acceptable), see below
    key_facts_pass(qid, answer) the same rule, used as an automatic scorer
    orbit_log()                 v1 + v2 answers with human labels and failure causes
    judge_set()                 80 labelled outputs for judge calibration (dev/test)
    production_sample()         300 labelled crew questions in the real traffic mix
    pairwise_pairs()            v1 vs v2 (and padded) answer pairs for pairwise judging
    big_comparison()            400 paired production results for v2 vs v3
    failures()                  33 failed traces with causes, for error analysis
    dev_set_v0()                the developer's biased first eval set (20 questions)
    check_batch()               35 outputs with planted defects, for assertion suites

Measuring
    normalize, is_refusal, words, numbers   text helpers used by metrics and labels

The LLM judge
    judge_model()               responder for a FakeClaude used as an LLM judge

----------------------------------------------------------------------------------
How orbit_model() reads the system prompt
    default                     aikit.grounded(threshold=0.34)
    "eager" phrases             ("always give an answer", "as helpful as possible",
                                "best guess", "never refuse") lower the answer
                                threshold to 0.2: more questions answered, but it
                                also answers questions the handbook can't answer.
    a refusal clause            ("if the documents do not contain the answer, say
                                you don't know", "refuse", "unanswerable") adds a
                                check: if the question names a topic word (not a
                                FRAME_WORDS word like "long" or "role") that never
                                appears in the documents, it refuses instead of
                                guessing.

How human_label() decides (the "crew's" judgement)
    Unanswerable question       1 only for a refusal.
    Answerable question         1 if every KEY_FACTS group is present (any of its
                                alternatives, case-insensitive) and no known wrong
                                fact (e.g. the superseded "5 minutes") appears.
    HUMAN_OVERRIDES             (qid, answer substring) -> label, for places where a
                                person reads an answer differently (empty for now).

How judge_model() behaves (documented so lessons can rely on it)
    It reads the judge prompt (system + user). Inputs go in tags:
        <question>, <reference> (optional), <response>   for single grading
        <response_a>, <response_b>                       for pairwise grading
    Everything else is the rubric. It looks for these features in the rubric:
        binary      the words PASS and FAIL         -> answers PASS or FAIL
        scale       "1-10", "1 to 10", "scale", "score" (without PASS/FAIL)
                                                    -> answers a score 1..10
        facts       mentions the reference/gold answer and asks whether the
                    response contains/includes/matches/agrees with it, or states
                    its key facts. Only works if a <reference> is in the prompt.
        contradict  "contradict", "conflict", "inconsistent"
        refusal     "refuse", "don't know", "unanswerable", "cannot be answered"
        length      "length", "longer", "verbose", "padding", "concise"
        examples    two or more worked examples ("<example>" or "Example 1")
    Verdict for one response:
        with refusal + a reference: an "UNANSWERABLE" reference needs a refusal;
            a refusal to an answerable question fails.
        without refusal: every refusal fails (it looks unhelpful).
        with facts + reference: passes if all reference numbers appear and >= 75%
            of the reference's content words appear; with contradict it also
            fails responses that state the right number and, in a near-identical
            sentence, a different number with the same unit (stale + new docs).
        otherwise (vague rubric): a plausibility guess from topic overlap with the
            question, plus a bonus for long answers (verbosity bias), plus noise.
            Confident hallucinations look plausible, so they pass.
    Noise: a seeded "flip" of the final verdict, by model tier: small (haiku)
        8%, medium (sonnet) 3%, large (opus) 1%; halved when the rubric has
        examples. In scale mode, scores get Gaussian noise (sd 2.0 / 1.4 / 1.0).
    Pairwise: each response is assessed as above. With criteria (facts/refusal)
        the better one wins; on a tie the judge picks the first response (position
        bias), unless one is >= 1.4x longer and the rubric says nothing about length,
        in which case the longer one wins (verbosity bias). With a vague rubric it
        compares plausibility scores, adds 0.25 to a response >= 1.4x longer (unless
        the rubric mentions length) and 0.3 to whichever response comes first.
        It does all this even when told ties are allowed.
        Answer: "Winner: A" / "Winner: B" (or a <winner> tag if the rubric shows one).
    Randomness comes from a hash of the prompt and model, never call order.

Cache: standard runs are stored in llm_evaluation_cache.json with a fingerprint of
aikit.py, this file and the Helios data. A stale cache is ignored (runs are computed
live, slower). Rebuild and verify:  .venv/bin/python runner/kits/llm_evaluation.py --rebuild
"""

from __future__ import annotations

import functools
import hashlib
import json
import random
import re
import sys
import unicodedata
from pathlib import Path

if __name__ == "__main__":  # run as a script: make runner/ importable
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import aikit
from aikit import FakeClaude, VirtualClock, helios  # noqa: F401  (re-exported for pre_code)

MODEL = "claude-sonnet-5-5"
JUDGE_MODEL = "claude-sonnet-5-5"

# ====================================================================== text helpers

_STOP = set("""a an the is are was were be been being of to in on at for from by with and or but if then than
so as that this these those it its into over under about what which who whom whose when where why how do does
did can could should would will shall may might must i me my we our you your he she they them their there here
any all each some such only own same too very just also please tell much many stand mean""".split())

REFUSAL_RE = re.compile(r"\b(i don.t know|i do not know|not (in|covered by) the (provided )?(documents|handbook)|"
                        r"cannot answer|can.t answer|no information)\b", re.I)


def normalize(text: str) -> str:
    """Lowercase, strip accents, punctuation, articles and extra spaces."""
    text = unicodedata.normalize("NFKD", str(text or "")).encode("ascii", "ignore").decode()
    text = text.lower()
    text = re.sub(r"\[[^\]]*\]", " ", text)          # citation markers like [doc-id]
    text = re.sub(r"[^a-z0-9%.:\- ]", " ", text)
    text = re.sub(r"(?<!\d)[.:](?!\d)", " ", text)  # keep 0.7 and 06:00, drop sentence dots
    text = re.sub(r"\b(a|an|the)\b", " ", text)
    return " ".join(text.split())


def _stem(w: str) -> str:
    for suf in ("ing", "ed", "es", "s"):
        if len(w) > len(suf) + 2 and w.endswith(suf):
            w = w[: -len(suf)]
            break
    if len(w) > 4 and w.endswith("e"):
        w = w[:-1]
    return w


def words(text: str) -> list[str]:
    """Content words: normalised, stop words dropped, lightly stemmed."""
    return [_stem(w) for w in re.findall(r"[a-z0-9]+", normalize(text)) if w not in _STOP]


def numbers(text: str) -> set[str]:
    """Numbers in a text, e.g. {'8', '0.7', '06:00', '2400'}."""
    found = re.findall(r"\d+(?:[.,:]\d+)*", str(text or ""))
    return {n.replace(",", "") for n in found}


def is_refusal(text: str) -> bool:
    """True if the answer declines to answer."""
    return bool(REFUSAL_RE.search(str(text or "")))


# ====================================================================== questions and labels


def _keep_none(df, cols):
    """pandas 3 stores None as NaN in string columns; keep None so `x is None` works."""
    for c in cols:
        if c in df.columns:
            df[c] = df[c].astype(object).where(df[c].notna(), None)
    return df


def questions_df():
    """The 45 Helios questions: id, question, answer (None if unanswerable), type, doc_ids."""
    import pandas as pd

    rows = helios.questions()
    df = pd.DataFrame([{"id": q["id"], "question": q["question"], "answer": q["answer"],
                        "type": q["type"], "doc_ids": q["doc_ids"]} for q in rows])
    return _keep_none(df, ["answer"])


# Each entry: a list of groups; every group needs one of its alternatives present.
KEY_FACTS = {
    "q01": [["8 minutes"]], "q02": [["two", "2 crew"]], "q03": [["never", "cannot", "can't", "not allowed"]],
    "q04": [["2 hours"]], "q05": [["6.5 hours"]], "q06": [["60%"], ["75%"]], "q07": [["P-2"]],
    "q08": [["every week", "weekly"]], "q09": [["06:00"], ["18:00"]], "q10": [["28 days"]],
    "q11": [["93%"]], "q12": [["2,400", "2400"]], "q13": [["20.5%"], ["21.5%"]], "q14": [["12"], ["Module D"]],
    "q15": [["0.4%"]], "q16": [["90 days"]], "q17": [["36"]], "q18": [["shed", "switched off"]],
    "q19": [["mask"], ["leave"], ["hatch"]], "q20": [["Priya Raman", "medical officer"], ["commander"]],
    "q21": [["Module A"]], "q22": [["Tomas Lindqvist"]], "q23": [["06:00"]], "q24": [["19:00"]],
    "q25": [["2.5 hours"]], "q26": [["Sunday"], ["15:00"]], "q27": [["24 hours"]], "q28": [["4 hours"]],
    "q29": [["-80"]], "q30": [["Module D"]], "q31": [["Module F"]], "q32": [["Module D"]],
    "q33": [["60 days"]], "q34": [["30 days"]], "q35": [["90 days"]], "q36": [["mineral"], ["valve"]],
    "q37": [["Environmental Control and Life Support"]],
    "q38": [["Noor Haddad"], ["Priya Raman"], ["Module B"]], "q39": [["Kenji Watanabe"], ["botanist"]],
    "q40": [["Module E"], ["scrubber"]], "q41": [["Ferreira"], ["systems specialist"]],
}
# Facts that make an answer wrong even when the right fact is also there.
WRONG_FACTS = {"q01": ["5 minutes"], "q07": ["P-1"]}
# (qid, answer substring) -> label: places where a human reads it differently from the rule.
HUMAN_OVERRIDES: dict[tuple[str, str], int] = {}


def _has(text: str, alt: str) -> bool:
    if re.search(r"\d", alt):  # numbers must not be part of a bigger number: "2 hours" is not in "12 hours"
        return re.search(r"(?<![\d.,])" + re.escape(alt.lower()), str(text).lower()) is not None
    if re.search(r"[%:.\-]", alt):
        return alt.lower() in str(text).lower()
    return re.search(r"\b" + re.escape(normalize(alt)), normalize(text)) is not None


def human_label(qid: str, answer: str) -> int:
    """The crew's verdict on one answer: 1 = acceptable, 0 = not."""
    for (q, sub), lab in HUMAN_OVERRIDES.items():
        if q == qid and sub in answer:
            return lab
    if qid not in KEY_FACTS:  # unanswerable
        return int(is_refusal(answer))
    if is_refusal(answer):
        return 0
    if any(_has(answer, w) for w in WRONG_FACTS.get(qid, [])):
        return 0
    return int(all(any(_has(answer, alt) for alt in group) for group in KEY_FACTS[qid]))


# ====================================================================== ORBIT


@functools.lru_cache(maxsize=1)
def _docs_by_id():
    return {d["id"]: d for d in helios.handbook(include_superseded=True)}


@functools.lru_cache(maxsize=1)
def _doc_index():
    docs = helios.handbook(include_superseded=True)
    return docs, aikit.embed([d["title"] + ". " + d["text"] for d in docs])


class Retriever:
    """Top-k handbook search: cosine similarity of aikit.embed vectors."""

    def __init__(self, k: int = 3, titles: bool = True):
        self.k, self.titles = k, titles

    def search(self, question: str) -> list[dict]:
        cached = _cache().get("retrieval", {}).get(question)
        if cached is not None and self.k <= len(cached):
            by_id = _docs_by_id()
            return [by_id[i] for i in cached[: self.k]]
        import numpy as np

        docs, D = _doc_index()
        s = D @ aikit.embed(question)
        return [docs[i] for i in np.argsort(-s, kind="stable")[: self.k]]


# Words that frame a question ("how long", "what role") rather than name its subject.
FRAME_WORDS = set(words(
    "long longest often maximum minimum length big size normal level happen per far during role contain share "
    "wake up time temperature open within out minute two not much many number kind type need should make get "
    "use someone s check stand mean question answer"))

_EAGER_RE = re.compile(r"always (give|answer|provide|reply)|as helpful as possible|best guess|never (refuse|say you don.t know)", re.I)
_REFUSE_RE = re.compile(r"(don.t|do not) know|say so\b|\brefuse|unanswerable|cannot be answered|not in the (documents|handbook)", re.I)


def _off_topic(req) -> bool:
    """True when the question names something the documents never mention."""
    docs = aikit.extract_documents(req.all_text)
    q = re.sub(r"<document\b.*?</document>", " ", req.last_user_text, flags=re.S)
    asked = re.findall(r"[^.!?\n>]*\?", q)
    dw = set(words(" ".join(t for _, t in docs)))
    pre = {w[:5] for w in dw}
    topic = [w for w in words(asked[-1] if asked else q) if w not in FRAME_WORDS and len(w) >= 2 and w.isalpha()]
    return any(w not in dw and w[:5] not in pre for w in topic)


def orbit_model():
    """ORBIT's answering model. See the module docstring for how the system prompt matters."""
    normal, eager = aikit.grounded(threshold=0.34), aikit.grounded(threshold=0.2)

    def respond(req):
        sys_ = req.system or ""
        base = eager if _EAGER_RE.search(sys_) else normal
        if _REFUSE_RE.search(sys_) and _off_topic(req):
            return aikit.REFUSAL
        return base(req)

    return respond


BASE_SYSTEM = "You are ORBIT, the assistant on research station Helios-7. Answer crew questions using the handbook documents provided."

VERSIONS = {
    "v1": {"k": 1, "titles": False, "cite": False, "system": BASE_SYSTEM},
    "v2": {"k": 3, "titles": True, "cite": True, "system": BASE_SYSTEM},
    "v3": {"k": 3, "titles": True, "cite": True,
           "system": BASE_SYSTEM + " Be as helpful as possible: always give the crew an answer."},
    "v4": {"k": 3, "titles": True, "cite": True,
           "system": BASE_SYSTEM + " Be as helpful as possible: always give the crew an answer."
                                   " If the documents do not contain the answer, say you don't know."},
}


class Orbit:
    """ORBIT = retriever + prompt + model.

    orbit = Orbit(k=3, titles=True, cite=True, system=BASE_SYSTEM)
    out = orbit.answer("How long do spacewalkers prebreathe oxygen?")
    out -> {"answer": "...", "retrieved": ["eva-prep-checklist", ...]}
    `orbit.client` is a FakeClaude, so `orbit.client.calls` has tokens, cost and latency.
    """

    def __init__(self, k: int = 3, titles: bool = True, cite: bool = True, system: str = BASE_SYSTEM,
                 model: str = MODEL, client: FakeClaude | None = None, outage: bool = False):
        self.retriever = Retriever(k, titles)
        self.cite, self.system, self.model, self.outage = cite, system, model, outage
        self.client = client or FakeClaude(orbit_model(), clock=VirtualClock())

    def prompt(self, question: str, docs: list[dict]) -> str:
        ctx = "\n".join(f'<document id="{d["id"]}">{(d["title"] + ". ") if self.retriever.titles else ""}{d["text"]}</document>'
                        for d in docs)
        ins = "Answer using only the documents." + (" Cite the document id in brackets after each sentence." if self.cite else "")
        return f"{ctx}\n\n{ins}\n\nQuestion: {question}"

    def answer(self, question: str) -> dict:
        docs = [] if self.outage else self.retriever.search(question)
        r = self.client.messages.create(model=self.model, max_tokens=300, system=self.system,
                                        messages=[{"role": "user", "content": self.prompt(question, docs)}])
        return {"answer": r.text, "retrieved": [d["id"] for d in docs]}


def make_orbit(version: str = "v2", **overrides) -> Orbit:
    cfg = dict(VERSIONS[version])
    cfg.update(overrides)
    return Orbit(**cfg)


# ---- cache: ORBIT runs are deterministic but take a few seconds, so the standard
# versions (and the top-5 retrieval for every question) are stored in a JSON file.
# The cache records a fingerprint of aikit.py, this file and the Helios data; if any of
# them change, the cache is ignored and runs are computed live (correct, just slower).
# Rebuild it with:  .venv/bin/python runner/kits/llm_evaluation.py --rebuild

_CACHE_PATH = Path(__file__).with_name("llm_evaluation_cache.json")


def _fingerprint() -> str:
    h = hashlib.sha256()
    files = [Path(aikit.__file__), Path(__file__), aikit.DATA_DIR / "questions.jsonl"]
    files += sorted((aikit.DATA_DIR / "handbook").glob("*.md"))
    for f in files:
        h.update(f.name.encode())
        h.update(f.read_bytes())
    return h.hexdigest()


@functools.lru_cache(maxsize=1)
def _cache() -> dict:
    try:
        data = json.loads(_CACHE_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if data.get("fingerprint") == _fingerprint() else {}


def _cfg_key(cfg: dict) -> str:
    return json.dumps({k: cfg[k] for k in ("k", "titles", "cite", "system")}, sort_keys=True)


def _compute_run(cfg: dict) -> list:
    orbit = Orbit(**cfg)
    return [[q["id"], orbit.answer(q["question"])] for q in helios.questions()]


@functools.lru_cache(maxsize=16)
def _run(version: str, system: str | None = None):
    cfg = dict(VERSIONS[version])
    if system is not None:
        cfg["system"] = system
    hit = _cache().get("runs", {}).get(_cfg_key(cfg))
    return hit if hit is not None else _compute_run(cfg)


def run_orbit(version: str = "v2", system: str | None = None):
    """Answers of one ORBIT version to all 45 questions, with human labels.
    Columns: qid, question, type, gold, answer, retrieved, gold_retrieved, human."""
    import pandas as pd

    qs = {q["id"]: q for q in helios.questions()}
    rows = []
    for qid, out in _run(version, system):
        q = qs[qid]
        rows.append({"qid": qid, "question": q["question"], "type": q["type"], "gold": q["answer"],
                     "answer": out["answer"], "retrieved": out["retrieved"],
                     "gold_retrieved": bool(q["doc_ids"]) and set(q["doc_ids"]) <= set(out["retrieved"]),
                     "human": human_label(qid, out["answer"])})
    return _keep_none(pd.DataFrame(rows), ["gold"])


def failure_cause(row) -> str:
    """The upstream-most failure for one labelled row (used for the error-analysis data)."""
    if row["human"] == 1:
        return "ok"
    ans = row["answer"]
    if row["type"] == "unanswerable":
        return "hallucination"
    if not row["retrieved"]:
        return "hallucination"
    if re.search(r"-2024\]|5 minutes", ans):
        return "stale document"
    if not row["gold_retrieved"] and not any(d in row["retrieved"] for d in _gold_docs(row["qid"])):
        return "retrieval miss"
    if is_refusal(ans):
        return "over-refusal"
    return "incomplete answer"


def _gold_docs(qid):
    return next(q["doc_ids"] for q in helios.questions() if q["id"] == qid)


@functools.lru_cache(maxsize=1)
def _log_rows():
    import pandas as pd

    parts = []
    for v in ("v1", "v2"):
        d = run_orbit(v)
        d.insert(0, "version", v)
        parts.append(d)
    log = pd.concat(parts, ignore_index=True)
    log["cause"] = log.apply(failure_cause, axis=1)
    log.insert(0, "id", [f"r{i + 1:03d}" for i in range(len(log))])
    return log


def orbit_log():
    """90 rows: ORBIT v1 and v2 on all 45 questions, with `human` labels and `cause`."""
    return _keep_none(_log_rows().copy(), ["gold"])


# ====================================================================== more labelled data

UNANSWERABLE_REF = "UNANSWERABLE: the handbook does not contain this information."


def reference_for(gold) -> str:
    """Reference text to show a judge: the gold answer, or the UNANSWERABLE marker."""
    return UNANSWERABLE_REF if gold is None or gold != gold else str(gold)


PAD_BEFORE = "Great question! I checked the Helios-7 handbook carefully for you, so here is what it says. "
PAD_AFTER = " I hope this helps, and do let me know if there is anything else you need. Stay safe up there!"


def pad(answer: str) -> str:
    """Wrap an answer in friendly filler: same facts, three times the length."""
    return PAD_BEFORE + answer + PAD_AFTER


def wrong_number(answer: str, qid: str | None = None, seed: int = 0) -> str:
    """Change one number in the answer (outside citation brackets): the first number
    of the question's key facts if `qid` is given, else the first number."""
    rng = random.Random(seed)
    body = re.sub(r"\[[^\]]*\]", lambda m: "\0" * len(m.group(0)), answer)
    targets = [re.search(r"\d+(?:\.\d+)?", alt).group(0) for g in KEY_FACTS.get(qid, []) for alt in g
               if re.search(r"\d", alt)]
    m = None
    for t in targets:
        m = re.search(rf"(?<![\d.]){re.escape(t)}(?![\d])", body)
        if m:
            break
    m = m or re.search(r"\d+(?:\.\d+)?", body)
    if not m:
        return answer
    old = m.group(0)
    if "." in old:
        new = f"{float(old) + rng.choice([-1.5, 1.5, 2.5]):.1f}"
    else:
        new = str(int(old) + rng.choice([2, 3, 4, 6, 10])).zfill(len(old))
    return answer[: m.start()] + new + answer[m.end():]


@functools.lru_cache(maxsize=1)
def _judge_rows():
    import pandas as pd

    rng = random.Random(7)
    qs = {q["id"]: q for q in helios.questions()}
    v1, v2, v3 = run_orbit("v1"), run_orbit("v2"), run_orbit("v3")
    rows = []

    def add(src, qid, answer):
        q = qs[qid]
        rows.append({"qid": qid, "question": q["question"], "type": q["type"], "reference": reference_for(q["answer"]),
                     "answer": answer, "source": src, "human": human_label(qid, answer)})

    for _, r in v2.iterrows():
        add("v2", r.qid, r.answer)
    for _, r in v1[(v1.human == 0) | (v1.type == "unanswerable")].iterrows():
        add("v1", r.qid, r.answer)
    for _, r in v3[v3.answer != v2.answer].iterrows():
        add("v3", r.qid, r.answer)
    v4 = run_orbit("v4")
    for _, r in v4[(v4.answer != v2.answer) & (v4.type == "unanswerable")].iterrows():
        add("v4", r.qid, r.answer)
    good = [r for _, r in v2.iterrows() if r.human == 1 and r.type != "unanswerable"]
    rng.shuffle(good)
    outage = Orbit(**VERSIONS["v2"], outage=True)
    for r in good[:8]:
        add("outage", r.qid, outage.answer(r.question)["answer"])
    for r in good[8:16]:
        add("padded", r.qid, pad(r.answer))
    with_num = [r for r in good[16:] if any(re.search(r"\d", a) for g in KEY_FACTS[r.qid] for a in g)]
    for i, r in enumerate(with_num[:8]):
        add("wrong number", r.qid, wrong_number(r.answer, r.qid, seed=i))
    df = pd.DataFrame(rows)
    # keep 80: drop some plain v2 passes
    drop = df[(df.source == "v2") & (df.human == 1)].sample(n=len(df) - 80, random_state=3).index
    df = df.drop(drop).reset_index(drop=True)
    # stratified dev/test split: shuffle inside each (source, human, refusal) group, then alternate
    df["_ref"] = df.answer.map(is_refusal)
    order = []
    for _, g in df.groupby(["source", "human", "_ref"], sort=True):
        idx = list(g.index)
        random.Random(11).shuffle(idx)
        order += idx
    df["split"] = ""
    for i, ix in enumerate(order):
        df.loc[ix, "split"] = "dev" if i % 2 == 0 else "test"
    df = df.drop(columns="_ref")
    df.insert(0, "id", [f"j{i + 1:02d}" for i in range(len(df))])
    return df


def judge_set():
    """80 ORBIT outputs labelled by the crew, for judge calibration.
    Columns: id, qid, question, type, reference, answer, source, human, split ('dev' or 'test')."""
    return _judge_rows().copy()


# ====================================================================== the LLM judge

_TAG = {t: re.compile(rf"<{t}>(.*?)</{t}>", re.S | re.I) for t in ("question", "reference", "response", "response_a", "response_b")}


def _features(rubric: str) -> dict:
    r = rubric.lower()
    has_ref_word = bool(re.search(r"reference|gold|expected answer|correct answer", r))
    return {
        "binary": bool(re.search(r"\bpass\b", r) and re.search(r"\bfail\b", r)),
        "scale": bool(re.search(r"\b(1|one)\s*(-|to|–)\s*(10|ten|5|five)\b|\bscale\b|\bscore\b", r)),
        "facts": has_ref_word and bool(re.search(r"contain|includ|match|agree|consistent|state|fact|same", r)),
        "contradict": bool(re.search(r"contradict|conflict|inconsistent|different (number|value)", r)),
        "refusal": bool(re.search(r"refus|don.t know|do not know|unanswerable|cannot be answered|declin", r)),
        "length": bool(re.search(r"length|longer|verbos|padding|wordy|concise|filler", r)),
        "examples": len(re.findall(r"<example\b|\bexample \d", r)) >= 2,
        "tie": "tie" in r,
    }


def _contradicts(reference: str, response: str) -> bool:
    """True when the response states the reference's number in one sentence and a
    different number with the same unit in another, very similar sentence
    (e.g. "hold for 8 minutes" and "hold for 5 minutes")."""
    ref_pairs = {(n, _stem(u)) for n, u in re.findall(r"(\d+(?:\.\d+)?)\s*(%|[a-z]+)", normalize(reference))}
    sents = [x for x in re.split(r"(?<=[.!?])\s+", re.sub(r"\[[^\]]*\]", "", response)) if x.strip()]
    info = []
    for x in sents:
        pairs = {(n, _stem(u)) for n, u in re.findall(r"(\d+(?:\.\d+)?)\s*(%|[a-z]+)", normalize(x))}
        info.append((set(words(x)), pairs))
    for i, (wi, pi) in enumerate(info):
        right = pi & ref_pairs
        for j, (wj, pj) in enumerate(info):
            if i == j or not right:
                continue
            units = {u for _, u in right}
            other = {(n, u) for n, u in pj if u in units} - ref_pairs
            if other and len(wi & wj) / max(1, len(wi | wj)) >= 0.5:
                return True
    return False


def fact_check(reference: str, response: str, contradict: bool = False) -> bool:
    """The judge's reference check: every number in the reference appears in the
    response, and >= 75% of the reference's content words do. With `contradict`,
    it also fails responses that contradict themselves about the reference's number."""
    ref_n = numbers(reference)
    resp_n = numbers(re.sub(r"\[[^\]]*\]", "", response))
    if not ref_n <= resp_n:
        return False
    rw = {w for w in words(reference) if not w.isdigit()}
    resp_w = set(words(response))
    if rw and len(rw & resp_w) / len(rw) < 0.75:
        return False
    return not (contradict and _contradicts(reference, response))


def _plausibility(question: str, response: str) -> float:
    """What a judge with no reference and no criteria goes on: is it on topic, and does it sound sure?"""
    if is_refusal(response):
        return 0.15
    qw, rw = set(words(question)), set(words(response))
    overlap = len(qw & rw) / max(1, len(qw))
    specific = 0.15 if re.search(r"\d", response) else 0.0
    authority = 0.3 if re.search(r"according to|standard (station )?procedure|as set by|officially", response, re.I) else 0.0
    n = len(response.split())
    return 0.3 + 0.5 * overlap + specific + authority + (0.15 if n > 30 else 0.0)


_FLIP = {"small": 0.08, "medium": 0.03, "large": 0.01}
_SD = {"small": 2.0, "medium": 1.4, "large": 1.0}


def _rng_for(req) -> random.Random:
    h = hashlib.sha256((req.model + "\n" + req.system + "\n" + req.context_text).encode()).hexdigest()
    return random.Random(int(h[:16], 16))


def _assess(f: dict, question: str, reference: str | None, response: str, rng: random.Random):
    """(passes: bool, score_0_1: float, reason: str) for one response."""
    refusal = is_refusal(response)
    unans = reference is not None and reference.upper().startswith("UNANSWERABLE")
    if f["refusal"] and reference is not None:
        if unans:
            return (refusal, 1.0 if refusal else 0.0,
                    "The handbook has no answer; the response " + ("declines, as it should." if refusal else "makes one up."))
        if refusal:
            return False, 0.0, "The response declines although the reference has an answer."
    if refusal:
        return False, 0.1, "The response gives the crew nothing useful."
    if f["facts"] and reference is not None and not unans:
        ok = fact_check(reference, response, f["contradict"])
        return ok, 0.9 if ok else 0.25, ("The response states the reference's key facts." if ok
                                         else "The response misses or changes facts from the reference.")
    p = _plausibility(question, response) + rng.uniform(-0.15, 0.15)
    if f["length"]:
        p -= 0.15 if len(response.split()) > 30 else 0.0
    return p >= 0.7, min(1.0, p), "The response looks relevant and confident." if p >= 0.7 else "The response seems off topic."


def judge_model():
    """Responder for a FakeClaude used as an LLM judge. See the module docstring."""

    def respond(req):
        text = req.system + "\n" + req.context_text
        tags = {t: (rx.search(text).group(1).strip() if rx.search(text) else None) for t, rx in _TAG.items()}
        rubric = text
        for t in _TAG:
            rubric = _TAG[t].sub(" ", rubric)
        f = _features(rubric)
        rng = _rng_for(req)
        flip = _FLIP[req.tier] / (2 if f["examples"] else 1)
        q, ref = tags["question"] or "", tags["reference"]
        wants_tag = "<verdict>" in rubric.lower() or "<winner>" in rubric.lower() or "<score>" in rubric.lower()

        if tags["response_a"] is not None and tags["response_b"] is not None:
            a, b = tags["response_a"], tags["response_b"]
            pa, sa, _ = _assess(f, q, ref, a, random.Random(1))
            pb, sb, _ = _assess(f, q, ref, b, random.Random(1))
            criteria = f["facts"] or f["refusal"]
            qa, qb = (float(pa), float(pb)) if criteria else (sa, sb)
            la, lb = len(a.split()), len(b.split())
            if not f["length"] and not criteria:      # verbosity bias
                qa += 0.25 if la >= 1.4 * lb else 0.0
                qb += 0.25 if lb >= 1.4 * la else 0.0
            if not criteria:                           # position bias: the first slot looks better
                qa += 0.3
            if abs(qa - qb) < 0.01:                    # a tie on the criteria
                if not f["length"] and max(la, lb) >= 1.4 * min(la, lb):
                    win = "A" if la > lb else "B"
                    why = "Both are similar; the more detailed response is better."
                else:
                    win, why = "A", "Both responses are similar in quality."
            else:
                win = "A" if qa > qb else "B"
                why = f"Response {win} meets the criteria better."
            return f"{why}\n<winner>{win}</winner>" if wants_tag else f"{why}\nWinner: {win}"

        resp = tags["response"] if tags["response"] is not None else req.last_user_text
        passed, score, why = _assess(f, q, ref, resp, rng)
        if f["scale"] and not f["binary"]:
            base = 9.0 if passed and (f["facts"] or f["refusal"]) else 2.5 + 7.0 * score if not (f["facts"] or f["refusal"]) else 3.0
            if not f["length"]:
                base += 1.0 if len(resp.split()) > 30 else 0.0
            s = int(min(10, max(1, round(base + rng.gauss(0, _SD[req.tier])))))
            return f"{why}\n<score>{s}</score>" if wants_tag else f"{why}\nScore: {s}/10"
        if rng.random() < flip:
            passed = not passed
        v = "PASS" if passed else "FAIL"
        return f"<reasoning>{why}</reasoning>\n<verdict>{v}</verdict>" if wants_tag else f"Reasoning: {why}\nVerdict: {v}"

    return respond


def parse_verdict(text: str) -> int | None:
    """1 for PASS, 0 for FAIL, None if neither is found."""
    m = re.search(r"\b(PASS|FAIL)\b", text)
    return None if not m else int(m.group(1) == "PASS")


# ====================================================================== pairwise, production and comparison data


def pairwise_pairs():
    """Pairs of answers to the same question, for pairwise judging.
    Columns: pair_id, qid, question, reference, x, y, kind, human_x, human_y.
    kind: 'v1 vs v2' (the versions answer differently) or 'plain vs padded' (same facts, y is padded)."""
    import pandas as pd

    v1, v2 = run_orbit("v1"), run_orbit("v2")
    rows = []
    for (_, a), (_, b) in zip(v1.iterrows(), v2.iterrows()):
        if normalize(a.answer) != normalize(b.answer) and not (is_refusal(a.answer) and is_refusal(b.answer)):
            rows.append({"qid": a.qid, "question": a.question, "reference": reference_for(a.gold),
                         "x": a.answer, "y": b.answer, "kind": "v1 vs v2", "human_x": a.human, "human_y": b.human})
    good = v2[(v2.human == 1) & (v2.type != "unanswerable")]
    for _, r in good.iloc[::3].iterrows():
        rows.append({"qid": r.qid, "question": r.question, "reference": reference_for(r.gold),
                     "x": r.answer, "y": pad(r.answer), "kind": "plain vs padded", "human_x": 1, "human_y": 1})
    df = pd.DataFrame(rows)
    df.insert(0, "pair_id", [f"p{i + 1:02d}" for i in range(len(df))])
    return df


PRODUCTION_MIX = {"factual": 0.6, "multi-hop": 0.2, "unanswerable": 0.2}


def production_sample(version: str = "v2", n: int = 300, seed: int = 5):
    """n crew questions sampled in the real traffic mix (60% factual, 20% multi-hop,
    20% unanswerable), with the crew's verdict on `version`'s answer.
    Columns: qid, type, human."""
    import pandas as pd

    res = run_orbit(version)
    rng = random.Random(seed)
    by_type = {t: res[res.type == t] for t in PRODUCTION_MIX}
    rows = []
    for _ in range(n):
        t = rng.choices(list(PRODUCTION_MIX), weights=list(PRODUCTION_MIX.values()))[0]
        r = by_type[t].iloc[rng.randrange(len(by_type[t]))]
        rows.append({"qid": r.qid, "type": t, "human": int(r.human)})
    return pd.DataFrame(rows)


def dev_set_v0():
    """The first eval set ORBIT's developer wrote while building v2: 20 factual
    questions, mostly ones they had already seen work (18 pass, 2 fail on v2)."""
    qs = questions_df()
    v2 = run_orbit("v2").set_index("qid")
    fact = qs[qs.type == "factual"]
    ok = fact[fact.id.map(v2.human) == 1].sample(n=18, random_state=4)
    bad = fact[fact.id.map(v2.human) == 0].sample(n=2, random_state=4)
    import pandas as pd

    return pd.concat([ok, bad]).sort_values("id").reset_index(drop=True)


def big_comparison(n: int = 400, seed: int = 21):
    """n labelled production conversations, each answered by v2 and by the v3
    candidate (paired), in the production mix. Columns: case, type, v2, v3 (1 = pass).
    v3 is slightly better on factual questions and much worse on unanswerable ones."""
    import numpy as np
    import pandas as pd

    rng = np.random.default_rng(seed)
    p_v2 = {"factual": 0.84, "multi-hop": 0.50, "unanswerable": 0.75}
    gain = {"factual": 0.25, "multi-hop": 0.0, "unanswerable": 0.0}    # P(v3 fixes a v2 failure)
    loss = {"factual": 0.0, "multi-hop": 0.0, "unanswerable": 0.65}    # P(v3 breaks a v2 pass)
    types = rng.choice(list(PRODUCTION_MIX), size=n, p=list(PRODUCTION_MIX.values()))
    rows = []
    for i, t in enumerate(types):
        a = int(rng.random() < p_v2[t])
        b = (0 if rng.random() < loss[t] else 1) if a else (1 if rng.random() < gain[t] else 0)
        rows.append({"case": f"c{i + 1:03d}", "type": t, "v2": a, "v3": b})
    return pd.DataFrame(rows)


# ====================================================================== error analysis data

SAFETY_QIDS = {"q01", "q02", "q03", "q04", "q05", "q15", "q19", "q21", "q30", "q31", "q32"}


@functools.lru_cache(maxsize=1)
def _failure_rows():
    import pandas as pd

    log = orbit_log()
    fails = log[log.human == 0].drop(columns=["id"])
    v3 = run_orbit("v3")
    v3 = v3[(v3.type == "unanswerable") & (v3.human == 0)].copy()
    v3.insert(0, "version", "v3")
    v3["cause"] = v3.apply(failure_cause, axis=1)
    js = judge_set()
    out = js[js.source == "outage"]
    qs = {q["id"]: q for q in helios.questions()}
    outage = pd.DataFrame([{"version": "v2 (outage)", "qid": r.qid, "question": r.question, "type": r.type,
                            "gold": qs[r.qid]["answer"], "answer": r.answer, "retrieved": [],
                            "gold_retrieved": False, "human": 0, "cause": "hallucination"} for _, r in out.iterrows()])
    df = pd.concat([fails, v3, outage], ignore_index=True)
    df["safety"] = df.qid.isin(SAFETY_QIDS)
    df.insert(0, "trace_id", [f"t{i + 1:02d}" for i in range(len(df))])
    return df


def failures():
    """Failed ORBIT traces for error analysis: v1/v2 failures, v3 answering unanswerable
    questions, and answers given during a retrieval outage. Columns: trace_id, version,
    qid, question, type, gold, answer, retrieved, gold_retrieved, human, cause, safety."""
    return _keep_none(_failure_rows().copy(), ["gold"])


# ====================================================================== cache maintenance


def build_cache(path: Path = _CACHE_PATH) -> dict:
    """Recompute every cached run (slow) and write the cache file."""
    import numpy as np

    docs, D = _doc_index()
    retrieval = {}
    for q in helios.questions():
        sc = D @ aikit.embed(q["question"])
        retrieval[q["question"]] = [docs[i]["id"] for i in np.argsort(-sc, kind="stable")[:5]]
    data = {"fingerprint": _fingerprint(), "retrieval": retrieval, "runs": {}}
    _cache.cache_clear()
    _run.cache_clear()
    for cfg in VERSIONS.values():
        data["runs"][_cfg_key(cfg)] = _compute_run(dict(cfg))
    path.write_text(json.dumps(data, ensure_ascii=False, indent=0), encoding="utf-8")
    _cache.cache_clear()
    return data


def verify_cache() -> list[str]:
    """Compare the cache with a fresh computation. Returns a list of mismatches."""
    data = _cache()
    problems = [] if data else ["cache missing or stale (fingerprint mismatch): run with --rebuild"]
    for name, cfg in VERSIONS.items():
        live = json.loads(json.dumps(_compute_run(dict(cfg))))
        if data.get("runs", {}).get(_cfg_key(cfg)) != live:
            problems.append(f"run {name} differs from the cache")
    return problems


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    if "--rebuild" in sys.argv:
        build_cache()
        print("cache rebuilt:", _CACHE_PATH)
    print("mismatches:", verify_cache() or "none")


# ====================================================================== a batch for code-based checks


def check_batch():
    """35 ORBIT v2-style outputs for assertion suites. Some are fine; some are padded,
    cite a document that was never retrieved, lost their citations, or answer a question
    the handbook can't answer. Columns: id, qid, type, question, answer, retrieved, defect."""
    import pandas as pd

    v2 = run_orbit("v2").set_index("qid")
    v3 = run_orbit("v3").set_index("qid")
    rows = []

    def add(qid, answer, retrieved, defect):
        r = v2.loc[qid]
        rows.append({"qid": qid, "type": r.type, "question": r.question, "answer": answer,
                     "retrieved": list(retrieved), "defect": defect})

    for i in range(1, 25):
        q = f"q{i:02d}"
        add(q, v2.loc[q].answer, v2.loc[q].retrieved, "none")
    for q in ("q25", "q26", "q27"):
        add(q, pad(v2.loc[q].answer), v2.loc[q].retrieved, "padded")
    for q in ("q28", "q29", "q33"):
        add(q, re.sub(r"\[[^\]]+\]", "[maintenance-log]", v2.loc[q].answer, count=1), v2.loc[q].retrieved, "bad citation")
    for q in ("q31", "q32"):
        add(q, re.sub(r"\s*\[[^\]]+\]", "", v2.loc[q].answer), v2.loc[q].retrieved, "no citation")
    for q in ("q42", "q45"):
        add(q, v3.loc[q].answer, v3.loc[q].retrieved, "answered unanswerable")
    add("q43", v2.loc["q43"].answer, v2.loc["q43"].retrieved, "none")
    df = pd.DataFrame(rows)
    df.insert(0, "id", [f"o{i + 1:02d}" for i in range(len(df))])
    return df


def key_facts_pass(qid: str, answer: str) -> int:
    """The key-facts check (KEY_FACTS per question, refusal rule for unanswerable
    questions) used as the `correct` scorer in harness lessons. It is the rule the
    crew's labels follow, so it agrees with them on the labelled set."""
    return human_label(qid, answer)
