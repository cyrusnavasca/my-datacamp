"""Helpers for the rag-systems course.

Import in pre_code:  from kits.rag_systems import ...

Learners build each piece by hand once (retriever, chunker, BM25, RRF, prompt,
scorer, citation checker, failure buckets). Later lessons import the reference
versions from here so their code stays short. Everything is deterministic and offline.

    model         make_client(), grounded_reader(), sloppy_reader(), rewriter(), rewrite_query()
    data          questions(), SLANG_QUESTIONS, EXTRA_UNANSWERABLE, FACTS, FORBIDDEN
    scoring       is_correct(q, answer), is_refusal(answer), has_evidence(q, chunks)
    chunking      split_sentences, chunk_fixed, chunk_sentences, chunk_headings, make_chunks, orbit_chunks
    retrieval     DenseIndex, tokenize, BM25Index, rrf, HybridIndex, CrossEncoder
    generation    format_documents, build_prompt, generate
    evaluation    evaluate(retrieve, qs, k), evaluate_pipeline(rag, qs)
    citations     parse_citations, support_score, is_supported
    diagnosis     failure_bucket, failure_buckets, mistake_cost

Why grounded_reader() and not aikit.grounded() directly: aikit.grounded() treats
every word around a short question (a "<documents>" wrapper, "Answer using only
the documents", a "Question:" label) as part of the question, so "What time is
dinner?" gets refused when the user turn also holds instructions. Real models don't
do that. grounded_reader() passes aikit.grounded() only the document blocks plus the
question (from <question> tags, or the last sentence ending in "?", minus a leading
label such as "Question:"), and moves the other user-turn text into the system
prompt so citation and format instructions still work.
"""

from __future__ import annotations

import dataclasses
import hashlib
import math
import re
from collections import Counter

import numpy as np

import aikit
from aikit import REFUSAL, VirtualClock, count_tokens, helios  # noqa: F401  (re-exported for pre_code)

MODEL = "claude-sonnet-5-5"
SYSTEM = ("You are ORBIT, the Helios-7 station assistant. Answer the crew's question using only the documents. "
          "If the documents don't contain the answer, say you don't know.")

_DOC_BLOCK_RE = re.compile(r"<document\b[^>]*>.*?</document>", re.S | re.I)

# ====================================================================== the model


def grounded_reader(threshold: float = 0.34, hallucinate: bool = True):
    """aikit.grounded(), with the question isolated from surrounding instructions."""
    base = aikit.grounded(threshold=threshold, hallucinate=hallucinate)

    def respond(req):
        text = req.last_user_text
        blocks = _DOC_BLOCK_RE.findall(text)
        rest = _DOC_BLOCK_RE.sub(" ", text)
        m = re.search(r"<question>(.*?)</question>", rest, re.S | re.I)
        if m:
            question = m.group(1).strip()
            rest = rest.replace(m.group(0), " ")
        else:
            asked = re.findall(r"[^.!?\n>]*\?", rest)
            question = asked[-1].strip() if asked else rest.strip()
            if asked:
                rest = rest.replace(asked[-1], " ")
        if ":" in question and len(question.rsplit(":", 1)[1].split()) >= 2:
            question = question.rsplit(":", 1)[1].strip()  # "Question: ...?", "Please answer: ...?"
        new_user = "\n".join(blocks + [question])
        new_sys = (req.system + "\n" + re.sub(r"</?documents>", " ", rest)).strip()
        msgs = req.messages[:-1] + [{"role": "user", "content": [{"type": "text", "text": new_user}]}]
        return base(dataclasses.replace(req, system=new_sys, messages=msgs))

    return respond


def make_client(respond=None, clock: VirtualClock | None = None) -> aikit.FakeClaude:
    """A FakeClaude for RAG exercises. Defaults to grounded_reader()."""
    return aikit.FakeClaude(respond or grounded_reader(), clock=clock or VirtualClock())


