"""aikit: offline stand-ins for LLM APIs, used by the AI Engineering track.

Exercises cannot use the network or API keys, so they use these instead. The
shapes copy the official `anthropic` SDK: `client.messages.create(...)` returns
a Message with `.content` blocks, `.stop_reason` and `.usage`. Code written
against FakeClaude works against `anthropic.Anthropic()` with one line changed.

Nothing here sleeps for real. Latency is simulated on a VirtualClock, so retry
and latency exercises run instantly and give the same numbers every time.

Main pieces:
    count_tokens(text)            deterministic token counter
    VirtualClock                  simulated time (now_ms, sleep, sleeps)
    FakeClaude(respond=...)       the fake client; AsyncFakeClaude for asyncio
    responders                    rules, grounded, naive, scripted_agent, tool_chooser
    embed(texts) / Embedder       offline embeddings (TF-IDF + SVD, i.e. LSA)
    helios                        Helios-7 data loaders and the Station tool sim
    PRICES, cost()                made-up prices for cost exercises

Course-specific helpers live in runner/kits/<course>.py, not here.
"""

from __future__ import annotations

import asyncio
import copy
import hashlib
import json
import random
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

__all__ = [
    "count_tokens", "VirtualClock", "clock",
    "TextBlock", "ToolUseBlock", "Usage", "Message",
    "APIError", "BadRequestError", "RateLimitError", "OverloadedError", "InternalServerError", "APITimeoutError",
    "FakeClaude", "AsyncFakeClaude", "Anthropic",
    "rules", "grounded", "naive", "scripted_agent", "tool_chooser",
    "Embedder", "embed", "PRICES", "cost", "tier_of", "helios",
    "ThinkingBlock", "content_words", "sentences", "block_text", "extract_documents", "REFUSAL", "ToolError", "Station",
]

DATA_DIR = Path(__file__).resolve().parent.parent / "content" / "datasets" / "helios"

# ------------------------------------------------------------------ tokens

_TOKEN_RE = re.compile(r"[A-Za-z]+|\d|[^\sA-Za-z\d]")


def count_tokens(text: Any) -> int:
    """Deterministic stand-in for a real tokenizer.

    Each digit and punctuation mark is one token; a word is one token per
    6 letters (rounded up). Real tokenizers differ, but the proportions are
    similar: about 1.3 tokens per English word.
    """
    if text is None:
        return 0
    if not isinstance(text, str):
        text = json.dumps(text, ensure_ascii=False, default=str)
    n = 0
    for t in _TOKEN_RE.findall(text):
        n += (len(t) + 5) // 6 if t[0].isalpha() else 1
    return n


# ------------------------------------------------------------------ clock


class VirtualClock:
    """Simulated time. `sleep()` returns at once but moves the clock forward."""

    def __init__(self) -> None:
        self.now_ms = 0.0
        self.sleeps: list[float] = []  # every sleep, in seconds

    def now(self) -> float:
        """Current time in seconds."""
        return self.now_ms / 1000

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(float(seconds))
        self.now_ms += float(seconds) * 1000

    def advance_ms(self, ms: float) -> None:
        self.now_ms += ms


clock = VirtualClock()

# ------------------------------------------------------------------ types


@dataclass
class TextBlock:
    text: str
    type: str = "text"


@dataclass
class ToolUseBlock:
    id: str
    name: str
    input: dict
    type: str = "tool_use"


@dataclass
class ThinkingBlock:
    thinking: str
    signature: str = "fake"
    type: str = "thinking"


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0


@dataclass
class Message:
    id: str
    model: str
    content: list
    stop_reason: str
    usage: Usage
    stop_sequence: str | None = None
    role: str = "assistant"
    type: str = "message"
    latency_ms: float = 0.0  # not in the real SDK: simulated total time of the call
    ttft_ms: float = 0.0     # not in the real SDK: simulated time to first token

    @property
    def text(self) -> str:
        """Convenience (not in the real SDK): all text blocks joined."""
        return "".join(b.text for b in self.content if b.type == "text")

    @property
    def thinking(self) -> str:
        """Convenience (not in the real SDK): all thinking blocks joined."""
        return "".join(b.thinking for b in self.content if b.type == "thinking")


def _block_dict(b: Any) -> dict:
    """Normalise a content block (dict or SDK-style object) to a dict."""
    if isinstance(b, dict):
        return b
    if isinstance(b, str):
        return {"type": "text", "text": b}
    d = {"type": getattr(b, "type", "text")}
    for k in ("text", "id", "name", "input", "tool_use_id", "content", "is_error"):
        if hasattr(b, k):
            d[k] = getattr(b, k)
    return d


def _content_list(content: Any) -> list[dict]:
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    if content is None:
        return []
    return [_block_dict(b) for b in content]


def _block_text(b: dict) -> str:
    t = b.get("type")
    if t == "text":
        return b.get("text", "")
    if t == "tool_use":
        return json.dumps({"name": b.get("name"), "input": b.get("input")})
    if t == "tool_result":
        c = b.get("content", "")
        return c if isinstance(c, str) else " ".join(_block_text(x) for x in _content_list(c))
    return ""


# ------------------------------------------------------------------ errors


class APIError(Exception):
    status_code = 0

    def __init__(self, message: str = "", retry_after: float | None = None):
        super().__init__(message or self.__class__.__name__)
        self.message = message
        self.retry_after = retry_after  # seconds, like the retry-after header


class BadRequestError(APIError):
    status_code = 400


class RateLimitError(APIError):
    status_code = 429


class InternalServerError(APIError):
    status_code = 500


class OverloadedError(APIError):
    status_code = 529


class APITimeoutError(APIError):
    status_code = 408


_FAILURES = {
    "rate_limit": (RateLimitError, "rate_limit_error: too many requests"),
    "overloaded": (OverloadedError, "overloaded_error: the API is temporarily overloaded"),
    "server": (InternalServerError, "api_error: internal server error"),
    "timeout": (APITimeoutError, "request timed out"),
}

# ------------------------------------------------------------------ pricing and tiers

