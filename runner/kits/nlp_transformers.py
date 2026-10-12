"""Helpers for the nlp-transformers course.

Import in pre_code:  from kits.nlp_transformers import ...

Everything is deterministic (fixed seeds), offline and small. Model loaders
read the two models cached by `npm run setup:models` and silence the
download/progress chatter so the learner's console stays clean.
"""

from __future__ import annotations

import functools
import random
import re

import numpy as np

SENTIMENT_MODEL = "distilbert/distilbert-base-uncased-finetuned-sst-2-english"
GPT2_MODEL = "distilbert/distilgpt2"

# ------------------------------------------------------------------ tickets


def ticket_split(test_size: float = 0.3, seed: int = 0):
    """Helios-7 crew tickets split into (train, test) DataFrames, stratified by category."""
    import aikit
    from sklearn.model_selection import train_test_split

    df = aikit.helios.tickets()
    train, test = train_test_split(df, test_size=test_size, random_state=seed, stratify=df["category"])
    return train.reset_index(drop=True), test.reset_index(drop=True)


_STOP = set("the a an is in on of for my to can i it and with from this that are we have had since be will not at near".split())
_ABBR = {"module": "mod", "please": "pls", "monday": "mon", "tuesday": "tue", "wednesday": "wed",
         "thursday": "thu", "friday": "fri", "password": "pwd"}


def _typo(w: str, rng: random.Random) -> str:
    if len(w) < 4:
        return w
    i = rng.randrange(1, len(w) - 1)
    op = rng.choice(["drop", "double", "swap"])
    if op == "drop":
        return w[:i] + w[i + 1:]
    if op == "double":
        return w[:i] + w[i] + w[i:]
    return w[: i - 1] + w[i] + w[i - 1] + w[i + 1:]


def glove_typed(texts, seed: int = 7, typo_rate: float = 0.9):
    """Rewrite messages the way the crew types them on the new EVA-glove keypads:
    lowercase, filler words dropped, a few abbreviations, and a typo in most words."""
    rng = random.Random(seed)
    out = []
    for text in texts:
        words = [w for w in re.findall(r"[a-z0-9'-]+", str(text).lower()) if w not in _STOP]
        new = []
        for w in words:
            if w in _ABBR:
                w = _ABBR[w]
            elif rng.random() < typo_rate:
                w = _typo(w, rng)
            new.append(w)
        out.append(" ".join(new))
    return out


# ------------------------------------------------------------------ toy embeddings

# Interpretable dimensions for the analogy lesson.
TOY_DIMS = ["royal", "male", "adult", "family", "person", "job", "machine", "food"]
_TOY = {
    #            royal male adult family person job machine food
    "man":      [0.0, 1.0, 1.0, 0.0, 1.0, 0.0, 0.0, 0.0],
    "woman":    [0.0, -1.0, 1.0, 0.0, 1.0, 0.0, 0.0, 0.0],
    "boy":      [0.0, 1.0, -1.0, 0.0, 1.0, 0.0, 0.0, 0.0],
    "girl":     [0.0, -1.0, -1.0, 0.0, 1.0, 0.0, 0.0, 0.0],
    "king":     [1.0, 1.0, 1.0, 0.0, 1.0, 0.3, 0.0, 0.0],
    "queen":    [1.0, -1.0, 1.0, 0.0, 1.0, 0.3, 0.0, 0.0],
    "prince":   [1.0, 1.0, -0.6, 0.0, 1.0, 0.0, 0.0, 0.0],
    "princess": [1.0, -1.0, -0.6, 0.0, 1.0, 0.0, 0.0, 0.0],
    "father":   [0.0, 1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0],
    "mother":   [0.0, -1.0, 1.0, 1.0, 1.0, 0.0, 0.0, 0.0],
    "son":      [0.0, 1.0, -0.6, 1.0, 1.0, 0.0, 0.0, 0.0],
    "daughter": [0.0, -1.0, -0.6, 1.0, 1.0, 0.0, 0.0, 0.0],
    "uncle":    [0.0, 1.0, 1.0, 0.6, 1.0, 0.0, 0.0, 0.0],
    "aunt":     [0.0, -1.0, 1.0, 0.6, 1.0, 0.0, 0.0, 0.0],
    "he":       [0.0, 1.0, 0.0, 0.0, 0.6, 0.0, 0.0, 0.0],
    "she":      [0.0, -1.0, 0.0, 0.0, 0.6, 0.0, 0.0, 0.0],
    # Jobs should be gender-neutral, but the (imaginary) corpus leaked a lean.
    "engineer": [0.0, 0.35, 1.0, 0.0, 1.0, 1.0, 0.2, 0.0],
    "pilot":    [0.0, 0.3, 1.0, 0.0, 1.0, 1.0, 0.1, 0.0],
    "commander": [0.1, 0.4, 1.0, 0.0, 1.0, 1.0, 0.0, 0.0],
    "doctor":   [0.0, 0.2, 1.0, 0.0, 1.0, 1.0, 0.0, 0.0],
    "nurse":    [0.0, -0.4, 1.0, 0.0, 1.0, 1.0, 0.0, 0.0],
    "teacher":  [0.0, -0.25, 1.0, 0.0, 1.0, 1.0, 0.0, 0.0],
    "scientist": [0.0, 0.15, 1.0, 0.0, 1.0, 1.0, 0.0, 0.0],
    "pump":     [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0],
    "valve":    [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0],
    "heater":   [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.1],
    "coffee":   [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0],
    "soup":     [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0],
    "bread":    [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0],
}