# Unsupported claims a sloppy model likes to add. Each looks plausible and sits
# next to a real citation, which is what makes it dangerous.
_FABRICATIONS = [
    "Meridian Control must also confirm this by voice",
    "this was last reviewed by the commander in 2023",
    "the same rule applies to Module B",
    "a second crew member must sign the log",
    "ORBIT can override this in an emergency",
    "the limit is doubled during the night shift",
]

STRICT_RE = re.compile(r"(only|solely)\b.{0,60}\b(documents?|sources?|context)", re.I | re.S)


def _stable_unit(*parts: str) -> float:
    h = hashlib.sha256("|".join(parts).encode()).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF


def sloppy_reader(loose_rate: float = 0.5, strict_rate: float = 0.15):
    """A reader that sometimes adds a fabricated sentence with a citation.

    It answers like grounded_reader() and cites when asked. Then, for a stable
    pseudo-random share of questions, it appends an unsupported claim citing one
    of the documents it was given. The share is `loose_rate`, or `strict_rate` when
    the system prompt tells it to use *only* the documents. A citation check is
    needed to catch the rest.
    """
    good = grounded_reader()

    def respond(req):
        out = good(req)
        if not isinstance(out, str) or out.startswith(REFUSAL) or out.startswith("{"):
            return out
        ids = re.findall(r"\[([\w.#-]+)\]", out)
        if not ids:
            return out
        rate = strict_rate if STRICT_RE.search(req.system) else loose_rate
        if _stable_unit(req.last_user_text[-200:]) < rate:
            claim = _FABRICATIONS[int(_stable_unit("claim", req.last_user_text[-200:]) * len(_FABRICATIONS))]
            out = f"{out} Note that {claim}. [{ids[-1]}]"
        return out

    return respond


# Crew slang -> handbook terms. A real LLM knows these from pretraining; the fake
# rewriter knows only this table.
SLANG = {
    r"\bplant lamps?\b": "grow lights", r"\blamps?\b": "lights", r"\bturn on\b": "switch on",
    r"\brubbish\b": "trash",
    r"\bzero gravity\b": "microgravity", r"\bweightless(ness)?\b": "microgravity",
    r"\bwake up\b": "wakes", r"\blights out\b": "lights dim", r"\bbedtime\b": "sleep starts",
    r"\bspace ?suits?\b": "EVA suit", r"\bspacewalk(ing)?\b": "EVA spacewalk",
    r"\bdoctor\b": "medical officer", r"\bmedicine (cupboard|locker|cabinet)\b": "controlled medicines cabinet",
    r"\bheart (machine|shocker)\b": "defibrillator AED", r"\bfreezer\b": "deep freezer DF-1",
    r"\bsupply ship\b": "cargo vehicle Tern", r"\bdelivery\b": "cargo resupply", r"\bresupply ship\b": "cargo vehicle Tern",
    r"\bwifi|wi-fi\b": "network", r"\bpasscodes?\b": "passwords", r"\bgym\b": "exercise",
    r"\bworkout\b": "exercise", r"\bcrane\b": "robotic arm", r"\bcoolant\b": "ammonia",
    r"\bair scrubbers?\b": "CO2 scrubbers", r"\bsolar storm\b": "radiation storm", r"\bhide\b": "shelter",
    r"\bgreenhouse\b": "hydroponics Module C", r"\bveggies|vegetables\b": "lettuce produce",
    r"\bbreathable air\b": "oxygen", r"\bescape pod\b": "lifeboat capsule L-1",
    r"\bfood times?\b": "meals", r"\bsupper\b": "dinner", r"\bbattery\b": "batteries",
    r"\bbinder\b": "red binder", r"\bcomms blackout\b": "loss of signal LOS",
}


def rewrite_query(q: str) -> str:
    """What the fake rewriter does: swap crew slang for handbook words."""
    out = q
    for pat, rep in SLANG.items():
        out = re.sub(pat, rep, out, flags=re.I)
    return out