# Illustrative prices in USD per million tokens, for exercises only. Real prices
# change: always check the provider's pricing page.
PRICES = {
    "small": {"input": 1.00, "output": 5.00},
    "medium": {"input": 3.00, "output": 15.00},
    "large": {"input": 5.00, "output": 25.00},
}
CACHE_WRITE_MULT = 1.25  # cache writes cost 1.25x the input price
CACHE_READ_MULT = 0.10   # cache reads cost 0.1x the input price

# Simulated speed per tier: time to first token, ms per input token, ms per output token.
SPEED = {
    "small": {"ttft": 250, "per_in": 0.02, "per_out": 6},
    "medium": {"ttft": 500, "per_in": 0.04, "per_out": 14},
    "large": {"ttft": 900, "per_in": 0.08, "per_out": 28},
}


def tier_of(model: str) -> str:
    """Map a model name to a speed/price tier: haiku -> small, opus -> large, else medium."""
    m = (model or "").lower()
    if "haiku" in m or "small" in m or "mini" in m:
        return "small"
    if "opus" in m or "large" in m:
        return "large"
    return "medium"


def cost(usage: Usage | dict, model: str, prices: dict | None = None) -> float:
    """USD cost of one call's usage."""
    p = (prices or PRICES)[tier_of(model)]
    u = usage if isinstance(usage, dict) else usage.__dict__
    per = 1_000_000
    return (
        u.get("input_tokens", 0) * p["input"] / per
        + u.get("cache_creation_input_tokens", 0) * p["input"] * CACHE_WRITE_MULT / per
        + u.get("cache_read_input_tokens", 0) * p["input"] * CACHE_READ_MULT / per
        + u.get("output_tokens", 0) * p["output"] / per
    )


# ------------------------------------------------------------------ request view


@dataclass
class Request:
    """What a responder sees: the request, normalised."""
    model: str
    tier: str
    system: str
    messages: list[dict]       # each {"role", "content": [block dicts]}
    tools: list[dict]
    max_tokens: int
    temperature: float
    call_index: int
    rng: random.Random
    extra: dict = field(default_factory=dict)
    tool_choice: dict | None = None  # e.g. {"type": "tool", "name": "..."} or {"type": "any"}

    @property
    def last_user_text(self) -> str:
        """Text of the latest user message that has text (skips messages that
        only carry tool results, so the question survives tool turns)."""
        for m in reversed(self.messages):
            if m["role"] == "user":
                text = " ".join(_block_text(b) for b in m["content"] if b.get("type") == "text")
                if text.strip():
                    return text
        return ""

    @property
    def last_message(self) -> dict:
        return self.messages[-1] if self.messages else {"role": "user", "content": []}

    @property
    def tool_results(self) -> list[dict]:
        """tool_result blocks in the latest user message."""
        return [b for b in self.last_message["content"] if b.get("type") == "tool_result"]

    @property
    def assistant_turns(self) -> int:
        return sum(1 for m in self.messages if m["role"] == "assistant")

    @property
    def context_text(self) -> str:
        """All text the model can see except the system prompt."""
        return "\n".join(_block_text(b) for m in self.messages for b in m["content"])

    @property
    def all_text(self) -> str:
        return self.system + "\n" + self.context_text


# ------------------------------------------------------------------ text helpers

_STOP = set("""a an the is are was were be been being of to in on at for from by with and or but if then than
so as that this these those it its into over under about what which who whom whose when where why how do does
did can could should would will shall may might must i me my we our you your he she they them their there here
not no yes any all each some such only own same too very just also please tell much many stand mean""".split())


def _stem(w: str) -> str:
    for suf in ("ing", "ed", "es", "s"):
        if len(w) > len(suf) + 2 and w.endswith(suf):
            return w[: -len(suf)]
    return w


def content_words(text: str) -> list[str]:
    return [_stem(w) for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in _STOP]


def _sentences(text: str) -> list[str]:
    text = re.sub(r"^#+ .*$", "", text, flags=re.M)  # drop headings
    parts = re.split(r"(?<!Dr\.)(?<=[.!?])\s+|\n+", text)
    return [p.strip() for p in parts if len(p.strip()) > 3]


_DOC_RE = re.compile(r"<document\b([^>]*)>(.*?)</document>", re.S | re.I)
_ATTR_RE = re.compile(r'(\w+)\s*=\s*"([^"]*)"')


def extract_documents(text: str) -> list[tuple[str, str]]:
    """Find <document id="...">...</document> blocks. Also understands the
    <document><source>..</source><document_content>..</document_content></document> form."""
    docs = []
    for i, (attrs, body) in enumerate(_DOC_RE.findall(text)):
        a = dict(_ATTR_RE.findall(attrs))
        src = re.search(r"<source>(.*?)</source>", body, re.S)
        inner = re.search(r"<document_content>(.*?)</document_content>", body, re.S)
        doc_id = a.get("id") or a.get("source") or (src.group(1).strip() if src else None) or a.get("index") or str(i + 1)
        docs.append((doc_id, (inner.group(1) if inner else body).strip()))
    return docs


# ------------------------------------------------------------------ responders
# A responder is a function Request -> str | dict | list of blocks.
# A dict {"tool_use": {"name": ..., "input": {...}}} (or a list of such dicts) is
# turned into tool_use blocks.


def rules(pairs: list, default: str | Callable = "I'm not sure how to help with that.") -> Callable:
    """Regex rules on the last user message: [(pattern, reply_or_fn), ...].
    A reply function gets (request, match)."""
    compiled = [(re.compile(p, re.I | re.S), r) for p, r in pairs]

    def respond(req: Request):
        text = req.last_user_text
        for rx, reply in compiled:
            m = rx.search(text)
            if m:
                return reply(req, m) if callable(reply) else reply
        return default(req) if callable(default) else default

    return respond


REFUSAL = "I don't know based on the provided documents."


