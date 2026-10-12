"""Helpers for the embeddings-vector-search course.

Import in pre_code:  from kits.embeddings_vector_search import ...

Text side (Helios-7 handbook):
    split_sentences(text)          sentence splitter used for chunking
    handbook_docs()                answerable handbook docs (superseded ones dropped)
    handbook_chunks(title_prefix)  one chunk per sentence, with doc_id metadata
    labelled_questions()           handbook questions that have gold doc ids
    crew_queries(kind, split)      a second labelled set written by the crew:
                                   kinds "exact" (part codes like P-2), "paraphrase"
                                   (everyday words) and "jargon" (station slang)
    CREW_GLOSSARY                  station slang -> handbook words
    embed_general(texts)           a "general-purpose" embedding model: same LSA recipe
                                   as aikit.embed, but trained on everyday text too,
                                   so it knows that "evening meal" is close to "dinner"
    CODE_TOKEN_PATTERN             a token regex that keeps codes like "p-2" whole
    KeywordIndex                   TF-IDF keyword search (code-aware)
    rrf(rankings)                  reciprocal rank fusion
    dedupe(ids)                    keep the first occurrence, in order

Metrics:
    hit_at_k, recall_at_k, reciprocal_rank, ndcg_at_k
    build_testset(), evaluate(search, testset, k)   labelled set and per-query results

Broken systems for troubleshooting lessons:
    summed_doc_vectors()           doc vectors that were summed, never normalised
    legacy_index()                 a broken "related docs" index (ch. 1 boss)

Vector-index side (synthetic, seeded, realistic clustering):
    make_vectors(n, d)             clustered unit vectors, float32
    make_queries(X, n)             queries near the data
    exact_topk(X, Q, k)            brute-force ground truth
    knn_graph(X, m)                k-nearest-neighbour graph (array of neighbour ids)
    greedy_search / beam_search    reference graph searches
    projected_latency_ms(frac)     production latency model (5M x 768 vectors)
"""

from __future__ import annotations

import heapq
import re

import numpy as np

import aikit

# ------------------------------------------------------------------ text corpus


def split_sentences(text: str) -> list[str]:
    """Split a handbook body into sentences. Markdown headings are dropped."""
    text = re.sub(r"^#+ .*$", "", text, flags=re.M)
    parts = re.split(r"(?<!Dr\.)(?<=[.!?])\s+|\n+", text)
    return [p.strip() for p in parts if len(p.strip()) > 3]


def handbook_docs() -> list[dict]:
    """The 34 current handbook docs (the superseded 2024 airlock procedure is dropped)."""
    return aikit.helios.handbook(include_superseded=False)


def handbook_chunks(title_prefix: bool = False) -> list[dict]:
    """One chunk per sentence: dicts with id ("doc-id#n"), doc_id, title and text.
    With title_prefix=True the chunk text starts with "<title>. "."""
    out = []
    for d in handbook_docs():
        for i, s in enumerate(split_sentences(d["text"])):
            text = f"{d['title']}. {s}" if title_prefix else s
            out.append({"id": f"{d['id']}#{i}", "doc_id": d["id"], "title": d["title"], "text": text})
    return out


def labelled_questions() -> list[dict]:
    """Handbook questions that have at least one gold doc (unanswerables dropped)."""
    return [q for q in aikit.helios.questions() if q["doc_ids"]]