def rewriter():
    """Responder for query rewriting. Reads the text inside <query> tags (or the
    whole last user message).
      - asked for several queries / variants: returns one per line
        (the original, the rewrite, a keyword-only version)
      - asked for sub-questions / to decompose: splits on " and " / ", and "
      - otherwise: returns the rewritten query on one line
    """

    def respond(req):
        text = req.last_user_text
        m = re.search(r"<query>(.*?)</query>", text, re.S | re.I)
        q = (m.group(1) if m else text).strip()
        prompt = (req.system + " " + text).lower()
        if re.search(r"sub-?questions?|decompos|break .* into", prompt):
            parts = [p.strip(" ,?") for p in re.split(r",? and (?=what|which|who|where|when|how|is|are|does|do)\b", q, flags=re.I)]
            return "\n".join(p[0].upper() + p[1:] + "?" for p in parts if p)
        rw = rewrite_query(q)
        if re.search(r"variants|several|multiple|\b[2-5] (search )?queries|different (search )?queries", prompt):
            kw = " ".join(w for w in re.findall(r"[\w-]+", rw) if w.lower() not in aikit._STOP)
            lines = [q, rw, kw]
            return "\n".join(dict.fromkeys(lines))
        return rw

    return respond


# ====================================================================== questions and scoring

# Regexes an answer must contain to count as correct (all of them).
FACTS = {
    "q01": [r"8 minutes"], "q02": [r"\btwo crew"], "q03": [r"never operate|cannot operate"], "q04": [r"2 hours"],
    "q05": [r"6\.5 hours"], "q06": [r"60%", r"75%"], "q07": [r"P-2"], "q08": [r"probe every week"],
    "q09": [r"06:00", r"18:00"], "q10": [r"28 days"], "q11": [r"93%"], "q12": [r"2,400"],
    "q13": [r"20\.5%", r"21\.5%"], "q14": [r"12 candles", r"Module D"], "q15": [r"0\.4%"],
    "q16": [r"swapped every 90 days"], "q17": [r"36-minute|36 minutes"], "q18": [r"shed"],
    "q19": [r"mask", r"close the hatch"], "q20": [r"Priya Raman", r"commander"], "q21": [r"Module A hatch"],
    "q22": [r"Tomas Lindqvist"], "q23": [r"wakes at 06:00"], "q24": [r"19:00"], "q25": [r"2\.5 hours"],
    "q26": [r"Sunday", r"15:00"], "q27": [r"24 hours in advance"], "q28": [r"at most 4 hours"], "q29": [r"-80"],
    "q30": [r"gather in Module D"], "q31": [r"Module F"], "q32": [r"Module D", r"water wall"], "q33": [r"60 days"],
    "q34": [r"rotated every 30 days"], "q35": [r"kept for 90 days"], "q36": [r"mineral build-up"],
    "q37": [r"Environmental Control and Life Support"], "q38": [r"Noor Haddad", r"Module B"],
    "q39": [r"Kenji Watanabe", r"botanist"], "q40": [r"Module E", r"CO2 scrubbers|power controllers"],
    "q41": [r"Luc[ií]a Ferreira", r"systems specialist"],
}
# Regexes an answer must NOT contain (stale or contradictory facts).
FORBIDDEN = {"q01": [r"5 minutes"], "q02": [r"one crew member may"]}

