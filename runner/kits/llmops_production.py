"""Helpers for the llmops-production course.

Import in pre_code:  from kits.llmops_production import ...

The world: ORBIT, the Helios-7 station assistant, is live. These helpers give
each lesson a production-like system to measure, break and fix, deterministically.

    EVAL, grade(item, text)     41 crew questions with key facts; 11 are "hard"
    SYSTEM, RULES, HANDBOOK_BLOCK
                                ORBIT's production system prompt (about 3,950 tokens:
                                rules + the whole handbook)
    CONCISE                     an instruction that makes ORBIT answer first, briefly
    orbit_model()               responder for aikit.FakeClaude: long, padded answers by
                                default; short ones when asked; the small tier gets hard
                                questions wrong; says UNSURE when allowed to
    run_eval(client, ...)       run every EVAL question once, return a DataFrame
    summarize(df)               p50/p95 latency, TTFT p95, accuracy, cost
    OpsClaude                   FakeClaude plus per-request `timeout=`, a slow tail,
                                model outages, and a corrected `retry_after` on 429s
                                (for reliability lessons)
    traces()                    aikit.helios.traces() with the day-11 429 burst restored
                                and a ttft_ms column for llm spans
    requests_log()              one row per ORBIT request with the question text and
                                the crew's feedback (thumbs, rephrased)
    PROMPT_HISTORY, release_log()
                                prompt versions v1-v4 and the production log they made
    app_logs()                  an afternoon of JSON application logs (structured-logs lesson)
"""

from __future__ import annotations

import hashlib
import json
import math
import re

import numpy as np

import aikit
from aikit import (APIError, APITimeoutError, BadRequestError, FakeClaude, AsyncFakeClaude,  # noqa: F401
                   InternalServerError, OverloadedError, RateLimitError, VirtualClock, count_tokens, helios)

MODEL = "claude-sonnet-5-5"
SMALL = "claude-haiku-4-5"
LARGE = "claude-opus-5-5"
PRICES = aikit.PRICES

# ====================================================================== the handbook prompt

HANDBOOK = helios.handbook(include_superseded=False)
DOCS = {d["id"]: d for d in HANDBOOK}


def doc_block(d: dict) -> str:
    """One handbook doc as a <document> block (the format ORBIT's prompt uses)."""
    return f'<document id="{d["id"]}" title="{d["title"]}">\n{d["text"]}\n</document>'


HANDBOOK_BLOCK = "<handbook>\n" + "\n".join(doc_block(d) for d in HANDBOOK) + "\n</handbook>"

RULES = ("You are ORBIT, the station assistant on research station Helios-7. "
         "Answer crew questions using the handbook documents below. Be friendly and thorough, "
         "explain the background, and never operate airlock controls.")

SYSTEM = RULES + "\n\n" + HANDBOOK_BLOCK

CONCISE = "Answer in one or two sentences. Put the answer first, with no preamble."

_CONCISE_RE = re.compile(r"\b(concise|concisely|brief|briefly|one or two sentences|one sentence|"
                         r"short answer|no preamble|answer first|at most \d+ words|under \d+ words)\b", re.I)
_UNSURE_RE = re.compile(r"\bUNSURE\b")