# Written for this course. Gold doc ids refer to handbook_docs().
_CREW = [
    # exact: the part or panel code is the main signal
    ("e01", "exact", "What is shown on F-2?", ["airlock-procedure"]),
    ("e02", "exact", "What does F-1 display?", ["depressurisation-response"]),
    ("e03", "exact", "What gets logged on E-4?", ["co2-scrubbers"]),
    ("e04", "exact", "P-2 is silent", ["hydroponics-troubleshooting", "incident-2025-hydro-flood"]),
    ("e05", "exact", "Does D-3 need a defrost?", ["hydroponics-troubleshooting"]),
    ("e06", "exact", "What temperature is DF-1?", ["sample-handling"]),
    ("e07", "exact", "How long does L-1 take to land?", ["medical-emergencies"]),
    ("e08", "exact", "What broke in SCR-2?", ["incident-2026-scrubber-fault"]),
    ("e09", "exact", "Where is AL-2?", ["modules-map"]),
    ("e10", "exact", "Rules for BSL-2", ["sample-handling"]),
    ("e11", "exact", "Who can join HELIOS-NET?", ["it-network"]),
    ("e12", "exact", "How long did SCR-1 run alone?", ["incident-2026-scrubber-fault"]),
    # paraphrase: everyday words that the handbook never uses
    ("p01", "paraphrase", "When is the evening meal?", ["galley-and-meals"]),
    ("p02", "paraphrase", "How long should I work out each day?", ["exercise-requirements"]),
    ("p03", "paraphrase", "Where do we hide from a solar flare?", ["radiation-storm-protocol"]),
    ("p04", "paraphrase", "Who is the ship's doctor?", ["crew-roster", "med-bay-access"]),
    ("p05", "paraphrase", "When can I ring home?", ["comms-windows"]),
    ("p06", "paraphrase", "How often do supply ships visit?", ["cargo-resupply"]),
    ("p07", "paraphrase", "What gas do I breathe before going outside?", ["eva-prep-checklist"]),
    ("p08", "paraphrase", "How quiet must the bedrooms be?", ["crew-quarters"]),
    ("p09", "paraphrase", "What keeps the lights on at night?", ["power-systems"]),
    ("p10", "paraphrase", "We are leaking air, where do we go?", ["depressurisation-response"]),
    ("p11", "paraphrase", "What happens to our rubbish?", ["waste-management"]),
    ("p12", "paraphrase", "When does everyone go to bed?", ["daily-schedule"]),
    # jargon: station slang (see CREW_GLOSSARY)
    ("j01", "jargon", "When does the veg bay get watered?", ["hydroponics-schedule"]),
    ("j02", "jargon", "How long is the dark pass?", ["power-systems"]),
    ("j03", "jargon", "When is the next bird due?", ["cargo-resupply"]),
    ("j04", "jargon", "Who is allowed to use the box?", ["lab-booking-policy", "sample-handling"]),
    ("j05", "jargon", "How many scrubs do we have?", ["co2-scrubbers"]),
    ("j06", "jargon", "What happens on suit day?", ["eva-prep-checklist"]),
    ("j07", "jargon", "What does ORBIT do with messages in a blackout?", ["comms-windows"]),
    ("j08", "jargon", "Who runs the farm?", ["hydroponics-schedule"]),
    ("j09", "jargon", "How cold is the cold box?", ["sample-handling"]),
    ("j10", "jargon", "What is the longest walk allowed?", ["eva-prep-checklist"]),
    ("j11", "jargon", "How long is the chute ride down?", ["medical-emergencies"]),
    ("j12", "jargon", "Who has the code for the drug locker besides Doc?", ["med-bay-access"]),
    ("j13", "jargon", "What is in the hab?", ["modules-map"]),
    ("j14", "jargon", "When do we hide behind the water wall?", ["radiation-storm-protocol"]),
    ("j15", "jargon", "Where do the farm crops go?", ["galley-and-meals"]),
    ("j16", "jargon", "Does the bird take our trash?", ["waste-management", "cargo-resupply"]),
]

CREW_GLOSSARY = {
    "veg bay": "hydroponics Module C",
    "farm": "hydroponics Module C",
    "dark pass": "eclipse",
    "bird": "cargo vehicle Tern",
    "box": "glovebox",
    "scrubs": "CO2 scrubbers",
    "suit day": "EVA day spacewalk",
    "walk": "spacewalk",
    "blackout": "loss of signal LOS",
    "cold box": "deep freezer",
    "chute": "lifeboat capsule L-1 landing",
    "doc": "medical officer",
    "drug locker": "controlled medicines cabinet",
    "hab": "Module A Habitat",
    "water wall": "radiation storm shelter Module D",
}


def crew_queries(kind: str | list | None = None, split: str | None = None) -> list[dict]:
    """Crew-written labelled queries: dicts with id, kind, query, doc_ids.

    kind:  "exact", "paraphrase", "jargon" (or a list of them); None for all.
    split: "dev" (odd-numbered ids), "test" (even-numbered ids) or None for all.
    """
    kinds = [kind] if isinstance(kind, str) else kind
    out = []
    for qid, k, q, gold in _CREW:
        if kinds and k not in kinds:
            continue
        n = int(qid[1:])
        if split == "dev" and n % 2 == 0 or split == "test" and n % 2 == 1:
            continue
        out.append({"id": qid, "kind": k, "query": q, "doc_ids": list(gold)})
    return out