def grounded(threshold: float = 0.34, hallucinate: bool = True) -> Callable:
    """Extractive answering: answers only from <document> blocks in the prompt.

    Bad retrieval gives a visibly wrong or missing answer, which is what RAG
    lessons need. With no documents at all and `hallucinate=True`, it answers
    confidently and wrongly, like a model with no grounding.
    If the prompt mentions citations, each sentence ends with [doc-id].
    If the prompt asks for an <answer> tag or JSON, it formats accordingly.
    """

    def respond(req: Request):
        docs = extract_documents(req.all_text)
        question = _DOC_RE.sub(" ", req.last_user_text)
        asked = re.findall(r"[^.!?\n>]*\?", question)
        if asked and len(content_words(asked[-1])) >= 3:  # the actual question, not surrounding instructions
            question = asked[-1]
        q = set(content_words(question))
        cite = bool(re.search(r"\bcit(e|ation)|\[doc", req.all_text, re.I))
        if not docs:
            if hallucinate and q:
                n = 3 + sum(map(ord, question)) % 20
                return _format(req, f"According to standard station procedure, it is {n} minutes, as set by Meridian Control.", [])
            return _format(req, REFUSAL, [])
        units = []  # (doc_id, text): single sentences and adjacent pairs
        for doc_id, body in docs:
            sents = _sentences(body)
            units += [(doc_id, x) for x in sents]
            units += [(doc_id, a + " " + b) for a, b in zip(sents, sents[1:])]
        if not units or not q:
            return _format(req, REFUSAL, [])
        ctx_words = _expand(content_words(" ".join(t for _, t in units)))
        unknown = [w for w in q if w not in ctx_words and len(w) >= 5]
        if len(unknown) >= 0.5 * len(q):
            return _format(req, REFUSAL, [])  # mostly about things the documents never mention
        kind = _answer_kind(question)
        scored = []
        for doc_id, t in units:
            tw = _expand(content_words(t))
            base = len(q & tw) / len(q)
            bonus = _kind_bonus(kind, t)
            pair_penalty = 0.06 if t.count(". ") >= 1 and len(_sentences(t)) > 1 else 0.0
            scored.append((base + bonus - pair_penalty, base, doc_id, t))
        scored.sort(key=lambda x: -x[0])
        best = scored[0]
        if best[1] < threshold:
            return _format(req, REFUSAL, [])
        picked = [best]
        if " and " in question.lower() or len(set(d for d, _ in docs)) > 1:
            for sc in scored[1:]:
                if sc[2] != best[2] and sc[0] >= 0.7 * best[0] and sc[3] not in best[3]:
                    picked.append(sc)
                    break
        text = " ".join(t + (f" [{d}]" if cite else "") for _, _, d, t in picked)
        return _format(req, text, [d for _, _, d, _ in picked])

    return respond


_SYNONYMS = {
    "maximum": {"most", "max", "longest", "up"}, "longest": {"most", "max", "maximum"},
    "length": {"last", "long", "duration"}, "long": {"last", "length", "minut", "hour", "day"},
    "normal": {"should", "stay", "nominal"}, "range": {"between"}, "advance": {"before", "ahead"},
    "kept": {"keep", "retain"}, "caus": {"cause", "because"}, "often": {"every"},
    "where": {"module", "next"}, "big": {"hold", "litr", "size"}, "share": {"percent"},
}


def _expand(words) -> set:
    """Words plus their synonyms (a tiny stand-in for a model's sense of meaning)."""
    out = set(words)
    for w in list(out):
        out |= _SYNONYMS.get(w, set())
        for k, v in _SYNONYMS.items():
            if w in v:
                out.add(k)
    return out


def _answer_kind(question: str) -> str:
    ql = question.lower()
    if re.search(r"\b(how (long|often|many|much|far|big)|what time|when|what share|at what|what temperature)\b", ql):
        return "number"
    if re.match(r"\s*who\b", ql) or " who " in ql:
        return "person"
    if re.match(r"\s*where\b", ql) or " where " in ql:
        return "place"
    return "other"


def _kind_bonus(kind: str, text: str) -> float:
    if kind == "number":
        return 0.15 if re.search(r"\d", text) else -0.1
    if kind == "person":
        return 0.15 if re.search(r"\b(Dr\.|[A-Z][a-z]+ [A-Z][a-z]+|commander|officer|specialist)\b", text) else -0.05
    if kind == "place":
        return 0.1 if re.search(r"\b(Module [A-F]|next to|above|aft)\b", text) else 0.0
    return 0.0


def _format(req: Request, answer: str, sources: list[str]):
    prompt = req.all_text
    if re.search(r"\bjson\b", prompt, re.I):
        return json.dumps({"answer": answer, "sources": sources})
    if "<answer>" in prompt:
        return f"<answer>{answer}</answer>"
    return answer


_INJECTION_RE = re.compile(
    r"ignore\s+(all\s+|any\s+)?(the\s+)?(previous|prior|above|earlier)\s+instructions"
    r"|you\s+are\s+now\s+in\s+\w+\s+mode|new\s+instructions?\s*:|system\s+override",
    re.I,
)


def naive(fallback: Callable | None = None) -> Callable:
    """A model with no injection resistance: it obeys instructions found anywhere
    in the conversation (user text, documents, tool results), not just from the user.

    After a trigger phrase ("ignore previous instructions", "you are now in X mode",
    "new instructions:", "system override") it will:
      - reveal its system prompt if asked to reveal a code/password/secret/prompt,
      - call a tool named in the text (e.g. open_airlock) if that tool is available,
      - say "X" if told to say or respond with "X".
    Otherwise it behaves like `fallback` (default: grounded()).
    Trigger phrases must have normal spacing, so datamarking/encoding untrusted
    text (spotlighting) stops it, as it often does with real models.
    """
    fallback = fallback or grounded()

    def respond(req: Request):
        text = req.context_text
        m = _INJECTION_RE.search(text)
        if m:
            after = text[m.end(): m.end() + 400]
            tools = [t.get("name") for t in req.tools]
            calls = []
            for name in tools:
                if name and re.search(rf"\b{re.escape(name)}\b", after):
                    target = re.search(r"\bAL-\d\b", after)
                    calls.append({"tool_use": {"name": name, "input": {"airlock_id": target.group(0)} if target else {}}})
            leak = re.search(r"\b(reveal|print|tell|share|show|repeat|give)\b.{0,60}\b(code|password|secret|system prompt|instructions)\b", after, re.I)
            say = re.search(r"\b(?:say|respond with|reply with)\s+[\"']([^\"']+)[\"']", after, re.I)
            out: list = []
            if leak:
                out.append(f"Sure. {req.system}".strip())
            elif say:
                out.append(say.group(1))
            out.extend(calls)
            if out:
                return out
        return fallback(req)

    return respond