# ====================================================================== the eval set
# (id, facts that must appear, hard for the small model?, what the small model says instead)
_FACTS = {
    "q01": (["8 minutes", "0.7 bar"], False, "5 minutes at 0.5 bar."),
    "q02": (["two"], False, "One."),
    "q03": (["never"], False, "Yes, if the commander asks."),
    "q04": (["2 hours"], False, "30 minutes of pure oxygen."),
    "q05": (["6.5 hours"], False, "8 hours."),
    "q06": (["60%", "75%"], False, "Between 40% and 50%."),
    "q07": (["P-2"], True, "Check the nutrient dosing pump P-1."),
    "q08": (["week"], False, "Every month."),
    "q09": (["06:00", "18:00"], False, "At noon and midnight."),
    "q10": (["28 days"], False, "Every 14 days."),
    "q11": (["93%"], False, "About 75%."),
    "q12": (["2,400"], False, "1,000 litres."),
    "q13": (["20.5%", "21.5%"], False, "Between 18% and 19%."),
    "q14": (["12", "Module D"], True, "8 candles, in Module E."),
    "q15": (["0.4%"], False, "1%."),
    "q16": (["90 days"], False, "Every 30 days."),
    "q17": (["36 minutes"], True, "45 minutes."),
    "q18": (["shed"], True, "ORBIT sends an alert and the crew switches to backup power."),
    "q19": (["mask", "close the hatch"], True, "Ventilate the module and keep working until the smell fades."),
    "q20": (["Priya Raman", "commander"], False, "Any crew member."),
    "q21": (["Module A"], False, "In Module C."),
    "q22": (["Lindqvist"], False, "Kenji Watanabe."),
    "q23": (["06:00"], False, "07:30 station time."),
    "q24": (["19:00"], False, "18:00."),
    "q25": (["2.5 hours"], False, "1 hour."),
    "q26": (["Sundays", "15:00"], False, "Saturdays, 10:00 to 11:00."),
    "q27": (["24 hours"], False, "At least 2 hours."),
    "q28": (["4 hours"], False, "8 hours."),
    "q29": (["-80"], True, "-20 °C in the lab fridge."),
    "q30": (["Module D"], False, "Module A."),
    "q31": (["Module F"], False, "Module B."),
    "q32": (["Module D"], False, "Module C."),
    "q33": (["60 days"], False, "Every 30 days."),
    "q34": (["30 days"], False, "Every 90 days."),
    "q35": (["90 days"], False, "One year."),
    "q36": (["valve"], True, "A crew member left the watering cycle running overnight."),
    "q37": (["Environmental Control"], False, "Emergency Crew Life Safety System."),
    "q38": (["Haddad", "Module B"], True, "Kenji Watanabe; it is in Module C."),
    "q39": (["Watanabe", "botanist"], True, "Amara Okafor, the commander."),
    "q40": (["Module E", "scrubbers"], True, "Module D (Storage), which also holds the spare parts."),
    "q41": (["Ferreira"], True, "Tomas Lindqvist, the flight engineer."),
}
OVERCONFIDENT = {"q14", "q17"}  # small model is wrong here but does not say UNSURE
FALSE_ALARM = {"q05", "q26"}    # small model says UNSURE here although it would be right

_SECTION_TOPIC = {"eva": "eva", "life-support": "life-support", "hydroponics": "hydroponics", "laboratory": "laboratory",
                  "crew": "crew", "emergency": "emergency", "medical": "emergency", "it": "it", "comms": "crew",
                  "incidents": "hydroponics", "engineering": "life-support", "general": "crew", "logistics": "crew"}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9%:,.\- ]", " ", s.lower())).strip(" .?!")


def _build_eval() -> list[dict]:
    items = []
    for q in helios.questions():
        if q["id"] not in _FACTS:
            continue
        facts, hard, wrong = _FACTS[q["id"]]
        items.append({"id": q["id"], "question": q["question"], "answer": q["answer"], "doc_ids": q["doc_ids"],
                      "facts": facts, "hard": hard, "wrong": wrong, "type": q["type"],
                      "topic": _SECTION_TOPIC.get(DOCS[q["doc_ids"][0]]["section"], "crew")})
    return items


EVAL = _build_eval()
_BY_NORM = sorted(((_norm(it["question"]), it) for it in EVAL), key=lambda x: -len(x[0]))


def find_item(text: str) -> dict | None:
    """The EVAL item whose question appears in `text` (case and punctuation ignored)."""
    t = _norm(text)
    for nq, it in _BY_NORM:
        if nq in t:
            return it
    return None


def _has_fact(fact: str, text: str) -> bool:
    return re.search(r"(?<![A-Za-z0-9])" + re.escape(fact.lower()) + r"(?![A-Za-z0-9])", text.lower()) is not None


def grade(item: dict, text: str) -> bool:
    """True when every key fact of `item` appears in `text` (case-insensitive, whole words)."""
    return bool(text) and all(_has_fact(f, text) for f in item["facts"])


# ====================================================================== the ORBIT model

def _sentences(text: str) -> list[str]:
    text = re.sub(r"^#+ .*$", "", text, flags=re.M)
    parts = re.split(r"(?<!Dr\.)(?<=[.!?])\s+|\n+", text)
    return [p.strip() for p in parts if len(p.strip()) > 3]


_PREAMBLE = ("Good question! I went through the station handbook so I can give you the full picture, "
             "including the background that explains the answer.")
_OUTRO = ("I hope that helps. Let me know if you would like me to go through any of this in more detail, "
          "or if there is anything else I can look up for you.")