def toy_table(noise: float = 0.05, extra_dims: int = 4, seed: int = 0):
    """(words, E): a small embedding table with 8 readable dimensions plus a few noise dimensions."""
    rng = np.random.default_rng(seed)
    words = list(_TOY)
    E = np.array([_TOY[w] for w in words], dtype=float)
    E = E + rng.normal(0, noise, E.shape)
    E = np.hstack([E, rng.normal(0, noise, (len(words), extra_dims))])
    return words, E


# ------------------------------------------------------------------ co-occurrence corpus

CORPUS_GROUPS = {
    "crew": "pilot medic engineer botanist".split(),
    "equipment": "pump valve fan heater".split(),
    "food": "coffee tea soup rice".split(),
    "place": "galley lab gym dock".split(),
}
_TEMPLATES = [
    "the {crew} fixed the {equipment}", "the {equipment} in the {place} broke",
    "the {crew} drank {food} in the {place}", "the {crew} ate {food}", "hot {food} in the {place}",
    "the {crew} checked the {equipment}", "the {crew} went to the {place}",
    "the {equipment} needs a new part", "fresh {food} tastes good",
]


def station_corpus(n: int = 300, seed: int = 0):
    """n short, lowercase station-log sentences built from templates."""
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        t = rng.choice(_TEMPLATES)
        out.append(t.format(**{k: rng.choice(v) for k, v in CORPUS_GROUPS.items()}))
    return out


# ------------------------------------------------------------------ broken similarity search

SEARCH_GROUPS = {
    "equipment": "pump valve fan heater scrubber filter airlock hatch".split(),
    "food": "coffee tea rice soup bread lettuce tomato noodles".split(),
    "medical": "headache rash fever nausea dizziness cough bruise sprain".split(),
    "crew": "commander engineer doctor pilot scientist medic botanist technician".split(),
    "places": "galley lab gym bridge greenhouse storage cupola dock".split(),
    "days": "monday tuesday wednesday thursday friday saturday sunday weekend".split(),
}


def search_table(seed: int = 3, dim: int = 16):
    """(words, groups, freq, E) for the 'broken similarity search' mission.

    The vectors behave like raw trained embeddings: their length grows with
    word frequency, and they all share one large common direction."""
    rng = np.random.default_rng(seed)
    centres = {g: rng.normal(0, 1, dim) for g in SEARCH_GROUPS}
    words, groups, vecs = [], [], []
    for g, ws in SEARCH_GROUPS.items():
        for w in ws:
            words.append(w)
            groups.append(g)
            vecs.append(centres[g] + rng.normal(0, 0.6, dim))
    E = np.array(vecs)
    freq = np.round(np.exp(rng.normal(5, 1.5, len(words)))).astype(int) + 1
    common = rng.normal(0, 1, dim)
    common = common / np.linalg.norm(common) * 20
    scale = np.sqrt(freq) / np.sqrt(freq).mean()
    return words, np.array(groups), freq, E * scale[:, None] + common


# ------------------------------------------------------------------ crew mood messages