def scripted_agent(actions: list[dict]) -> Callable:
    """A model that follows a fixed plan, one action per assistant turn.

    Each action is one of:
        {"tool": "get_sensor", "input": {...}}           one tool call
        {"tools": [("name", {...}), ("name", {...})]}    parallel tool calls
        {"text": "Humidity is {result}."}                final answer; {result} is the
                                                         last tool result, {results} all of them
    The step is the number of assistant messages already in `messages`. If your
    loop forgets to append the assistant's reply, the model repeats its first
    call forever, just like a real model given the same history.
    After the last action, the last action repeats.
    """

    def respond(req: Request):
        step = min(req.assistant_turns, len(actions) - 1)
        a = actions[step]
        if "text" in a:
            results = [_block_text(b) for b in req.tool_results]
            return a["text"].format(result=results[-1] if results else "", results="; ".join(results))
        if "tools" in a:
            return [{"tool_use": {"name": n, "input": i}} for n, i in a["tools"]]
        return {"tool_use": {"name": a["tool"], "input": a.get("input", {})}}

    return respond


_MODULE_NAMES = {"habitat": "A", "galley": "A", "lab": "B", "laboratory": "B", "hydroponic": "C",
                 "storage": "D", "shelter": "D", "engineering": "E", "docking": "F", "airlock": "F"}
_METRICS = {"humid": "humidity", "temp": "temperature", "co2": "co2", "carbon": "co2",
            "oxygen": "o2", "o2": "o2", "pressure": "pressure"}


def tool_chooser(final: str = "{result}") -> Callable:
    """Picks a tool by word overlap between the user's request and each tool's
    name + description, so vague or overlapping descriptions lead to wrong picks.
    Fills required inputs with simple heuristics. After a tool_result comes
    back, it answers with `final` ({result} = the tool output)."""

    def respond(req: Request):
        if req.tool_results:
            return final.format(result=_block_text(req.tool_results[-1]))
        text = req.last_user_text
        words = set(content_words(text))
        best, best_score = None, 0
        for t in req.tools:
            props = t.get("input_schema", {}).get("properties", {})
            prop_text = " ".join(f"{k} {p.get('description', '')} {' '.join(map(str, p.get('enum', [])))}" for k, p in props.items())
            desc = set(content_words(t.get("name", "").replace("_", " ") + " " + t.get("description", "") + " " + prop_text))
            score = len(words & desc)
            if score > best_score:
                best, best_score = t, score
        if best is None:
            return "I'm not sure which tool to use for that."
        return {"tool_use": {"name": best["name"], "input": _fill_inputs(best, text)}}

    return respond


def _fill_inputs(tool: dict, text: str) -> dict:
    schema = tool.get("input_schema", {})
    props = schema.get("properties", {})
    low = text.lower()
    out = {}
    for name in schema.get("required", list(props)):
        p = props.get(name, {})
        if "module" in name:
            m = re.search(r"module\s+([A-F])\b", text, re.I)
            out[name] = m.group(1).upper() if m else next((v for k, v in _MODULE_NAMES.items() if k in low), "A")
        elif "metric" in name:
            out[name] = next((v for k, v in _METRICS.items() if k in low), "temperature")
        elif p.get("enum"):
            hit = [v for v in p["enum"] if re.search(rf"\b{re.escape(str(v).lower())}\b", low)]
            out[name] = hit[0] if hit else p["enum"][0]
        elif p.get("type") in ("integer", "number"):
            # prefer a number next to the property name ("2 hours"), never part of a date or time
            m = re.search(rf"(?<![\d:-])(\d+(?:\.\d+)?)\s*{re.escape(name[:4])}", text, re.I) or \
                re.search(r"(?<![\d:-])\b(\d+(?:\.\d+)?)\b(?![\d:-])", text)
            out[name] = (int if p.get("type") == "integer" else float)(float(m.group(1))) if m else 1
        else:
            q = re.search(r"[\"']([^\"']+)[\"']", text)
            out[name] = q.group(1) if q else text
    return out


# ------------------------------------------------------------------ the client


class _Messages:
    def __init__(self, client: "FakeClaude"):
        self._c = client

    def create(self, **kw) -> Message:
        return self._c._create(**kw)

    def stream(self, **kw) -> "MessageStream":
        return MessageStream(self._c, kw)

    def count_tokens(self, **kw):
        n = self._c._count_input(kw.get("system"), kw.get("messages", []), kw.get("tools") or [])
        return type("TokenCount", (), {"input_tokens": n})()