# Everyday text a general-purpose model would have seen in training. It never
# mentions Helios-7 or the station's own slang.
_WORLD = """Dinner is the evening meal, sometimes called supper.
Breakfast is the morning meal and lunch is the midday meal.
People work out in a gym to stay fit; exercise such as running on a treadmill or cycling builds muscle and bone.
A daily workout or exercise session keeps the body healthy.
A doctor, or physician, is a medical officer who treats patients and gives medicine.
A solar flare is a burst of radiation from the sun; a solar storm sends particles that are dangerous to astronauts.
During a solar storm people hide and shelter from radiation behind thick walls.
To ring or phone home means to call your family.
Supply ships and cargo vehicles bring supplies, food and equipment to a station and visit regularly.
Before going outside in a spacesuit, astronauts breathe pure oxygen.
A bedroom is private sleeping quarters; quiet means a low noise level.
At night there is no sunlight, so solar panels produce no power and batteries keep the lights on.
An eclipse is when a planet blocks the sun.
A leak lets air escape; when you are leaking air the pressure drops and an alarm sounds.
Rubbish, garbage and waste are trash that must be thrown away or stored.
Going to bed means going to sleep at bedtime, when the lights dim.
Plants that droop or wilt need water or a working pump.
A fridge or freezer keeps food and samples cold.
A fire alarm warns of smoke and fire.
A password protects a computer network.
An assistant answers questions and follows instructions.
A spacesuit protects an astronaut outside the spacecraft.
A heater or cooler controls the temperature of a room.
A hospital or clinic has a medical bay with beds and medicine.
A timetable or schedule lists what happens at what time each day.
Engineers repair machines, pumps, fans and valves when they break.
Water from a tap is drinking water; clean water is stored in a tank.""".split("\n")

_general = None


def embed_general(texts):
    """Embed with the "general-purpose" model: LSA fitted on the handbook plus everyday
    text, 64 dims, L2-normalised. Same interface as aikit.embed."""
    global _general
    if _general is None:
        corpus = []
        for d in aikit.helios.handbook():
            corpus.append(d["title"] + ". " + d["text"])
            corpus.extend(split_sentences(d["text"]))
        _general = aikit.Embedder(corpus + _WORLD, dim=64)
    return _general.embed(texts)


# ------------------------------------------------------------------ keyword search

CODE_TOKEN_PATTERN = r"[a-z]+-\d+|[a-z0-9]{2,}"


class KeywordIndex:
    """TF-IDF keyword search whose tokenizer keeps codes like "p-2" and "al-1" whole.

    idx = KeywordIndex(texts); order, scores = idx.search("Is P-2 running?", k=5)
    """

    def __init__(self, texts: list[str]):
        from sklearn.feature_extraction.text import TfidfVectorizer

        self.vec = TfidfVectorizer(token_pattern=CODE_TOKEN_PATTERN, stop_words="english", sublinear_tf=True)
        self.M = self.vec.fit_transform(texts)

    def scores(self, query: str) -> np.ndarray:
        return (self.M @ self.vec.transform([query]).T).toarray().ravel()

    def search(self, query: str, k: int = 5):
        s = self.scores(query)
        order = np.argsort(-s, kind="stable")[:k]
        return order, s[order]


def rrf(rankings: list, k: int = 60) -> list:
    """Reciprocal rank fusion: score(item) = sum over rankings of 1 / (k + rank), rank from 1.
    Returns items sorted by fused score, best first (ties keep first-seen order)."""
    scores: dict = {}
    for ranking in rankings:
        for r, item in enumerate(ranking, start=1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + r)
    return sorted(scores, key=lambda x: -scores[x])


def dedupe(ids) -> list:
    """Keep the first occurrence of each id, in order."""
    seen, out = set(), []
    for i in ids:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


# ------------------------------------------------------------------ metrics


def hit_at_k(ranked, relevant, k: int) -> float:
    """1.0 if any relevant item is in the top k, else 0.0."""
    return float(any(r in set(relevant) for r in list(ranked)[:k]))


def recall_at_k(ranked, relevant, k: int) -> float:
    """Share of the relevant items that appear in the top k."""
    rel = set(relevant)
    return len(rel & set(list(ranked)[:k])) / len(rel) if rel else 0.0


def reciprocal_rank(ranked, relevant) -> float:
    """1 / rank of the first relevant item (rank from 1); 0.0 if none is found."""
    rel = set(relevant)
    for i, r in enumerate(ranked, start=1):
        if r in rel:
            return 1.0 / i
    return 0.0