def verbose_answer(item: dict, answer: str) -> str:
    """ORBIT's default style: preamble, background, the answer, more background, an outro.
    Background sentences never contain the key facts, so only `answer` decides correctness."""
    sents = []
    for d in item["doc_ids"]:
        sents += [s for s in _sentences(DOCS[d]["text"]) if not any(_has_fact(f, s) for f in item["facts"])]
    half = (len(sents) + 1) // 2
    bg, rest = sents[:half], sents[half:]
    parts = [_PREAMBLE, "Some background first.", *bg, "So, to answer your question directly:", answer, *rest, _OUTRO]
    return " ".join(p for p in parts if p)


def orbit_model() -> callable:
    """Responder for FakeClaude that behaves like ORBIT's production model.

    - Recognises EVAL questions anywhere in the user message.
    - Default style is long and padded (verbose_answer): the answer sits in the middle,
      so a low `max_tokens` cuts it off. With a brevity instruction (see CONCISE)
      it replies with the answer only.
    - Answers correctly only if the gold documents are in the prompt
      (`<document id="...">`), otherwise it makes something up.
    - The small tier (haiku) gets hard questions wrong. If the prompt says it may reply
      UNSURE, it does so on most of them (and on a couple of easy ones).
    """

    def respond(req):
        text = req.last_user_text
        item = find_item(text)
        if item is None:
            return "I can help with questions about Helios-7 procedures, schedules and systems."
        instr = req.system + "\n" + text
        concise = bool(_CONCISE_RE.search(instr))
        unsure_ok = bool(_UNSURE_RE.search(instr))
        has_docs = all(f'id="{d}"' in req.all_text for d in item["doc_ids"])
        if req.tier == "small" and unsure_ok and (
                (item["hard"] and item["id"] not in OVERCONFIDENT) or item["id"] in FALSE_ALARM):
            return "UNSURE"
        if not has_docs or (req.tier == "small" and item["hard"]):
            ans = item["wrong"]
        else:
            ans = item["answer"]
        return ans if concise else verbose_answer(item, ans)

    return respond


def make_client(**kw) -> FakeClaude:
    """A FakeClaude running orbit_model() on its own VirtualClock (unless clock= is given)."""
    kw.setdefault("clock", VirtualClock())
    return FakeClaude(orbit_model(), **kw)


# ====================================================================== running the eval

def cached_system(system: str) -> list:
    """`system` as one text block with a cache breakpoint at its end."""
    return [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]


def run_eval(client, model: str = MODEL, system: str | None = None, rules: str | None = None,
             max_tokens: int = 600, cache: bool = False, route=None, items=None):
    """Ask every EVAL question once and return a DataFrame, one row per question:
    id, question, hard, model, answer, correct, latency_ms, ttft_ms, input_tokens,
    output_tokens, cache_read, cache_write, cost, stop_reason.

    system  full system prompt (default SYSTEM); or pass `rules` and the handbook is appended
    cache   put a cache breakpoint at the end of the system prompt
    route   optional function question -> model id (overrides `model` per question)
    """
    import pandas as pd

    if system is None:
        system = (rules + "\n\n" + HANDBOOK_BLOCK) if rules is not None else SYSTEM
    rows = []
    for it in items or EVAL:
        m = route(it["question"]) if route else model
        r = client.messages.create(model=m, max_tokens=max_tokens, system=cached_system(system) if cache else system,
                                   messages=[{"role": "user", "content": it["question"]}])
        c = client.calls[-1]
        rows.append({"id": it["id"], "question": it["question"], "hard": it["hard"], "model": m, "answer": r.text,
                     "correct": grade(it, r.text), "latency_ms": r.latency_ms, "ttft_ms": r.ttft_ms,
                     "input_tokens": r.usage.input_tokens, "output_tokens": r.usage.output_tokens,
                     "cache_read": r.usage.cache_read_input_tokens, "cache_write": r.usage.cache_creation_input_tokens,
                     "cost": c["cost"], "stop_reason": r.stop_reason})
    return pd.DataFrame(rows)


def summarize(df) -> dict:
    """Headline numbers for a run_eval DataFrame."""
    return {
        "p50_ms": float(np.percentile(df["latency_ms"], 50)),
        "p95_ms": float(np.percentile(df["latency_ms"], 95)),
        "ttft_p95_ms": float(np.percentile(df["ttft_ms"], 95)),
        "accuracy": float(df["correct"].mean()),
        "cost": float(df["cost"].sum()),
        "cost_per_q": float(df["cost"].mean()),
    }


# ====================================================================== OpsClaude