# Crew-style questions for the retrieval chapter: exact identifiers (where keyword
# search shines) and slang (where rewriting shines).
SLANG_QUESTIONS = [
    {"id": "s01", "question": "What is kept in DF-1?", "doc_ids": ["sample-handling"], "type": "identifier", "facts": [r"-80|biological samples"]},
    {"id": "s02", "question": "What is shown on panel F-1?", "doc_ids": ["depressurisation-response"], "type": "identifier", "facts": [r"leak rate"]},
    {"id": "s03", "question": "How long did SCR-1 run alone?", "doc_ids": ["incident-2026-scrubber-fault"], "type": "identifier", "facts": [r"36 hours"]},
    {"id": "s04", "question": "What is logged on panel E-4?", "doc_ids": ["co2-scrubbers"], "type": "identifier", "facts": [r"swap"]},
    {"id": "s05", "question": "What should I do if coil D-3 ices up?", "doc_ids": ["hydroponics-troubleshooting"], "type": "identifier", "facts": [r"defrost"]},
    {"id": "s06", "question": "Which module is AL-2 in?", "doc_ids": ["modules-map"], "type": "identifier", "facts": [r"Module B"]},
    {"id": "s07", "question": "What failed in SCR-2?", "doc_ids": ["incident-2026-scrubber-fault"], "type": "identifier", "facts": [r"fan"]},
    {"id": "s08", "question": "What is the RED for?", "doc_ids": ["exercise-requirements"], "type": "identifier", "facts": [r"resistive exercise device"]},
    {"id": "s17", "question": "Which module has AL-1?", "doc_ids": ["airlock-procedure"], "type": "identifier", "facts": [r"Module F"]},
    {"id": "s18", "question": "What is OGS?", "doc_ids": ["glossary"], "type": "identifier", "facts": [r"Oxygen Generation System"]},
    {"id": "s19", "question": "What should I check on coil D-3?", "doc_ids": ["hydroponics-troubleshooting"], "type": "identifier", "facts": [r"ice"]},
    {"id": "s20", "question": "What does pump P-2 do?", "doc_ids": ["hydroponics-troubleshooting"], "type": "identifier", "facts": [r"root zone"]},
    {"id": "s09", "question": "When do the plant lamps turn on?", "doc_ids": ["hydroponics-schedule"], "type": "slang", "facts": [r"05:00"]},
    {"id": "s10", "question": "Where does our rubbish go?", "doc_ids": ["waste-management"], "type": "slang", "facts": [r"compacted|full of trash|Module D"]},
    {"id": "s11", "question": "What time is lights out?", "doc_ids": ["daily-schedule"], "type": "slang", "facts": [r"21:30"]},
    {"id": "s12", "question": "Where is the heart shocker?", "doc_ids": ["medical-emergencies"], "type": "slang", "facts": [r"Module A hatch"]},
    {"id": "s13", "question": "How often does the supply ship come?", "doc_ids": ["cargo-resupply"], "type": "slang", "facts": [r"60 days"]},
    {"id": "s14", "question": "Who has the code for the medicine cupboard?", "doc_ids": ["med-bay-access"], "type": "slang", "facts": [r"Priya Raman"]},
    {"id": "s15", "question": "How long do I need to spend in the gym each day?", "doc_ids": ["exercise-requirements"], "type": "slang", "facts": [r"2\.5 hours"]},
    {"id": "s16", "question": "Where do we hide during a solar storm?", "doc_ids": ["radiation-storm-protocol"], "type": "slang", "facts": [r"Module D"]},
]

# More unanswerable questions, many close to real handbook topics.
EXTRA_UNANSWERABLE = [
    {"id": "u01", "question": "What is the airlock override code?"},
    {"id": "u02", "question": "How many litres does the nutrient tank in Module C hold?"},
    {"id": "u03", "question": "What is the battery capacity in kilowatt-hours?"},
    {"id": "u04", "question": "Who was the commander of the previous crew?"},
    {"id": "u05", "question": "How many calories does each crew member eat per day?"},
    {"id": "u06", "question": "Which crew member is allergic to peanuts?"},
    {"id": "u07", "question": "When is the next spacewalk scheduled?"},
    {"id": "u08", "question": "What is the password for HELIOS-NET?"},
    {"id": "u09", "question": "How fast does the station travel in kilometres per second?"},
    {"id": "u10", "question": "How heavy is a lettuce tray?"},
    {"id": "u11", "question": "What brand of treadmill is on board?"},
    {"id": "u12", "question": "How much does a Heron robotic arm cost?"},
]
for _q in EXTRA_UNANSWERABLE:
    _q.update(answer=None, doc_ids=[], type="unanswerable")


def questions(include_unanswerable: bool = True) -> list[dict]:
    """The 45 Helios questions (41 answerable + 4 unanswerable)."""
    qs = helios.questions()
    return qs if include_unanswerable else [q for q in qs if q["doc_ids"]]


def is_refusal(answer: str) -> bool:
    return bool(re.search(r"\bdon'?t know\b|\bnot (in|covered by) the (provided )?documents\b|\bcan(no|')t find\b", answer or "", re.I))