def ndcg_at_k(ranked, gains: dict, k: int) -> float:
    """nDCG@k with graded gains {item: gain}; log2 discount."""
    dcg = sum(gains.get(r, 0) / np.log2(i + 1) for i, r in enumerate(list(ranked)[:k], start=1))
    ideal = sorted(gains.values(), reverse=True)[:k]
    idcg = sum(g / np.log2(i + 1) for i, g in enumerate(ideal, start=1))
    return float(dcg / idcg) if idcg else 0.0


# ------------------------------------------------------------------ broken systems


def summed_doc_vectors():
    """Doc vectors built the wrong way: the sum of each doc's sentence embeddings,
    never normalised, so long docs have long vectors. Returns (doc_ids, V)."""
    docs = handbook_docs()
    V = np.array([aikit.embed(split_sentences(d["text"])).sum(axis=0) for d in docs])
    return [d["id"] for d in docs], V


def legacy_index():
    """The "related docs" index left by a previous engineer. Returns (doc_ids, texts, V).

    It has two bugs: the rows of V were written in order of the docs' `updated`
    date while doc_ids is in alphabetical order, and each row is a sum of sentence
    vectors that was never normalised."""
    docs = handbook_docs()
    ids = [d["id"] for d in docs]
    texts = [d["title"] + ". " + d["text"] for d in docs]
    by_date = sorted(docs, key=lambda d: (d["updated"], d["id"]))
    V = np.array([aikit.embed(split_sentences(d["text"])).sum(axis=0) for d in by_date])
    return ids, texts, V


# ------------------------------------------------------------------ synthetic vectors


def make_vectors(n: int, d: int = 64, n_topics: int = 100, spread: float = 2.0, seed: int = 0) -> np.ndarray:
    """n unit vectors in d dims, float32, clustered around n_topics random topic
    directions (real embeddings are clustered too). Larger spread = fuzzier topics."""
    rng = np.random.default_rng(seed)
    C = rng.standard_normal((n_topics, d))
    C /= np.linalg.norm(C, axis=1, keepdims=True)
    w = rng.dirichlet(np.ones(n_topics) * 2)
    lab = rng.choice(n_topics, size=n, p=w)
    X = C[lab] + spread * rng.standard_normal((n, d)) / np.sqrt(d)
    X /= np.linalg.norm(X, axis=1, keepdims=True)
    return X.astype(np.float32)


def make_queries(X: np.ndarray, n: int = 100, noise: float = 0.5, seed: int = 1) -> np.ndarray:
    """n unit query vectors: random rows of X plus noise (queries look like the data)."""
    rng = np.random.default_rng(seed)
    Q = X[rng.choice(len(X), n, replace=False)] + noise * rng.standard_normal((n, X.shape[1])) / np.sqrt(X.shape[1])
    Q /= np.linalg.norm(Q, axis=1, keepdims=True)
    return Q.astype(np.float32)


def exact_topk(X: np.ndarray, Q: np.ndarray, k: int = 10) -> np.ndarray:
    """Brute-force top-k row ids for each query (rows of Q), best first. Shape (len(Q), k)."""
    Q2 = np.atleast_2d(Q)
    S = Q2 @ X.T
    part = np.argpartition(-S, kth=min(k, S.shape[1] - 1), axis=1)[:, :k]
    rows = np.arange(len(Q2))[:, None]
    order = np.argsort(-S[rows, part], axis=1, kind="stable")
    return part[rows, order]


def knn_graph(X: np.ndarray, m: int = 16) -> np.ndarray:
    """Each node's m nearest other nodes by cosine, best first. Shape (n, m).
    Built by brute force, so keep n to a few thousand."""
    G = np.empty((len(X), m), dtype=np.int64)
    for start in range(0, len(X), 1000):
        S = X[start:start + 1000] @ X.T
        rows = np.arange(S.shape[0])
        S[rows, start + rows] = -np.inf
        part = np.argpartition(-S, kth=m, axis=1)[:, :m]
        order = np.argsort(-S[rows[:, None], part], axis=1, kind="stable")
        G[start:start + 1000] = part[rows[:, None], order]
    return G


def greedy_search(q, X, graph, entry: int = 0):
    """Reference greedy walk: move to the best neighbour while it improves.
    Returns (node, n_distance_computations)."""
    cur, best, evals = entry, float(X[entry] @ q), 1
    while True:
        nb = graph[cur]
        s = X[nb] @ q
        evals += len(nb)
        j = int(np.argmax(s))
        if s[j] <= best:
            return cur, evals
        cur, best = int(nb[j]), float(s[j])