_POS = """Thanks for fixing the scrubber so fast, the air feels great.
The new coffee in the galley is fantastic.
Loved the movie night in the cupola, let's do it again.
Huge thanks to Priya for patching my hand, she was brilliant.
The lettuce harvest looks amazing this week.
Docking went perfectly, well done everyone.
Really happy with the new bunk curtains, I finally slept well.
Great job on the solar array repair, power is rock solid now.
The view of the aurora from the cupola was breathtaking today.
Tomas made the best noodle soup I have had in months.
Thank you for swapping my galley duty, I owe you one.
The gym bike works smoothly again, nice work.
My experiment results came out even better than expected.
Lovely chat with my family during the comms window, made my day.
The hydroponics team did a wonderful job with the tomatoes.
Network is fast today, uploads finished in seconds.
Kudos to the night shift for keeping everything calm.
The birthday cake for Noor was a lovely surprise.
So relieved the pressure test passed, great teamwork.
Excellent briefing this morning, very clear and helpful.
I really enjoy working in the new lab layout.
The resupply arrived early and everything was intact, brilliant.
Fresh strawberries from the greenhouse, what a treat.
The medical check-up was quick and friendly, thanks.
Best EVA so far, the suit fit perfectly.
Thanks for the quick password reset, I am back in.
Morale is high after the successful sample return.
The new playlist in the gym is excellent.
Our robotic arm practice run was flawless.
Grateful for everyone's help during the move to Module D.
The quiet hours rule is working nicely, I sleep much better.
Delighted that the water recycler is back to full efficiency.
Brilliant idea to add herbs to the galley menu.
The crew dinner tonight was wonderful.
Happy to report the leak is fixed and the floor is dry.
Smooth comms all week, thank you IT."""

_NEG = """The scrubber failed again and my head is pounding.
I am exhausted, the alarms kept me awake all night.
This is the third time the printer has broken this week, it is ridiculous.
The coffee machine is leaking everywhere and nobody cares.
I am really frustrated that my lab booking was cancelled without warning.
The galley smells terrible after the freezer failure.
Awful night, the fan rattled for hours.
I feel sick and the medical bay was closed.
My experiment was ruined because the heater died.
The network keeps dropping and I lost my report.
Nobody answered my maintenance ticket for five days, unacceptable.
The noise from Module E is driving me crazy.
I am worried about the crack near the hatch seal.
The food has been bland and cold all week.
Lost two days of data because the backup failed.
The new schedule is a mess and I keep missing my gym slot.
I hate how cramped the storage module has become.
My bunk light is broken and I cannot read at night.
The leak is getting worse and the floor is soaked.
Terrible comms today, the call with my family kept cutting out.
I am fed up with the constant valve clicking.
The tomatoes all died, months of work wasted.
The heater broke again and my quarters are freezing.
I am stressed, the deadline is impossible with these outages.
That docking drill was chaotic and badly planned.
My back hurts badly after the cargo transfer.
The water tastes strange and I do not trust it.
Annoyed that someone took the last of the coffee again.
The robotic arm jammed and nearly hit the panel, scary.
The air in the lab feels stale and I keep getting headaches.
Disappointed that the resupply was delayed again.
The gym treadmill is broken and nobody is fixing it.
I am sick of the printer jamming every single time.
Horrible migraine, I could not work today.
The airlock alarm went off for nothing and scared everyone.
The new filters are useless, the dust is everywhere."""

_NEU = """Please book bench 2 in Module B for Thursday.
Cancel my lab booking for Friday.
Where are the spare filters stored?
Please add batteries to the next resupply manifest.
Can I move my exercise slot to the afternoon?
The comms window opens at 14:00 station time.
Reminder that the pressure check is scheduled for Monday.
I need the glovebox on Tuesday morning.
Swap my galley duty on Wednesday with Tomas?
Requesting a routine check-up next week.
What time is the crew briefing tomorrow?
Module C humidity reading is 62 percent.
I will be in the lab until 18:00.
Please send me the updated docking checklist.
The next supply ship is due in nine days.
Moving the sample freezer inventory to the shared drive.
Which channel should I use for the EVA prep call?
Need two more zip ties for the lab.
The water recycler log for today is attached.
Can someone confirm the gym schedule for Saturday?
I am switching my sleep shift to the late rota next week.
Printer in Module A needs a toner refill.
Please update my emergency contact details.
How many sample bags are left in storage?
The robotic arm session is booked for 10:00.
Logging the CO2 reading from Module E at 0.4 percent.
I moved the spare batteries to Module D.
Is the medical bay open on Sunday?
Forwarding the hydroponics schedule for next week.
Please add coffee to the next manifest.
The airlock inspection is due on Friday.
My lab report is uploaded to the shared folder.
What is the password policy for station laptops?
Booking the cupola for a photography session on Thursday.
The new crew roster will be posted tonight.
I will run the filter replacement after lunch."""


def mood_messages():
    """108 crew messages labelled 'positive', 'negative' or 'neutral' (36 each), shuffled with a fixed seed."""
    import pandas as pd

    rows = [(t, "positive") for t in _POS.split("\n")]
    rows += [(t, "negative") for t in _NEG.split("\n")]
    rows += [(t, "neutral") for t in _NEU.split("\n")]
    df = pd.DataFrame(rows, columns=["text", "label"])
    return df.sample(frac=1.0, random_state=0).reset_index(drop=True)