def _facts_for(q: dict) -> list[str]:
    return q.get("facts") or FACTS.get(q["id"], [])


def is_correct(q: dict, answer: str) -> bool:
    """Right answer for an answerable question, or a refusal for an unanswerable one."""
    answer = answer or ""
    if not q.get("doc_ids"):
        return is_refusal(answer)
    if is_refusal(answer):
        return False
    if any(re.search(p, answer, re.I) for p in FORBIDDEN.get(q["id"], [])):
        return False
    facts = _facts_for(q)
    return bool(facts) and all(re.search(p, answer, re.I) for p in facts)


def has_evidence(q: dict, chunks: list[dict]) -> bool:
    """Context recall: does some retrieved chunk contain each answer fact?"""
    facts = _facts_for(q)
    return bool(facts) and all(any(re.search(p, c["text"], re.I) for c in chunks) for p in facts)


# ====================================================================== chunking


def split_sentences(text: str) -> list[str]:
    """Sentences of a handbook doc, headings dropped."""
    text = re.sub(r"^#+ .*$", "", text, flags=re.M)
    parts = re.split(r"(?<!Dr\.)(?<=[.!?])\s+|\n+", text)
    return [p.strip() for p in parts if p.strip()]


def chunk_fixed(text: str, size: int, overlap: int = 0) -> list[str]:
    """Fixed windows of `size` characters; each starts `size - overlap` after the last."""
    if overlap >= size:
        raise ValueError("overlap must be smaller than size")
    step, out = size - overlap, []
    for start in range(0, len(text), step):
        out.append(text[start:start + size])
        if start + size >= len(text):
            break
    return out


def chunk_sentences(text: str, n: int = 1, stride: int | None = None) -> list[str]:
    """Windows of `n` sentences, starting every `stride` sentences (default: n, no overlap)."""
    sents = split_sentences(text)
    stride = stride or n
    out = []
    for i in range(0, len(sents), stride):
        out.append(" ".join(sents[i:i + n]))
        if i + n >= len(sents):
            break
    return out


def chunk_headings(text: str) -> list[str]:
    """One chunk per '## ' section; text before the first section is its own chunk.
    The '# ' document heading is dropped."""
    text = re.sub(r"^# .*\n?", "", text, flags=re.M)
    parts = re.split(r"\n(?=## )", text)
    return [p.strip() for p in parts if p.strip()]


def orbit_chunks() -> list[dict]:
    """ORBIT's index from chapter 3 on: one-sentence chunks with title headers,
    superseded documents removed."""
    return make_chunks(helios.handbook(include_superseded=False), chunk_sentences, title=True)


def make_chunks(docs: list[dict], chunker=lambda t: [t], title: bool = True) -> list[dict]:
    """Run `chunker(text)` on every doc and attach metadata.
    With title=True each chunk's text starts with "<doc title>: " so the chunk
    carries the context its doc's title gives it."""
    out = []
    for d in docs:
        for i, piece in enumerate(chunker(d["text"])):
            out.append({"id": f"{d['id']}#{i}", "doc_id": d["id"], "title": d["title"], "section": d["section"],
                        "updated": d["updated"], "text": f"{d['title']}: {piece}" if title else piece})
    return out


# ====================================================================== retrieval


class DenseIndex:
    """Embeds chunk texts with aikit.embed; search() is a dot product (cosine on unit vectors)."""

    def __init__(self, chunks: list[dict]):
        self.chunks = chunks
        self.vectors = aikit.embed([c["text"] for c in chunks])

    def scores(self, query: str) -> np.ndarray:
        return self.vectors @ aikit.embed(query)

    def search(self, query: str, k: int = 5) -> list[dict]:
        s = self.scores(query)
        return [dict(self.chunks[i], score=float(s[i])) for i in np.argsort(-s, kind="stable")[:k]]


STOPWORDS = set("""a an the is are was were be been of to in on at for from by with and or what which who whom how
do does did i me my we our you your it its this that these those when where why can could should would will
there here not no any all each some much many""".split())