def beam_search(q, X, graph, ef: int = 20, k: int = 10, entry: int = 0):
    """Reference best-first (beam) search, the core of HNSW's layer search.
    Returns (top-k node ids best first, n_distance_computations)."""
    visited = {entry}
    s0 = float(X[entry] @ q)
    evals = 1
    candidates = [(-s0, entry)]
    results = [(s0, entry)]
    while candidates:
        neg, c = heapq.heappop(candidates)
        if -neg < results[0][0] and len(results) >= ef:
            break
        for nb in graph[c]:
            nb = int(nb)
            if nb in visited:
                continue
            visited.add(nb)
            s = float(X[nb] @ q)
            evals += 1
            if len(results) < ef or s > results[0][0]:
                heapq.heappush(candidates, (-s, nb))
                heapq.heappush(results, (s, nb))
                if len(results) > ef:
                    heapq.heappop(results)
    top = [i for _, i in sorted(results, reverse=True)[:k]]
    return top, evals


# Production numbers for the indexes chapter: 5M vectors of 768 dims, float32.
# A full brute-force scan is 5e6 * 768 multiply-adds; at about 20 billion per second
# that is 192 ms. Every query also pays a fixed 2 ms (query embedding lookup, network).
FULL_SCAN_MS = 192.0
OVERHEAD_MS = 2.0


def projected_latency_ms(frac_scanned) -> np.ndarray:
    """Projected production latency for queries that scan this fraction of the
    vectors (a number or an array of per-query fractions)."""
    return OVERHEAD_MS + np.asarray(frac_scanned, dtype=float) * FULL_SCAN_MS


# ------------------------------------------------------------------ the search system ORBIT ships


def _minmax(x: np.ndarray) -> np.ndarray:
    lo, hi = float(np.min(x)), float(np.max(x))
    return (x - lo) / (hi - lo) if hi > lo else np.zeros_like(x, dtype=float)


class HybridSearch:
    """Chunk-level hybrid search over the handbook, deduplicated to doc ids.

    score = alpha * minmax(semantic) + (1 - alpha) * minmax(keyword)
    hs = HybridSearch(); hs.search("Is P-2 running?", k=3) -> ["hydroponics-troubleshooting", ...]
    alpha=1.0 is pure semantic search, alpha=0.0 pure keyword search.
    """

    def __init__(self, alpha: float = 0.5, embed=None, title_prefix: bool = False):
        self.embed = embed or embed_general
        self.chunks = handbook_chunks(title_prefix=title_prefix)
        texts = [c["text"] for c in self.chunks]
        self.doc_ids = [c["doc_id"] for c in self.chunks]
        self.V = self.embed(texts)
        self.kw = KeywordIndex(texts)
        self.alpha = alpha

    def scores(self, query: str) -> np.ndarray:
        sem = self.V @ self.embed(query)
        kw = self.kw.scores(query)
        return self.alpha * _minmax(sem) + (1 - self.alpha) * _minmax(kw)

    def search(self, query: str, k: int = 3) -> list:
        order = np.argsort(-self.scores(query), kind="stable")
        return dedupe(self.doc_ids[i] for i in order)[:k]


# ------------------------------------------------------------------ evaluation harness


def build_testset(include_crew: bool = True) -> list[dict]:
    """Labelled queries as dicts with id, query, doc_ids, type: the answerable handbook
    questions (type "factual" or "multi-hop"), plus the crew queries (type = kind)."""
    out = [{"id": q["id"], "query": q["question"], "doc_ids": list(q["doc_ids"]), "type": q["type"]}
           for q in labelled_questions()]
    if include_crew:
        out += [{"id": q["id"], "query": q["query"], "doc_ids": q["doc_ids"], "type": q["kind"]} for q in crew_queries()]
    return out


def evaluate(search, testset: list[dict], k: int = 3):
    """Run `search(query) -> ranked doc ids` on every test query. Returns a DataFrame with
    one row per query: id, type, rank (of the first relevant doc, NaN if none), hit, recall, rr."""
    import pandas as pd

    rows = []
    for t in testset:
        ranked = list(search(t["query"]))
        rr = reciprocal_rank(ranked, t["doc_ids"])
        rows.append({"id": t["id"], "type": t["type"], "rank": 1 / rr if rr else float("nan"),
                     "hit": hit_at_k(ranked, t["doc_ids"], k), "recall": recall_at_k(ranked, t["doc_ids"], k), "rr": rr})
    return pd.DataFrame(rows)