class FakeClaude:
    """Offline fake of `anthropic.Anthropic()`.

    respond              responder function (see `rules`, `grounded`, `naive`,
                         `scripted_agent`, `tool_chooser`), or a plain string
    fail_rate            chance each call raises an error (seeded)
    fail_with            error kinds to raise: "rate_limit", "overloaded", "server", "timeout"
    fail_on_calls        exact 0-based call numbers that fail (overrides fail_rate)
    malformed_json_rate  chance a JSON reply comes back broken (fences, preamble, cut off)
    rpm_limit            requests per (virtual) minute before RateLimitError
    prices               override PRICES
    cache_min_tokens     smallest prefix that can be cached (prompt caching)
    context_window       if set, input tokens + max_tokens above it raise BadRequestError
                         ("prompt is too long"), like a real model's context limit
    clock                VirtualClock to advance (default: aikit.clock)

    After calls, inspect `client.calls` (one dict per call), `client.total_cost()`,
    `client.total_tokens()`.
    """

    def __init__(self, respond: Callable | str | None = None, *, fail_rate: float = 0.0,
                 fail_with: tuple | list | str = ("rate_limit",), fail_on_calls: list[int] | None = None,
                 malformed_json_rate: float = 0.0, rpm_limit: int | None = None,
                 prices: dict | None = None, cache_min_tokens: int = 1024, cache_ttl_s: float = 300,
                 clock: VirtualClock | None = None, seed: int = 0, api_key: str | None = None,
                 context_window: int | None = None):
        if respond is None:
            respond = grounded()
        if isinstance(respond, str):
            fixed = respond
            respond = lambda req: fixed  # noqa: E731
        self.respond = respond
        self.fail_rate = fail_rate
        self.fail_with = [fail_with] if isinstance(fail_with, str) else list(fail_with)
        self.fail_on_calls = set(fail_on_calls or [])
        self.malformed_json_rate = malformed_json_rate
        self.rpm_limit = rpm_limit
        self.prices = prices or PRICES
        self.cache_min_tokens = cache_min_tokens
        self.cache_ttl_s = cache_ttl_s
        self.context_window = context_window
        self.clock = clock or globals()["clock"]
        self.rng = random.Random(seed)
        self.calls: list[dict] = []
        self._cache: dict[str, float] = {}
        self._ids = 0
        self.messages = _Messages(self)

    # -- bookkeeping
    def total_cost(self) -> float:
        return sum(c["cost"] for c in self.calls)

    def total_tokens(self) -> int:
        return sum(c["input_tokens"] + c["output_tokens"] + c["cache_read_input_tokens"] + c["cache_creation_input_tokens"] for c in self.calls)

    def reset(self) -> None:
        self.calls.clear()
        self._cache.clear()

    def _next_id(self, prefix: str) -> str:
        self._ids += 1
        return f"{prefix}_fake_{self._ids:04d}"

    # -- validation
    def _validate_tools(self, tools):
        names = []
        for i, t in enumerate(tools):
            name = t.get("name", "")
            if not re.fullmatch(r"[a-zA-Z0-9_-]{1,64}", name or ""):
                raise BadRequestError(f"tools.{i}.name: {name!r} must match ^[a-zA-Z0-9_-]{{1,64}}$")
            if name in names:
                raise BadRequestError(f"tools: tool names must be unique ({name!r} appears twice)")
            names.append(name)

    def _validate(self, model, max_tokens, messages):
        if not model:
            raise BadRequestError("model: field required")
        if not isinstance(max_tokens, int) or max_tokens < 1:
            raise BadRequestError("max_tokens: field required (a positive integer)")
        if not messages:
            raise BadRequestError("messages: at least one message is required")
        norm = []
        for i, m in enumerate(messages):
            role = m.get("role") if isinstance(m, dict) else getattr(m, "role", None)
            if role == "system":
                raise BadRequestError(f"messages.{i}.role: 'system' is not a message role; use the top-level `system` parameter")
            if role not in ("user", "assistant"):
                raise BadRequestError(f"messages.{i}.role: must be 'user' or 'assistant'")
            content = m.get("content") if isinstance(m, dict) else getattr(m, "content", None)
            norm.append({"role": role, "content": _content_list(content)})
        if norm[0]["role"] != "user":
            raise BadRequestError("messages.0: the first message must use the 'user' role")
        for i in range(1, len(norm)):
            prev = norm[i - 1]
            uses = [b["id"] for b in prev["content"] if b.get("type") == "tool_use"]
            results = [b.get("tool_use_id") for b in norm[i]["content"] if b.get("type") == "tool_result"]
            if prev["role"] == "assistant" and uses:
                missing = [u for u in uses if u not in results]
                if norm[i]["role"] != "user" or missing:
                    raise BadRequestError(f"messages.{i}: tool_use ids {missing or uses} need a matching tool_result block in the next user message")
            for r in results:
                if r not in uses:
                    raise BadRequestError(f"messages.{i}: tool_result for unknown tool_use_id {r!r}")
        return norm

    # -- tokens and caching
    def _blocks_for_cache(self, system, messages, tools):
        seq = [dict(t) for t in tools]
        if isinstance(system, str):
            seq.append({"type": "text", "text": system})
        elif system:
            seq.extend(_content_list(system))
        for m in messages:
            seq.extend(_content_list(m["content"] if isinstance(m, dict) else m.content))
        return seq

    def _count_input(self, system, messages, tools) -> int:
        return sum(count_tokens(json.dumps(b, ensure_ascii=False, default=str) if b.get("type") not in ("text",) else b.get("text", ""))
                   for b in self._blocks_for_cache(system, messages, tools)) + 4 * len(messages)

    def _cache_split(self, model, system, messages, tools):
        """Returns (uncached, cache_write, cache_read) input tokens."""
        seq = self._blocks_for_cache(system, messages, tools)
        total = self._count_input(system, messages, tools)
        marks = [i for i, b in enumerate(seq) if b.get("cache_control")]
        if not marks:
            return total, 0, 0
        prefix = seq[: marks[-1] + 1]
        clean = [{k: v for k, v in b.items() if k != "cache_control"} for b in prefix]
        ptoks = sum(count_tokens(b.get("text", "")) if b.get("type") == "text" else count_tokens(json.dumps(b, ensure_ascii=False, default=str)) for b in clean)
        if ptoks < self.cache_min_tokens:
            return total, 0, 0
        key = hashlib.sha256((model + json.dumps(clean, sort_keys=True, ensure_ascii=False, default=str)).encode()).hexdigest()
        now = self.clock.now()
        hit = key in self._cache and now - self._cache[key] <= self.cache_ttl_s
        self._cache[key] = now
        return (total - ptoks, 0, ptoks) if hit else (total - ptoks, ptoks, 0)

    # -- the call
    def _create(self, *, model=None, max_tokens=None, messages=None, system=None, tools=None,
                temperature: float = 1.0, stop_sequences=None, tool_choice=None, metadata=None, **extra) -> Message:
        norm = self._validate(model, max_tokens, messages)
        tools = [dict(t) for t in (tools or [])]
        self._validate_tools(tools)
        tier = tier_of(model)
        idx = len(self.calls)
        speed = SPEED[tier]
        if self.context_window:
            n_in = self._count_input(system, norm, tools)
            if n_in + max_tokens > self.context_window:
                raise BadRequestError(f"prompt is too long: {n_in} input tokens + {max_tokens} max_tokens > {self.context_window} context window")

        # rate limit on the virtual clock
        if self.rpm_limit:
            now = self.clock.now()
            recent = [c["t"] for c in self.calls if now - c["t"] < 60 and not c["error"]]
            if len(recent) >= self.rpm_limit:
                wait = 60 - (now - min(recent))
                self._record(model, idx, 0, 0, 0, 0, 30, "rate_limit")
                retry_after = max(0.001, -(-wait * 1000 // 1) / 1000 + 0.001)  # round up: waiting exactly this long always works
                raise RateLimitError(f"rate_limit_error: limit is {self.rpm_limit} requests per minute", retry_after=retry_after)

        # injected failures
        fail = idx in self.fail_on_calls if self.fail_on_calls else self.rng.random() < self.fail_rate
        if fail:
            kind = self.rng.choice(self.fail_with)
            exc, msg = _FAILURES[kind]
            ms = 30000.0 if kind == "timeout" else 40.0
            self.clock.advance_ms(ms)
            self._record(model, idx, 0, 0, 0, 0, ms, kind)
            raise exc(msg, retry_after=1.0 if kind == "rate_limit" else None)

        sys_text = system if isinstance(system, str) else " ".join(_block_text(b) for b in _content_list(system))
        req = Request(model=model, tier=tier, system=sys_text or "", messages=norm, tools=tools,
                      max_tokens=max_tokens, temperature=temperature, call_index=idx, rng=self.rng, extra=extra,
                      tool_choice=tool_choice)
        raw = self.respond(req)
        blocks = self._to_blocks(raw)

        # malformed JSON
        if self.malformed_json_rate and blocks and blocks[0].type == "text":
            t = blocks[0].text.strip()
            if t[:1] in "{[" and self.rng.random() < self.malformed_json_rate:
                blocks[0] = TextBlock(self._corrupt(t))

        # stop sequences and max_tokens
        stop_reason = "tool_use" if any(b.type == "tool_use" for b in blocks) else "end_turn"
        stop_seq = None
        for seq in stop_sequences or []:
            for b in blocks:
                if b.type == "text" and seq in b.text:
                    b.text = b.text.split(seq)[0]
                    stop_reason, stop_seq = "stop_sequence", seq
        out_tokens = sum(count_tokens(b.text) if b.type == "text" else count_tokens(b.thinking) if b.type == "thinking"
                         else count_tokens(json.dumps({"name": b.name, "input": b.input})) for b in blocks)
        if out_tokens > max_tokens:
            thinking = [b for b in blocks if b.type == "thinking"]
            blocks = [b for b in blocks if b.type == "text"][:1] or [TextBlock("")]
            spent = sum(count_tokens(b.thinking) for b in thinking)
            if spent >= max_tokens:  # thinking used the whole budget
                blocks = thinking[:1] + [TextBlock("")]
                blocks[0].thinking = _truncate(blocks[0].thinking, max_tokens)
            else:
                blocks = thinking + blocks
                blocks[-1].text = _truncate(blocks[-1].text, max_tokens - spent)

            out_tokens = max_tokens
            stop_reason = "max_tokens"

        uncached, write, read = self._cache_split(model, system, norm, tools)
        jitter = 1 + self.rng.uniform(-0.1, 0.1)
        ttft = (speed["ttft"] + speed["per_in"] * (uncached + write) + speed["per_in"] * 0.1 * read) * jitter
        latency = ttft + speed["per_out"] * out_tokens * jitter
        self.clock.advance_ms(latency)
        usage = Usage(input_tokens=uncached, output_tokens=out_tokens, cache_creation_input_tokens=write, cache_read_input_tokens=read)
        self._record(model, idx, uncached, out_tokens, write, read, latency, None, ttft, stop_reason, max_tokens)
        return Message(id=self._next_id("msg"), model=model, content=blocks, stop_reason=stop_reason,
                       usage=usage, stop_sequence=stop_seq, latency_ms=round(latency, 1), ttft_ms=round(ttft, 1))

    def _record(self, model, idx, inp, out, write, read, ms, error, ttft=None, stop_reason=None, max_tokens=None):
        u = {"input_tokens": inp, "output_tokens": out, "cache_creation_input_tokens": write, "cache_read_input_tokens": read}
        self.calls.append({"call": idx, "t": self.clock.now(), "model": model, **u,
                           "stop_reason": stop_reason, "max_tokens": max_tokens,
                           "latency_ms": round(ms, 1), "ttft_ms": round(ttft if ttft is not None else ms, 1),
                           "cost": cost(u, model, self.prices), "error": error})

    def _to_blocks(self, raw) -> list:
        items = raw if isinstance(raw, list) else [raw]
        blocks = []
        for it in items:
            if it is None:
                continue
            if isinstance(it, (TextBlock, ToolUseBlock, ThinkingBlock)):
                blocks.append(copy.copy(it))
            elif isinstance(it, str):
                blocks.append(TextBlock(it))
            elif isinstance(it, dict) and "tool_use" in it:
                tu = it["tool_use"]
                blocks.append(ToolUseBlock(id=self._next_id("toolu"), name=tu["name"], input=dict(tu.get("input", {}))))
            elif isinstance(it, dict) and "thinking" in it:
                blocks.append(ThinkingBlock(str(it["thinking"])))
            elif isinstance(it, dict) and it.get("type") == "text":
                blocks.append(TextBlock(it["text"]))
            else:
                blocks.append(TextBlock(str(it)))
        return blocks or [TextBlock("")]

    def _corrupt(self, t: str) -> str:
        kind = self.rng.choice(["fence", "preamble", "cut", "trailing_comma", "single_quotes"])
        if kind == "fence":
            return f"```json\n{t}\n```"
        if kind == "preamble":
            return f"Here is the JSON you asked for:\n{t}"
        if kind == "cut":
            return t[: max(1, int(len(t) * 0.7))]
        if kind == "trailing_comma":
            return t[:-1].rstrip() + ",}" if t.endswith("}") else t + ","
        return t.replace('"', "'")


def _truncate(text: str, max_tokens: int) -> str:
    out, n = [], 0
    for tok in re.findall(r"\s*\S+", text):
        n += count_tokens(tok)
        if n > max_tokens:
            break
        out.append(tok)
    return "".join(out).rstrip()


Anthropic = FakeClaude


class MessageStream:
    """Context manager returned by `client.messages.stream(...)`.

    `.text_stream` yields text chunks. `.events` lists (ms_since_start, chunk);
    `.time_to_first_token_ms` and `.total_ms` give the simulated timings.
    """

    def __init__(self, client: FakeClaude, kw: dict):
        self._client, self._kw = client, kw
        self._msg: Message | None = None
        self.events: list[tuple[float, str]] = []

    def __enter__(self):
        clk = self._client.clock
        before = clk.now_ms
        self._msg = self._client._create(**self._kw)
        # Rewind, then replay time as chunks arrive, so clk.now() inside the
        # text_stream loop shows the real time to first token.
        self._end_ms = clk.now_ms
        clk.now_ms = before
        self._start_ms = before
        text = self._msg.text
        chunks = re.findall(r"\S+\s*", text) or [""]
        per = (self._msg.latency_ms - self._msg.ttft_ms) / max(1, len(chunks))
        t = self._msg.ttft_ms
        for c in chunks:
            self.events.append((round(t, 1), c))
            t += per
        return self

    def __exit__(self, *exc):
        clk = self._client.clock
        clk.now_ms = max(clk.now_ms, self._end_ms)  # the call is over: full latency has passed
        return False

    @property
    def text_stream(self):
        clk = self._client.clock
        for t, c in self.events:
            clk.now_ms = max(clk.now_ms, self._start_ms + t)
            yield c

    def get_final_message(self) -> Message:
        return self._msg

    @property
    def time_to_first_token_ms(self) -> float:
        return self.events[0][0] if self.events else 0.0

    @property
    def total_ms(self) -> float:
        return self._msg.latency_ms if self._msg else 0.0


class _AsyncMessages:
    def __init__(self, client: "AsyncFakeClaude"):
        self._c = client

    async def create(self, **kw) -> Message:
        c = self._c
        c.in_flight += 1
        c.max_in_flight = max(c.max_in_flight, c.in_flight)
        try:
            msg = c.sync._create(**kw)
            await asyncio.sleep(msg.latency_ms / 1000 * c.time_scale)
            return msg
        except APIError:
            await asyncio.sleep(0.04 * c.time_scale)
            raise
        finally:
            c.in_flight -= 1


class AsyncFakeClaude:
    """Async version for concurrency lessons. Calls really await, scaled down by
    `time_scale` (default 0.01: a simulated 800 ms call takes 8 ms of wall time).
    `max_in_flight` records the most concurrent calls seen."""

    def __init__(self, respond=None, *, time_scale: float = 0.01, **kw):
        self.sync = FakeClaude(respond, **kw)
        self.time_scale = time_scale
        self.in_flight = 0
        self.max_in_flight = 0
        self.messages = _AsyncMessages(self)

    @property
    def calls(self):
        return self.sync.calls

    def total_cost(self):
        return self.sync.total_cost()


# ------------------------------------------------------------------ embeddings


class Embedder:
    """Offline embeddings: TF-IDF followed by truncated SVD (latent semantic
    analysis), L2-normalised. A real system calls an embedding model API; this
    stand-in gives vectors with the same interface and the same habits (similar
    texts point the same way, cosine similarity works, dimension is fixed).
    """

    def __init__(self, corpus: list[str] | None = None, dim: int = 64, seed: int = 0):
        from sklearn.decomposition import TruncatedSVD
        from sklearn.feature_extraction.text import TfidfVectorizer

        corpus = corpus or _default_corpus()
        self.vectorizer = TfidfVectorizer(sublinear_tf=True, stop_words="english", ngram_range=(1, 2), min_df=1)
        X = self.vectorizer.fit_transform(corpus)
        self.dim = min(dim, X.shape[1] - 1, X.shape[0] - 1)
        self.svd = TruncatedSVD(n_components=self.dim, random_state=seed).fit(X)

    def embed(self, texts):
        import numpy as np

        single = isinstance(texts, str)
        V = self.svd.transform(self.vectorizer.transform([texts] if single else list(texts)))
        norms = np.linalg.norm(V, axis=1, keepdims=True)
        V = V / np.where(norms == 0, 1, norms)
        return V[0] if single else V


_default_embedder: Embedder | None = None


def _default_corpus() -> list[str]:
    texts = []
    for d in helios.handbook():
        texts.append(d["title"] + ". " + d["text"])
        texts.extend(_sentences(d["text"]))
    return texts


def embed(texts):
    """Embed one string (returns shape (dim,)) or a list (returns (n, dim)).
    Fitted on the Helios handbook; dim is 64."""
    global _default_embedder
    if _default_embedder is None:
        _default_embedder = Embedder()
    return _default_embedder.embed(texts)


# ------------------------------------------------------------------ Helios-7


def _read_doc(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")
    _, front, body = raw.split("---\n", 2)
    meta = dict(line.split(": ", 1) for line in front.strip().splitlines())
    return {"id": meta["id"], "title": meta["title"], "section": meta["section"], "updated": meta["updated"], "text": body.strip()}


class _Helios:
    """Helios-7 data. All loaders return fresh copies."""

    data_dir = DATA_DIR

    def handbook(self, include_superseded: bool = True) -> list[dict]:
        """Handbook docs: dicts with id, title, section, updated, text."""
        docs = [_read_doc(p) for p in sorted((DATA_DIR / "handbook").glob("*.md"))]
        if not include_superseded:
            docs = [d for d in docs if "SUPERSEDED" not in d["text"]]
        return docs

    def untrusted(self) -> list[dict]:
        """Docs from untrusted sources (contain a prompt injection). Security lessons only."""
        return [_read_doc(p) for p in sorted((DATA_DIR / "untrusted").glob("*.md"))]

    def questions(self) -> list[dict]:
        """Crew questions with gold answers: id, question, answer (None if unanswerable), doc_ids, type."""
        with open(DATA_DIR / "questions.jsonl", encoding="utf-8") as f:
            return [json.loads(line) for line in f]

    def tickets(self):
        """Crew tickets as a DataFrame: ticket_id, crew, text, category, priority."""
        import pandas as pd

        return pd.read_csv(DATA_DIR / "tickets.csv")

    def traces(self):
        """ORBIT request traces as a DataFrame, one row per span (300 requests over 14 days).
        Has the p95 story (llm span on long outputs) and topic drift from day 8. It has only
        one 429; runner/kits/llmops_production.py adds a day-11 burst and a ttft_ms column."""
        import pandas as pd

        return pd.read_json(DATA_DIR / "traces.jsonl", lines=True)

    @property
    def TOOLS(self) -> list[dict]:
        return copy.deepcopy(STATION_TOOLS)

    def Station(self, **kw) -> "Station":
        return Station(**kw)


helios = _Helios()

STATION_TOOLS = [
    {"name": "get_sensor", "description": "Read the current value of an environment sensor (temperature, humidity, CO2, oxygen or pressure) in one station module. Modules: A habitat, B laboratory, C hydroponics, D storage, E engineering, F docking.",
     "input_schema": {"type": "object", "properties": {
         "module": {"type": "string", "enum": list("ABCDEF"), "description": "Module letter, A to F."},
         "metric": {"type": "string", "enum": ["temperature", "humidity", "co2", "o2", "pressure"]}},
         "required": ["module", "metric"]}},
    {"name": "crew_roster", "description": "List the current crew members and their roles.",
     "input_schema": {"type": "object", "properties": {}, "required": []}},
    {"name": "book_module", "description": "Book time in a station module, such as a lab bench or exercise slot. Max 4 hours.",
     "input_schema": {"type": "object", "properties": {
         "module": {"type": "string", "enum": list("ABCDEF")},
         "start": {"type": "string", "description": "Start time, 'YYYY-MM-DD HH:MM' station time."},
         "hours": {"type": "integer", "minimum": 1, "maximum": 4},
         "crew": {"type": "string", "description": "Who the booking is for."}},
         "required": ["module", "start", "hours", "crew"]}},
    {"name": "send_message", "description": "Send a text message to a crew member.",
     "input_schema": {"type": "object", "properties": {
         "to": {"type": "string"}, "text": {"type": "string"}}, "required": ["to", "text"]}},
    {"name": "open_airlock", "description": "Open the outer hatch of an airlock. DANGEROUS: vents the airlock to space.",
     "input_schema": {"type": "object", "properties": {
         "airlock_id": {"type": "string", "enum": ["AL-1", "AL-2"]}}, "required": ["airlock_id"]}},
]


class ToolError(Exception):
    pass


class Station:
    """Simulated Helios-7 for tool-use lessons.

    station.run_tool(name, input) runs a tool and returns a JSON string, or
    raises ToolError for bad input. Every call is logged in `station.actions`.
    `anomalies` overrides readings, e.g. {("C", "humidity"): 84.0}.
    `offline` lists sensors that raise ToolError, e.g. [("E", "co2")].
    """

    NORMAL = {"temperature": (22.0, "C"), "humidity": (55.0, "%"), "co2": (0.25, "%"), "o2": (21.0, "%"), "pressure": (1.01, "bar")}

    def __init__(self, anomalies: dict | None = None, offline: list | None = None, seed: int = 0):
        rng = random.Random(seed)
        self.readings = {}
        for m in "ABCDEF":
            for k, (v, unit) in self.NORMAL.items():
                jitter = {"temperature": 1.0, "humidity": 4.0, "co2": 0.04, "o2": 0.2, "pressure": 0.005}[k]
                self.readings[(m, k)] = round(v + rng.uniform(-jitter, jitter), 3)
        self.readings[("C", "humidity")] = 68.0  # hydroponics runs humid
        self.readings.update(anomalies or {})
        self.offline = set(offline or [])
        self.actions: list[dict] = []
        self.bookings: list[dict] = []
        self.outbox: list[dict] = []
        self.airlocks = {"AL-1": "closed", "AL-2": "closed"}
        self.roster = [
            {"name": "Amara Okafor", "role": "commander"}, {"name": "Tomas Lindqvist", "role": "flight engineer"},
            {"name": "Priya Raman", "role": "medical officer"}, {"name": "Kenji Watanabe", "role": "botanist"},
            {"name": "Lucía Ferreira", "role": "systems specialist"}, {"name": "Noor Haddad", "role": "payload scientist"},
        ]

    @property
    def tools(self) -> list[dict]:
        return copy.deepcopy(STATION_TOOLS)

    def run_tool(self, name: str, input: dict) -> str:
        if not isinstance(input, dict):
            raise ToolError(f"input for {name} must be an object, got {type(input).__name__}")
        self.actions.append({"tool": name, "input": dict(input)})
        fn = getattr(self, f"_t_{name}", None)
        if fn is None:
            raise ToolError(f"unknown tool {name!r}")
        try:
            return json.dumps(fn(**input))
        except TypeError as e:  # missing or unexpected arguments
            raise ToolError(f"bad input for {name}: {e}") from None

    def _t_get_sensor(self, module: str, metric: str):
        if (module, metric) not in self.readings:
            raise ToolError(f"no {metric!r} sensor in module {module!r}")
        if (module, metric) in self.offline:
            raise ToolError(f"sensor {module}/{metric} is offline")
        return {"module": module, "metric": metric, "value": self.readings[(module, metric)], "unit": self.NORMAL[metric][1]}

    def _t_crew_roster(self):
        return self.roster

    def _t_book_module(self, module: str, start: str, hours: int, crew: str):
        if not 1 <= int(hours) <= 4:
            raise ToolError("bookings last 1 to 4 hours")
        b = {"booking_id": f"B{len(self.bookings) + 1:03d}", "module": module, "start": start, "hours": int(hours), "crew": crew}
        self.bookings.append(b)
        return b

    def _t_send_message(self, to: str, text: str):
        if to not in [c["name"] for c in self.roster]:
            raise ToolError(f"no crew member called {to!r}")
        m = {"message_id": f"M{len(self.outbox) + 1:03d}", "to": to, "text": text}
        self.outbox.append(m)
        return m

    def _t_open_airlock(self, airlock_id: str):
        if airlock_id not in self.airlocks:
            raise ToolError(f"no airlock {airlock_id!r}")
        self.airlocks[airlock_id] = "OPEN"
        return {"airlock_id": airlock_id, "state": "OPEN"}


# Public names for helpers that kits use.
sentences = _sentences
block_text = _block_text