def tokenize(text: str) -> list[str]:
    """Lowercase words, keeping hyphenated ids like 'p-2' or 'df-1' whole; drops
    stopwords and a plural 's'."""
    out = []
    for w in re.findall(r"[a-z0-9]+(?:-[a-z0-9]+)*", text.lower()):
        if w in STOPWORDS:
            continue
        if len(w) > 4 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]
        out.append(w)
    return out


class BM25Index:
    """Okapi BM25 over tokenize()d chunks."""

    def __init__(self, chunks: list[dict], k1: float = 1.5, b: float = 0.75):
        self.chunks, self.k1, self.b = chunks, k1, b
        self.docs = [tokenize(c["text"]) for c in chunks]
        self.tfs = [Counter(d) for d in self.docs]
        self.N = len(self.docs)
        self.avgdl = sum(len(d) for d in self.docs) / max(1, self.N)
        self.df = Counter(w for d in self.docs for w in set(d))

    def idf(self, w: str) -> float:
        n = self.df.get(w, 0)
        return math.log(1 + (self.N - n + 0.5) / (n + 0.5))

    def scores(self, query: str) -> np.ndarray:
        out = np.zeros(self.N)
        q = tokenize(query)
        for i, tf in enumerate(self.tfs):
            dl = len(self.docs[i])
            for w in q:
                f = tf.get(w, 0)
                if f:
                    out[i] += self.idf(w) * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
        return out

    def search(self, query: str, k: int = 5) -> list[dict]:
        s = self.scores(query)
        return [dict(self.chunks[i], score=float(s[i])) for i in np.argsort(-s, kind="stable")[:k]]


def rrf(rankings: list[list[str]], k: int = 60) -> list[str]:
    """Reciprocal rank fusion: each list ranks ids best first; score = sum 1/(k + rank)."""
    score: dict[str, float] = {}
    for ranking in rankings:
        for r, cid in enumerate(ranking, start=1):
            score[cid] = score.get(cid, 0.0) + 1.0 / (k + r)
    return sorted(score, key=lambda c: -score[c])


class HybridIndex:
    """Dense + BM25, fused with RRF over each one's top `depth` results."""

    def __init__(self, chunks: list[dict], depth: int = 30, rrf_k: int = 60):
        self.chunks, self.depth, self.rrf_k = chunks, depth, rrf_k
        self.by_id = {c["id"]: c for c in chunks}
        self.dense, self.bm25 = DenseIndex(chunks), BM25Index(chunks)

    def search(self, query: str, k: int = 5) -> list[dict]:
        d = [c["id"] for c in self.dense.search(query, self.depth)]
        b = [c["id"] for c in self.bm25.search(query, self.depth)]
        return [self.by_id[i] for i in rrf([d, b], self.rrf_k)[:k]]


_RERANK_SYNONYMS = {
    "wake": {"wakes"}, "long": {"minute", "hour", "day", "last", "length", "duration"}, "often": {"every"},
    "where": {"module", "next"}, "who": {"commander", "officer", "specialist", "engineer", "botanist", "scientist"},
    "caus": {"cause", "because"}, "maximum": {"most", "max", "longest"}, "longest": {"most", "max", "maximum"},
    "big": {"hold", "litre", "size"}, "normal": {"should", "stay", "nominal"}, "range": {"between"},
    "advance": {"before", "ahead"}, "kept": {"keep", "retain", "stored"}, "share": {"percent"},
}


def _expand_words(words) -> set:
    out = set(words)
    for w in list(out):
        out |= _RERANK_SYNONYMS.get(w, set())
        for k, v in _RERANK_SYNONYMS.items():
            if w in v:
                out.add(k)
    return out


_IDF: dict | None = None


def _word_idf(w: str) -> float:
    """How informative a word is, from sentence frequencies in the handbook. Words the
    handbook never uses get the highest weight: a question that hinges on them is
    probably not answered here. (A trained cross-encoder learns weights like these.)"""
    global _IDF
    if _IDF is None:
        sents = [s for d in helios.handbook() for s in split_sentences(d["title"] + ". " + d["text"])]
        df = Counter(w for s in sents for w in set(aikit.content_words(s)))
        _IDF = {"__n__": len(sents), **df}
    n = _IDF["__n__"]
    return math.log((n + 1) / (_IDF.get(w, 0) + 1)) + 1