def mood_split(test_size: float = 0.4, seed: int = 0):
    """mood_messages() split into (train, test), stratified by label."""
    from sklearn.model_selection import train_test_split

    df = mood_messages()
    tr, te = train_test_split(df, test_size=test_size, random_state=seed, stratify=df["label"])
    return tr.reset_index(drop=True), te.reset_index(drop=True)


# ------------------------------------------------------------------ pretrained models


def quiet():
    """Silence transformers' warnings and progress bars."""
    import os

    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
    import transformers

    transformers.logging.set_verbosity_error()
    try:
        transformers.utils.logging.disable_progress_bar()
    except AttributeError:
        pass


@functools.lru_cache(maxsize=1)
def sentiment_pipeline():
    """The cached DistilBERT SST-2 sentiment pipeline, pinned to the CPU (pipelines otherwise grab a GPU/MPS device)."""
    quiet()
    from transformers import pipeline

    return pipeline("sentiment-analysis", model=SENTIMENT_MODEL, device="cpu")


@functools.lru_cache(maxsize=1)
def load_sentiment():
    """(tokenizer, model) for DistilBERT SST-2, in eval mode."""
    quiet()
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(SENTIMENT_MODEL)
    model = AutoModelForSequenceClassification.from_pretrained(SENTIMENT_MODEL).eval()
    return tok, model


@functools.lru_cache(maxsize=1)
def load_gpt2():
    """(tokenizer, model) for DistilGPT2, in eval mode."""
    quiet()
    from transformers import AutoModelForCausalLM, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(GPT2_MODEL)
    model = AutoModelForCausalLM.from_pretrained(GPT2_MODEL).eval()
    return tok, model


# ------------------------------------------------------------------ generation helpers

_GEN_CACHE: dict = {}


def continue_text(prompt: str, seed: int = 0, max_new_tokens: int = 40, **settings) -> list[int]:
    """Exactly `max_new_tokens` new DistilGPT2 token ids for `prompt`.

    `settings` go straight to `model.generate` (do_sample, temperature, top_p, top_k,
    repetition_penalty, no_repeat_ngram_size, ...). The torch seed is set to `seed` first, so
    sampled output is reproducible. Results are cached per process."""
    import torch

    key = repr((prompt, seed, max_new_tokens, sorted(settings.items())))
    if not _GEN_CACHE:
        _GEN_CACHE.update(_load_disk_cache())
    if key not in _GEN_CACHE:
        tok, model = load_gpt2()
        enc = tok(prompt, return_tensors="pt")
        torch.manual_seed(seed)
        with torch.no_grad():
            out = model.generate(**enc, max_new_tokens=max_new_tokens, min_new_tokens=max_new_tokens,
                                 pad_token_id=tok.eos_token_id, **settings)
        _GEN_CACHE[key] = out[0, enc["input_ids"].shape[1]:].tolist()
        _save_disk_cache()
    return list(_GEN_CACHE[key])


# Generation is deterministic for a given prompt, seed and settings, so results are also kept in a
# small JSON file in the temp folder. Sequential exercises re-run earlier steps on every submit;
# the file cache makes those re-runs instant.
def _cache_path():
    import os
    import tempfile

    return os.path.join(tempfile.gettempdir(), "my-datacamp-nlp-transformers-gen-cache.json")


def _load_disk_cache() -> dict:
    import json

    try:
        with open(_cache_path()) as fh:
            data = json.load(fh)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _save_disk_cache() -> None:
    import json
    import os

    path = _cache_path()
    tmp = f"{path}.{os.getpid()}.tmp"
    try:
        with open(tmp, "w") as fh:
            json.dump(_GEN_CACHE, fh)
        os.replace(tmp, path)
    except OSError:
        pass


def fluency(prompt: str, new_ids) -> float:
    """Mean negative log-likelihood per new token under DistilGPT2 at temperature 1.

    Lower is more fluent. Greedy text scores about 1, normal sampling about 2-3,
    word salad from a very high temperature 8 or more."""
    import torch

    tok, model = load_gpt2()
    p_ids = tok(prompt)["input_ids"]
    ids = torch.tensor([p_ids + list(new_ids)])
    with torch.no_grad():
        logp = torch.log_softmax(model(ids).logits[0, :-1], dim=-1)
    target = ids[0, 1:]
    nll = -logp[torch.arange(len(target)), target][len(p_ids) - 1:]
    return float(nll.mean())


def repeated_ngram_rate(ids, n: int = 3) -> float:
    """Share of n-grams in `ids` that repeat an earlier n-gram: 1 - unique / total."""
    grams = [tuple(ids[i:i + n]) for i in range(len(ids) - n + 1)]
    return 1 - len(set(grams)) / len(grams) if grams else 0.0