class OpsClaude(FakeClaude):
    """FakeClaude with three production problems you can switch on.

    timeout          default per-request timeout in seconds (requests can also pass
                     `timeout=`, like the real SDK). A call slower than this raises
                     APITimeoutError after exactly `timeout` seconds on the clock.
    slow_rate        chance a call hangs for an extra `slow_ms` (a slow tail), seeded
    slow_ms          extra time of a slow call, in ms
    outages          {model_substring: [(start_s, end_s), ...]}: calls to a matching
                     model in that window of the clock raise OverloadedError (529)
    """

    def __init__(self, respond=None, *, timeout: float | None = None, slow_rate: float = 0.0,
                 slow_ms: float = 45000.0, outages: dict | None = None, slow_seed: int = 3, **kw):
        if respond is None:
            respond = orbit_model()
        super().__init__(respond, **kw)
        self.default_timeout = timeout
        self.slow_rate = slow_rate
        self.slow_ms = slow_ms
        self.outages = outages or {}
        import random as _random
        self._slow_rng = _random.Random(slow_seed)

    def _down(self, model: str) -> bool:
        now = self.clock.now()
        return any(k in (model or "") and any(a <= now < b for a, b in wins) for k, wins in self.outages.items())

    def _create(self, *, timeout: float | None = None, **kw):
        timeout = timeout if timeout is not None else self.default_timeout
        model = kw.get("model")
        if model and self._down(model):
            self.clock.advance_ms(40)
            self._record(model, len(self.calls), 0, 0, 0, 0, 40, "overloaded")
            raise OverloadedError("overloaded_error: the API is temporarily overloaded")
        start = self.clock.now_ms
        slow = self.slow_rate and self._slow_rng.random() < self.slow_rate
        try:
            msg = super()._create(**kw)
        except RateLimitError as e:
            # aikit rounds retry_after to 3 decimals, which can give 0.0 while the window is
            # still full, so a client that sleeps exactly retry_after would spin forever.
            # Recompute it, rounded up, with 1 ms to spare.
            if self.rpm_limit:
                now = self.clock.now()
                recent = [c["t"] for c in self.calls if now - c["t"] < 60 and not c["error"]]
                if recent:
                    wait = 60 - (now - min(recent))
                    e.retry_after = math.ceil(wait * 1000) / 1000 + 0.001
            raise
        if slow:
            self.clock.advance_ms(self.slow_ms)
            msg.latency_ms = round(msg.latency_ms + self.slow_ms, 1)
            self.calls[-1]["latency_ms"] = msg.latency_ms
            self.calls[-1]["t"] = self.clock.now()
        if timeout is not None and msg.latency_ms > timeout * 1000:
            self.clock.now_ms = start + timeout * 1000
            rec = self.calls[-1]
            u = {"input_tokens": rec["input_tokens"] + rec["cache_read_input_tokens"] + rec["cache_creation_input_tokens"]}
            rec.update(error="timeout", latency_ms=round(timeout * 1000, 1), output_tokens=0, t=self.clock.now(),
                       cost=aikit.cost(u, model, self.prices))
            raise APITimeoutError(f"request timed out after {timeout:g} s")
        return msg


# ====================================================================== traces

def traces():
    """ORBIT's production traces (aikit.helios.traces()), one row per span, with two fixes:

    - the 429 burst on day 11 is present (in aikit's data it was generated for the
      wrong trace numbers): llm spans of day-11 requests between 09:00 and 17:00 fail
      with rate_limit (most of them);
    - llm spans have a `ttft_ms` column (time to first token); other spans have NaN.
    """
    import pandas as pd

    t = helios.traces()
    rng = np.random.default_rng(11)
    hour = t["timestamp"].dt.hour
    burst_traces = sorted(t.loc[(t["day"] == 11) & hour.between(9, 16), "trace_id"].unique())
    failing = {tid for tid in burst_traces if rng.random() < 0.85}
    is_llm = t["span"] == "llm"
    hit = t["trace_id"].isin(failing)
    t.loc[hit & is_llm, ["error", "duration_ms", "output_tokens"]] = ["rate_limit", 150.0, 0]
    t = t[~(hit & t["span"].str.startswith("tool:"))].reset_index(drop=True)
    # ttft: the llm span is about ttft + output_tokens * ms_per_token
    per_tok = np.where(t["model"].str.contains("haiku"), 12, 28)
    ttft = (t["duration_ms"] - t["output_tokens"] * per_tok).clip(lower=150).round(1)
    t["ttft_ms"] = np.where((t["span"] == "llm") & t["error"].isna(), ttft, np.nan)
    t["error"] = t["error"].where(t["error"].notna(), None)
    return t