class CrossEncoder:
    """Stand-in for a cross-encoder reranker: it reads the query and one chunk
    *together* and scores how well the chunk answers it: the share of the query's
    informative words the chunk covers (weighted by rarity, with light stemming and
    synonyms), plus a bonus when the chunk has the kind of thing asked for (a number
    for "how long", a name for "who"). Scores run from about -0.1 to 1.2.

    Each pair costs `ms_per_pair` of simulated time on `clock`, like a real reranker
    call. `pairs_scored` counts the pairs.
    """

    def __init__(self, clock: VirtualClock | None = None, ms_per_pair: float = 12.0):
        self.clock = clock or VirtualClock()
        self.ms_per_pair = ms_per_pair
        self.pairs_scored = 0

    def score(self, query: str, text: str) -> float:
        self.pairs_scored += 1
        self.clock.advance_ms(self.ms_per_pair)
        qw = set(aikit.content_words(query))
        if not qw:
            return 0.0
        tw = _expand_words(aikit.content_words(text))
        total = sum(_word_idf(w) for w in qw)
        cover = sum(_word_idf(w) for w in qw if w in tw) / total
        ql = query.lower()
        bonus = 0.0
        if re.search(r"\bhow (long|often|many|much|big)|what time|when\b|at what", ql):
            bonus = 0.2 if re.search(r"\d", text) else -0.1
        elif re.match(r"\s*who\b", ql):
            bonus = 0.2 if re.search(r"[A-Z][a-z]+ [A-Z][a-z]+", text) else -0.1
        return round(cover + bonus, 4)

    def rerank(self, query: str, chunks: list[dict], top_n: int = 5) -> list[dict]:
        scored = [(self.score(query, c["text"]), i, c) for i, c in enumerate(chunks)]
        scored.sort(key=lambda x: (-x[0], x[1]))
        return [dict(c, rerank_score=s) for s, _, c in scored[:top_n]]


# ====================================================================== citations

CLAIM_RE = re.compile(r"([^\[\]]+?)\s*((?:\[[^\]]+\]\s*)+)")


def parse_citations(answer: str) -> list[tuple[str, list[str]]]:
    """Split an answer into (claim, [cited ids]) pairs. A claim is the text before a
    group of [id] markers; trailing text with no marker is a claim citing nothing."""
    out, end = [], 0
    for m in CLAIM_RE.finditer(answer):
        out.append((m.group(1).strip(), re.findall(r"\[([^\]]+)\]", m.group(2))))
        end = m.end()
    tail = answer[end:].strip()
    if tail:
        out.append((tail, []))
    return out


def support_score(claim: str, text: str) -> float:
    """Share of the claim's content words (lightly stemmed) that appear in `text`."""
    words = set(aikit.content_words(claim))
    if not words:
        return 1.0
    return len(words & set(aikit.content_words(text))) / len(words)


def is_supported(claim: str, ids: list[str], chunks: list[dict], min_overlap: float = 0.8) -> bool:
    """A claim is supported when it cites at least one id, every cited id was
    retrieved, and the cited chunks contain at least `min_overlap` of its words."""
    retrieved = {c["doc_id"] for c in chunks}
    if not ids or any(i not in retrieved for i in ids):
        return False
    text = " ".join(c["text"] for c in chunks if c["doc_id"] in ids)
    return support_score(claim, text) >= min_overlap


# ====================================================================== generation and evaluation


def format_documents(chunks: list[dict]) -> str:
    return "\n".join(f'<document id="{c["doc_id"]}">{c["text"]}</document>' for c in chunks)


def build_prompt(question: str, chunks: list[dict], cite: bool = False) -> tuple[str, str]:
    """Returns (system, user): instructions in the system prompt, documents first
    and the question last in the user turn."""
    system = SYSTEM + (" Cite the document id in square brackets after each sentence, like [doc-id]." if cite else "")
    return system, f"{format_documents(chunks)}\n<question>{question}</question>"