# ====================================================================== request log with feedback

_TOPIC_QUESTIONS = {}
for _it in EVAL:
    _TOPIC_QUESTIONS.setdefault(_it["topic"], []).append(_it["question"])
_TOPIC_QUESTIONS.setdefault("it", []).extend(["How do I reset my tablet password?", "Why is the lab printer offline?"])
_TOPIC_QUESTIONS["laboratory"] = _TOPIC_QUESTIONS.get("laboratory", []) + [
    "Which lab bench has the glovebox?", "Can I book the centrifuge for Saturday?"]

CAMPAIGN_QUESTIONS = [
    "How do I log a run of the CRYSTAL-2 protein experiment?",
    "Which bench is reserved for the CRYSTAL-2 campaign?",
    "What temperature should the CRYSTAL-2 growth cells be kept at?",
    "Who signs off CRYSTAL-2 sample transfers to the freezer?",
    "How often do we photograph the CRYSTAL-2 crystal trays?",
    "Can I pause a CRYSTAL-2 run during a comms blackout?",
]


def requests_log():
    """One row per ORBIT request (300, matching traces()): trace_id, day, topic, model,
    question, error, thumbs ("up", "down" or None), rephrased (the user asked again
    within a minute).

    From day 8 a new crew rotation starts the CRYSTAL-2 experiment campaign. Many lab
    questions are about it, the handbook has nothing on it, and the crew is unhappy.
    """
    import pandas as pd

    t = traces()
    llm = t[t["span"] == "llm"].reset_index(drop=True)
    rng = np.random.default_rng(8)
    rows = []
    for _, r in llm.iterrows():
        topic = r["topic"]
        campaign = topic == "laboratory" and r["day"] >= 8 and rng.random() < 0.65
        pool = _TOPIC_QUESTIONS.get(topic) or _TOPIC_QUESTIONS["crew"]
        q = CAMPAIGN_QUESTIONS[int(rng.integers(len(CAMPAIGN_QUESTIONS)))] if campaign else pool[int(rng.integers(len(pool)))]
        err = r["error"] if isinstance(r["error"], str) else None
        p_down = 0.55 if campaign else (0.30 if err else 0.06)
        p_up = 0.05 if campaign else 0.35
        u = rng.random()
        thumbs = "down" if u < p_down else ("up" if u < p_down + p_up else None)
        rephrased = bool(rng.random() < (0.45 if campaign else (0.7 if err else 0.08)))
        rows.append({"trace_id": r["trace_id"], "day": int(r["day"]), "topic": topic, "model": r["model"],
                     "question": q, "error": err, "thumbs": thumbs, "rephrased": rephrased})
    return pd.DataFrame(rows)


# ====================================================================== prompt versions

PROMPT_HISTORY = [
    {"name": "orbit-answer", "version": "v1", "model": MODEL, "max_tokens": 600, "temperature": 0.2,
     "rules": RULES, "note": "first release"},
    {"name": "orbit-answer", "version": "v2", "model": MODEL, "max_tokens": 600, "temperature": 0.2,
     "rules": RULES + " Use the crew member's name when you know it.", "note": "friendlier tone"},
    {"name": "orbit-answer", "version": "v3", "model": MODEL, "max_tokens": 120, "temperature": 0.2,
     "rules": RULES + " Use the crew member's name when you know it.", "note": "cut output cost"},
    {"name": "orbit-answer", "version": "v4", "model": MODEL, "max_tokens": 120, "temperature": 0.2,
     "rules": RULES + " Use the crew member's name when you know it. Mention the handbook section you used.",
     "note": "cite the handbook section"},
]
_RELEASE_DAYS = {"v1": (1, 3), "v2": (4, 6), "v3": (7, 9), "v4": (10, 12)}