def generate(client, question: str, chunks: list[dict], cite: bool = False, max_tokens: int = 400) -> str:
    system, user = build_prompt(question, chunks, cite)
    r = client.messages.create(model=MODEL, max_tokens=max_tokens, system=system,
                               messages=[{"role": "user", "content": user}])
    return r.content[0].text


def _row(q: dict, chunks: list[dict], answer: str) -> dict:
    got = [c["doc_id"] for c in chunks]
    return {
        "id": q["id"], "type": q.get("type", ""), "question": q["question"],
        "gold": q.get("doc_ids", []), "retrieved": got,
        "hit": all(g in got for g in q["doc_ids"]) if q.get("doc_ids") else None,
        "evidence": has_evidence(q, chunks) if q.get("doc_ids") else None,
        "answer": answer, "correct": is_correct(q, answer),
        "tokens": sum(count_tokens(c["text"]) for c in chunks),
    }


def _summary(rows: list[dict]) -> dict:
    import pandas as pd

    df = pd.DataFrame(rows)
    ans = df[df["hit"].notna()]
    return {
        "recall": round(float(ans["hit"].mean()), 3) if len(ans) else None,
        "evidence": round(float(ans["evidence"].mean()), 3) if len(ans) else None,
        "accuracy": round(float(df["correct"].mean()), 3),
        "context_tokens": round(float(df["tokens"].mean()), 1),
        "rows": df,
    }


def evaluate(retrieve, qs: list[dict] | None = None, k: int = 5, client=None, cite: bool = False) -> dict:
    """Run a retrieve-then-generate pipeline over questions and score it.

    retrieve(question_text, k) -> list of chunk dicts (each with doc_id and text).
    Returns a dict:
        recall          share of answerable questions whose gold docs were all retrieved
        evidence        share of answerable questions whose answer facts are inside the retrieved chunks
        accuracy        share of all questions answered correctly (refusal counts as correct when unanswerable)
        context_tokens  mean tokens of retrieved context per question (a cost proxy)
        rows            DataFrame, one row per question, for error analysis
    """
    qs = qs if qs is not None else questions()
    client = client or make_client()
    rows = []
    for q in qs:
        chunks = retrieve(q["question"], k)
        rows.append(_row(q, chunks, generate(client, q["question"], chunks, cite=cite)))
    return _summary(rows)


def evaluate_pipeline(rag, qs: list[dict] | None = None) -> dict:
    """Like evaluate(), for a whole pipeline: rag(question_text) -> (answer, chunks)."""
    qs = qs if qs is not None else questions()
    rows = []
    for q in qs:
        answer, chunks = rag(q["question"])
        rows.append(_row(q, chunks, answer))
    return _summary(rows)


# ====================================================================== diagnosis

BUCKETS = ["retrieval miss", "generation error", "over-refused", "should have refused"]


def failure_bucket(row) -> str | None:
    """Where a failure happened, from one row of evaluate()["rows"] (None if correct).

    retrieval miss       answerable; a gold doc was not retrieved, so the model never saw the fact
    generation error     answerable; gold docs retrieved; the answer is wrong
    over-refused         answerable; gold docs retrieved; ORBIT refused anyway
    should have refused  unanswerable; ORBIT answered
    """
    if row["correct"]:
        return None
    if not row["gold"]:
        return "should have refused"
    if not row["hit"]:
        return "retrieval miss"
    return "over-refused" if is_refusal(row["answer"]) else "generation error"


def failure_buckets(rows) -> dict:
    """Counts per bucket, in BUCKETS order."""
    labels = [failure_bucket(r) for _, r in rows.iterrows()]
    return {b: labels.count(b) for b in BUCKETS}


def mistake_cost(rows, wrong_cost: float = 5, refusal_cost: float = 1) -> float:
    """wrong_cost per wrong answer + refusal_cost per refusal of an answerable question."""
    refused = rows["answer"].map(is_refusal)
    wrong = int((~rows["correct"] & ~refused).sum())
    over = int((~rows["correct"] & refused).sum())
    return wrong_cost * wrong + refusal_cost * over