def release_log():
    """ORBIT's production log over 12 days, one row per request: request_id, day,
    prompt_version, question_id, stop_reason, output_tokens, cost, thumbs.
    Generated by actually running each prompt version on the crew's questions."""
    import pandas as pd

    rng = np.random.default_rng(5)
    client = make_client(seed=5)
    by_v = {p["version"]: p for p in PROMPT_HISTORY}
    rows = []
    n = 0
    for v, (d0, d1) in _RELEASE_DAYS.items():
        p = by_v[v]
        system = p["rules"] + "\n\n" + HANDBOOK_BLOCK
        for day in range(d0, d1 + 1):
            for _ in range(25):
                it = EVAL[int(rng.integers(len(EVAL)))]
                r = client.messages.create(model=p["model"], max_tokens=p["max_tokens"], system=system,
                                           messages=[{"role": "user", "content": it["question"]}])
                ok = grade(it, r.text)
                u = rng.random()
                thumbs = ("down" if u < 0.05 else ("up" if u < 0.45 else None)) if ok else \
                         ("down" if u < 0.5 else ("up" if u < 0.55 else None))
                n += 1
                rows.append({"request_id": f"req-{n:04d}", "day": day, "prompt_version": v, "question_id": it["id"],
                             "stop_reason": r.stop_reason, "output_tokens": r.usage.output_tokens,
                             "cost": client.calls[-1]["cost"], "thumbs": thumbs})
    return pd.DataFrame(rows)


def config_hash(config: dict) -> str:
    """Reference content hash of a prompt config (first 8 hex chars of sha256 of sorted JSON)."""
    return hashlib.sha256(json.dumps(config, sort_keys=True).encode()).hexdigest()[:8]


# ====================================================================== structured app logs

def app_logs(n_requests: int = 150) -> list[str]:
    """ORBIT's application log for one afternoon: JSON lines, interleaved across requests.

    Events per request: request -> retrieve -> llm_call (status ok or error, with
    error_type) -> [retry -> llm_call ...] -> response (status ok, degraded or error).
    Retryable errors (rate_limit, overloaded, timeout) are retried up to 2 times;
    bad_request is not. Request req-0137 is the one Lucía complained about.
    """
    import random as _random
    from datetime import datetime, timedelta

    rng = _random.Random(137)
    t0 = datetime(2026, 9, 11, 13, 0, 0)
    events = []
    for i in range(1, n_requests + 1):
        rid = f"req-{i:04d}"
        t = t0 + timedelta(seconds=i * 7 + rng.uniform(0, 5))
        user = rng.choice(["u_8c1f0a2b9e", "u_51d3c7e0aa", "u_e09b44f1c2", "u_7a2e9d03b5", "u_c4f1186e7d", "u_3b90a5d2f8"])
        ev = [("info", "request", {"user": user, "prompt_version": "orbit-answer@v2"})]
        ev.append(("info", "retrieve", {"docs": rng.randint(3, 6), "latency_ms": round(rng.uniform(80, 170), 1)}))
        if rid == "req-0137":
            plan = ["rate_limit", "rate_limit", "rate_limit"]
        else:
            plan = []
            for _ in range(3):
                u = rng.random()
                kind = ("rate_limit" if u < 0.08 else "overloaded" if u < 0.11 else "timeout" if u < 0.13
                        else "bad_request" if u < 0.14 else None)
                plan.append(kind)
                if kind in (None, "bad_request"):
                    break
        status = "ok"
        for attempt, kind in enumerate(plan):
            if kind is None:
                ev.append(("info", "llm_call", {"attempt": attempt + 1, "status": "ok", "model": MODEL,
                                                "input_tokens": rng.randint(3900, 4100), "output_tokens": rng.randint(30, 400),
                                                "latency_ms": round(rng.uniform(800, 6000), 1)}))
                status = "ok"
                break
            ev.append(("warning" if kind != "bad_request" else "error", "llm_call",
                       {"attempt": attempt + 1, "status": "error", "model": MODEL, "error_type": kind,
                        "latency_ms": 30000.0 if kind == "timeout" else round(rng.uniform(20, 60), 1)}))
            if kind == "bad_request":
                status = "error"
                break
            if attempt < len(plan) - 1:
                ev.append(("info", "retry", {"attempt": attempt + 2, "sleep_s": round(0.5 * 2 ** attempt, 2)}))
            else:
                ev.append(("error", "gave_up", {"attempts": attempt + 1}))
                status = "degraded"
        ev.append(("info", "response", {"status": status}))
        for level, name, fields in ev:
            t += timedelta(milliseconds=fields.get("latency_ms", 0) if name != "retry" else fields["sleep_s"] * 1000)
            t += timedelta(milliseconds=rng.uniform(1, 20))
            events.append((t, {"ts": t.isoformat(timespec="milliseconds") + "Z", "level": level, "event": name,
                               "request_id": rid, **fields}))
    events.sort(key=lambda e: e[0])
    return [json.dumps(e) for _, e in events]
