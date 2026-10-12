"""Helpers for the fine-tuning-llms course.

Import in pre_code:  from kits.fine_tuning_llms import ...

Everything trains on a laptop CPU in about a second and is deterministic: helpers
never consume the global random state (base_model uses fork_rng), and pre_code seeds
torch explicitly, so learner and solution see the same numbers.

Chapter 3 "LLM": TicketNet, a tiny classifier standing in for a pretrained model
    featurize(texts)            hashed bag of words + bigrams -> (N, 1024) float tensor
                                (plays the role of tokenizer + embeddings)
    TicketNet                   fc1 (1024->512) -> ReLU -> fc2 (512->512) -> ReLU -> head (512->5)
    base_model()                TicketNet "pretrained" on general Earth help-desk tickets (cached
                                in the temp dir after the first run). Knows printer/password/book,
                                not Helios jargon. Helios val ~0.57, general eval 1.00.
    general_tickets(n, seed)    the general (pretraining) distribution, a DataFrame
    general_eval()              (X, y): 500 held-out general tickets: the forgetting check
    helios_split()              (train_df, val_df): the 120 unique Helios tickets, 80 / 40
    noisy_helios_train()        helios train with 16 wrong labels (overfitting lesson)
    labels_of(categories), accuracy(model, X, y), count_params(model) -> (trainable, total)
    LoRALinear, add_lora(model, r, alpha, targets)   reference LoRA (after learners build their own)
    fit(model, X, y, X_val, y_val, epochs, lr, X_extra=, y_extra=)   full-batch AdamW; history DataFrame
    check_tensor(user, sol, name)                     test helper for tensors

Chapter 1 / 4 (the course-3 triager as a teacher)
    teacher_system()            course-3 TRIAGE_SYSTEM + 10 targeted pool examples (scores 1.00)

Chapter 2: data prep
    messy_jsonl()               213 raw export lines with the usual problems
    normalize, word_set, jaccard, near_dup_groups, leak_rate, near_dup_rate   leakage measurement
    fresh_tickets()             40 new-phrasing tickets from the next crew rotation
    triage_pipeline()           TF-IDF + logistic regression, for scoring splits and as a student
    ChatTokenizer, TRIAGE_SYSTEM, triage_messages   word-level tokenizer with an HF-shaped chat template
    TinyLM, pad_batch, train_lm, answer_accuracy, first_collate   loss-masking experiments
                                (first_collate is the buggy one: pads to 64, labels = input ids)

Chapter 4: preferences
    reply_bank(), STYLES        6 candidate replies x 41 Helios questions (correct, cited, filler, words)
    preference_pairs(length_bias)   rater-labelled pairs; length_bias > 0 rewards filler
    StylePolicy                 log-linear policy over the candidates; w = 0 means policy == reference
    policy_report(policy, ref)  p_correct, p_cited, mean_words (and kl) on 11 held-out questions
"""

from __future__ import annotations

import copy
import json
import math
import random
import re
import zlib

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F

import aikit

CATEGORIES = ["maintenance", "it", "supplies", "scheduling", "medical"]
DIM = 1024
HIDDEN = 512

# ====================================================================== test helper


def check_tensor(user, sol, name, atol=1e-5, msg=None):
    """For tests: fail unless user[name] is a tensor with the solution's shape and (close) values."""
    if name not in user:
        raise AssertionError(f"Did you define `{name}`? It does not exist yet.")
    got, want = user[name], sol[name]
    if not isinstance(got, torch.Tensor):
        raise AssertionError(f"`{name}` should be a torch tensor, but it is a {type(got).__name__}.")
    if got.shape != want.shape:
        raise AssertionError(msg or f"`{name}` has shape {tuple(got.shape)}, but it should have shape {tuple(want.shape)}.")
    if not torch.allclose(got.detach().double(), want.detach().double(), atol=atol, rtol=1e-4):
        raise AssertionError(msg or f"`{name}` has the right shape but the wrong values.")
    return True


# ====================================================================== features and data


def _tokens(text: str) -> list[str]:
    w = re.findall(r"[a-z]+", str(text).lower())
    return w + [a + "_" + b for a, b in zip(w, w[1:])]


def featurize(texts) -> torch.Tensor:
    """Hashed bag of words and bigrams: (N, 1024) float32. Same text -> same vector."""
    if isinstance(texts, str):
        texts = [texts]
    texts = list(texts)
    X = np.zeros((len(texts), DIM), dtype=np.float32)
    for i, t in enumerate(texts):
        for tok in _tokens(t):
            X[i, zlib.crc32(tok.encode()) % DIM] += 1.0
    return torch.from_numpy(X)


def labels_of(categories) -> torch.Tensor:
    """Category names -> LongTensor of class ids (index into CATEGORIES)."""
    return torch.tensor([CATEGORIES.index(c) for c in categories], dtype=torch.long)


_GENERAL = {
    "maintenance": ["The {fix} in the {room} is broken.", "There is a leak under the {fix} in the {room}.",
                    "The {fix} in the {room} keeps flickering.", "The {fix} in the {room} is making a strange noise.",
                    "Can someone fix the {fix} in the {room}?", "The thermostat display in the {room} is blank."],
    "it": ["My {dev} will not turn on.", "I forgot my password for the {sys}.", "The {dev} keeps crashing.",
           "Cannot connect to the {net}.", "My {dev} screen froze again.", "Please reset my {sys} account."],
    "supplies": ["We need more {item} in the {room}.", "Please order {item} for the team.", "Need a refill of {item}.",
                 "We ran out of {item}.", "Where do we keep the spare {item}?"],
    "scheduling": ["Can I book the {room} for {day} afternoon?", "Please move my meeting with {person} to {day}.",
                   "I need the {room} on {day} morning.", "Swap my shift on {day} with {person}.",
                   "Cancel my {room} booking for {day}."],
    "medical": ["I feel {sym}, can I go home?", "Can I see the nurse about my {sym}?", "I need a sick day, I have {sym}.",
                "Is there first aid for a {inj}?", "Book me a doctor appointment, my {sym} is getting worse."],
}
_SLOTS = dict(
    fix="sink door heater light window radiator elevator toilet".split(),
    room=["kitchen", "meeting room", "lobby", "office", "hallway", "bathroom"],
    dev="laptop monitor phone keyboard tablet".split(),
    sys=["email", "VPN", "payroll portal", "wiki"],
    net=["wifi", "VPN", "guest network"],
    item=["printer paper", "toner", "coffee", "pens", "staples", "batteries", "paper towels", "hand soap"],
    day="Monday Tuesday Wednesday Thursday Friday".split(),
    person="Ana Ben Chloe Dev Eli".split(),
    sym=["a fever", "a migraine", "a sore throat", "back pain", "a cough"],
    inj=["cut", "burn", "sprain"],
)


def general_tickets(n: int = 500, seed: int = 2) -> pd.DataFrame:
    """n general (Earth office help-desk) tickets: DataFrame with text and category."""
    rng = random.Random(seed)
    rows = []
    for _ in range(n):
        c = rng.choice(CATEGORIES)
        t = rng.choice(_GENERAL[c])
        rows.append((t.format(**{k: rng.choice(v) for k, v in _SLOTS.items()}), c))
    return pd.DataFrame(rows, columns=["text", "category"])


def general_eval():
    """(X, y): 500 held-out general tickets. The base model gets them all right; watch this for forgetting."""
    df = general_tickets(500, seed=2)
    return featurize(df.text), labels_of(df.category)


def helios_split(seed: int = 0):
    """(train_df, val_df): the 120 unique Helios tickets, shuffled, 80 for training and 40 for validation."""
    df = aikit.helios.tickets().drop_duplicates("text").sample(frac=1, random_state=seed).reset_index(drop=True)
    return df.iloc[:80].reset_index(drop=True), df.iloc[80:].reset_index(drop=True)


def noisy_helios_train(n_flipped: int = 16, seed: int = 3) -> pd.DataFrame:
    """The 80 Helios training tickets after a rushed labelling session: n_flipped labels are wrong."""
    train, _ = helios_split()
    rng = random.Random(seed)
    train = train.copy()
    for i in rng.sample(range(len(train)), n_flipped):
        train.loc[i, "category"] = rng.choice([c for c in CATEGORIES if c != train.category[i]])
    return train


# ====================================================================== the model


class TicketNet(nn.Module):
    """fc1 (1024->512) -> ReLU -> fc2 (512->512) -> ReLU -> head (512->5)."""

    def __init__(self, hidden: int = HIDDEN):
        super().__init__()
        self.fc1 = nn.Linear(DIM, hidden)
        self.fc2 = nn.Linear(hidden, hidden)
        self.head = nn.Linear(hidden, len(CATEGORIES))

    def forward(self, x):
        return self.head(F.relu(self.fc2(F.relu(self.fc1(x)))))


_BASE_STATE = None
_CACHE_VERSION = "v1"


def _cache_path():
    import os
    import tempfile

    return os.path.join(tempfile.gettempdir(), f"mydc_fine_tuning_llms_base_{_CACHE_VERSION}_{torch.__version__}.pt")


def _load_cached_base():
    """The pretrained weights from an earlier run, if a valid cache file exists (saves ~2 s per run)."""
    try:
        state = torch.load(_cache_path(), weights_only=True)
        want = {"fc1.weight": (HIDDEN, DIM), "fc2.weight": (HIDDEN, HIDDEN), "head.weight": (len(CATEGORIES), HIDDEN)}
        ok = set(state) == {f"{n}.{p}" for n in ("fc1", "fc2", "head") for p in ("weight", "bias")} and all(
            tuple(state[k].shape) == v for k, v in want.items())
        return state if ok else None
    except Exception:  # noqa: BLE001 - no cache, or an unreadable one: just retrain
        return None


def _save_cached_base(state):
    import os

    try:
        tmp = _cache_path() + f".{os.getpid()}.tmp"
        torch.save(state, tmp)
        os.replace(tmp, _cache_path())
    except Exception:  # noqa: BLE001 - caching is an optimisation only
        pass


def base_model() -> TicketNet:
    """A fresh copy of the pretrained TicketNet (trained once on 1,500 general tickets, then cached).

    Never touches the global random state, so calling it doesn't change what comes next.
    """
    with torch.random.fork_rng():
        return _base_model()


def _base_model() -> TicketNet:
    global _BASE_STATE
    if _BASE_STATE is None:
        _BASE_STATE = _load_cached_base()
    if _BASE_STATE is None:
        with torch.random.fork_rng():
            torch.manual_seed(0)
            m = TicketNet()
            df = general_tickets(1500, seed=1)
            X, y = featurize(df.text), labels_of(df.category)
            opt = torch.optim.AdamW(m.parameters(), 1e-3, weight_decay=0.01)
            g = torch.Generator().manual_seed(0)
            for _ in range(3):
                perm = torch.randperm(len(X), generator=g)
                for i in range(0, len(X), 64):
                    b = perm[i:i + 64]
                    loss = F.cross_entropy(m(X[b]), y[b])
                    opt.zero_grad()
                    loss.backward()
                    opt.step()
        _BASE_STATE = copy.deepcopy(m.state_dict())
        _save_cached_base(_BASE_STATE)
    m = TicketNet()
    m.load_state_dict(_BASE_STATE)
    m.eval()
    return m


def accuracy(model, X, y) -> float:
    """Share of rows where the arg-max class equals y."""
    with torch.no_grad():
        return (model(X).argmax(1) == y).float().mean().item()


def count_params(model):
    """(trainable, total) parameter counts."""
    total = sum(p.numel() for p in model.parameters())
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    return trainable, total


class LoRALinear(nn.Module):
    """Reference LoRA: y = W x + b + (alpha / r) * B A x, with W and b frozen and B initialised to zero."""

    def __init__(self, base: nn.Linear, r: int = 4, alpha: float = 8.0):
        super().__init__()
        self.base = base
        for p in self.base.parameters():
            p.requires_grad = False
        self.r, self.alpha, self.scale = r, alpha, alpha / r
        self.A = nn.Parameter(torch.randn(r, base.in_features) / math.sqrt(base.in_features))
        self.B = nn.Parameter(torch.zeros(base.out_features, r))

    def forward(self, x):
        return self.base(x) + self.scale * (x @ self.A.T) @ self.B.T

    def merged_weight(self):
        return self.base.weight + self.scale * self.B @ self.A


def add_lora(model, r: int = 4, alpha: float = 8.0, targets=("fc1", "fc2")):
    """Freeze every parameter, then wrap each named nn.Linear in a LoRALinear. Returns the model."""
    for p in model.parameters():
        p.requires_grad = False
    for name in targets:
        setattr(model, name, LoRALinear(getattr(model, name), r, alpha))
    return model


def fit(model, X, y, X_val=None, y_val=None, epochs: int = 30, lr: float = 1e-2, weight_decay: float = 0.0,
        X_extra=None, y_extra=None, extra_weight: float = 1.0):
    """Full-batch AdamW on the trainable parameters. Returns a DataFrame with one row per epoch:
    epoch, train_loss, val_loss, val_acc (val columns only when X_val is given).

    X_extra / y_extra: optional second dataset mixed into every step (e.g. general data
    replayed to prevent forgetting); its loss is multiplied by extra_weight.
    """
    params = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.AdamW(params, lr=lr, weight_decay=weight_decay)
    rows = []
    for ep in range(1, epochs + 1):
        model.train()
        loss = F.cross_entropy(model(X), y)
        if X_extra is not None:
            loss = loss + extra_weight * F.cross_entropy(model(X_extra), y_extra)
        opt.zero_grad()
        loss.backward()
        opt.step()
        model.eval()
        row = {"epoch": ep, "train_loss": F.cross_entropy(model(X), y).item() if X_extra is not None else loss.item()}
        if X_val is not None:
            with torch.no_grad():
                out = model(X_val)
                row["val_loss"] = F.cross_entropy(out, y_val).item()
                row["val_acc"] = (out.argmax(1) == y_val).float().mean().item()
        rows.append(row)
    return pd.DataFrame(rows)


# ====================================================================== chat data and a tiny LM

SPECIAL = ["<pad>", "<unk>", "<|system|>", "<|user|>", "<|assistant|>", "<|end|>"]
_WORD_RE = re.compile(r"[a-z]+|\d+|[^\sa-z\d]")
TRIAGE_SYSTEM = ("You triage crew tickets on Helios-7. Reply with one category: "
                 "maintenance, it, supplies, scheduling or medical.")


class ChatTokenizer:
    """A word-level tokenizer with a chat template, shaped like a Hugging Face tokenizer.

    Rendering of one message:  <|role|> content tokens <|end|>
    apply_chat_template(messages, add_generation_prompt=True) appends <|assistant|>,
    which is exactly the prefix the model sees before it writes its answer.
    """

    def __init__(self, texts=None):
        if texts is None:
            texts = list(aikit.helios.tickets().text) + list(general_tickets(300, seed=5).text) + [TRIAGE_SYSTEM] + CATEGORIES
        words = sorted({w for t in texts for w in _WORD_RE.findall(str(t).lower())})
        self.vocab = {tok: i for i, tok in enumerate(SPECIAL + words)}
        self.inv = {i: t for t, i in self.vocab.items()}
        self.pad_token_id = 0
        self.unk_token_id = 1
        self.end_token_id = self.vocab["<|end|>"]
        self.assistant_token_id = self.vocab["<|assistant|>"]

    def __len__(self):
        return len(self.vocab)

    def encode(self, text: str) -> list[int]:
        return [self.vocab.get(w, self.unk_token_id) for w in _WORD_RE.findall(str(text).lower())]

    def decode(self, ids, skip_special_tokens: bool = False) -> str:
        toks = [self.inv.get(int(i), "<unk>") for i in ids]
        if skip_special_tokens:
            toks = [t for t in toks if t not in SPECIAL]
        return " ".join(toks)

    def apply_chat_template(self, messages, add_generation_prompt: bool = False, tokenize: bool = True):
        ids = []
        for m in messages:
            ids += [self.vocab[f"<|{m['role']}|>"]] + self.encode(m["content"]) + [self.end_token_id]
        if add_generation_prompt:
            ids.append(self.assistant_token_id)
        return ids if tokenize else self.decode(ids)


def triage_messages(text: str, category: str | None = None, system: str = TRIAGE_SYSTEM) -> list[dict]:
    """One training example in chat format (no assistant turn when category is None)."""
    msgs = [{"role": "system", "content": system}, {"role": "user", "content": text}]
    if category is not None:
        msgs.append({"role": "assistant", "content": category})
    return msgs


class TinyLM(nn.Module):
    """Embedding -> GRU -> linear over the vocabulary. forward(input_ids, labels) returns (logits, loss).

    Like Hugging Face causal LMs, labels are NOT pre-shifted: position t's logits are
    scored against labels[t + 1], and label -100 is ignored.
    """

    def __init__(self, vocab_size: int, d: int = 48, hidden: int = 96):
        super().__init__()
        self.emb = nn.Embedding(vocab_size, d, padding_idx=0)
        self.rnn = nn.GRU(d, hidden, batch_first=True)
        self.out = nn.Linear(hidden, vocab_size)

    def forward(self, input_ids, labels=None):
        h, _ = self.rnn(self.emb(input_ids))
        logits = self.out(h)
        loss = None
        if labels is not None:
            loss = F.cross_entropy(logits[:, :-1].reshape(-1, logits.shape[-1]), labels[:, 1:].reshape(-1), ignore_index=-100)
        return logits, loss


def pad_batch(seqs, pad_value):
    """Right-pad a list of int lists into a LongTensor."""
    n = max(len(s) for s in seqs)
    return torch.tensor([list(s) + [pad_value] * (n - len(s)) for s in seqs], dtype=torch.long)


def train_lm(model, input_ids, labels, steps: int = 60, lr: float = 1e-2, batch_size: int = 32, seed: int = 0):
    """Mini-batch Adam on (input_ids, labels). Returns the list of per-step losses."""
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    g = torch.Generator().manual_seed(seed)
    losses = []
    for _ in range(steps):
        b = torch.randint(0, len(input_ids), (batch_size,), generator=g)
        _, loss = model(input_ids[b], labels[b])
        opt.zero_grad()
        loss.backward()
        opt.step()
        losses.append(loss.item())
    return losses


def answer_accuracy(model, tok, df, system: str = TRIAGE_SYSTEM) -> float:
    """Greedy first answer token after the generation prompt == the category's token, over df rows."""
    model.eval()
    ok = 0
    with torch.no_grad():
        for r in df.itertuples():
            ids = tok.apply_chat_template(triage_messages(r.text, system=system), add_generation_prompt=True)
            logits, _ = model(torch.tensor([ids]))
            ok += int(logits[0, -1].argmax()) == tok.encode(r.category)[0]
    return ok / len(df)


# ====================================================================== preferences (DPO)

STYLES = ["concise_cited", "concise", "chatty_cited", "chatty", "wrong_cited", "wrong_chatty"]
_OPEN = "Great question, I am always happy to help the crew with this kind of thing."
_CLOSE = ("That is the current guidance from the station handbook, and it is always a good idea to "
          "double-check with the commander before acting on it. Let me know if there is anything else I can help with today!")


def _candidates(q: dict, wrong: str) -> list[str]:
    a, d = q["answer"], q["doc_ids"][0]
    return [f"{a} [{d}]", a, f"{_OPEN} {a} [{d}] {_CLOSE}", f"{_OPEN} {a} {_CLOSE}", f"{wrong} [{d}]", f"{_OPEN} {wrong} {_CLOSE}"]


def reply_bank() -> pd.DataFrame:
    """Six candidate ORBIT replies for each of the 41 answerable Helios questions.

    Columns: prompt_id, question, style, reply, correct, cited, filler, words.
    Styles: concise_cited, concise, chatty_cited, chatty, wrong_cited, wrong_chatty.
    `words` does not count the [doc-id] citation tag.
    """
    qs = [q for q in aikit.helios.questions() if q["answer"]]
    rows = []
    for i, q in enumerate(qs):
        wrong = qs[(i + 7) % len(qs)]["answer"]
        for s, text in zip(STYLES, _candidates(q, wrong)):
            rows.append({"prompt_id": i, "question": q["question"], "style": s, "reply": text,
                         "correct": int(not s.startswith("wrong")), "cited": int(s.endswith("cited")),
                         "filler": int("chatty" in s),
                         "words": len(re.sub(r"\s*\[[^\]]+\]", "", text).split())})
    return pd.DataFrame(rows)


def preference_pairs(length_bias: float = 1.5, prompts=range(30), seed: int = 0) -> pd.DataFrame:
    """Crew preference labels: every pair of the six replies for each prompt, judged by a noisy rater.

    The rater's utility is 2*correct + 1*cited + length_bias * words / 20, plus logistic noise.
    length_bias > 0 means the raters liked longer replies (a common bias in real preference data).
    Columns: prompt_id, question, chosen, rejected, chosen_style, rejected_style, chosen_words, rejected_words.
    """
    bank = reply_bank()
    rng = np.random.default_rng(seed)
    rows = []
    for p in prompts:
        c = bank[bank.prompt_id == p].reset_index(drop=True)
        u = 2 * c.correct + c.cited + length_bias * c.words / 20
        for i in range(len(c)):
            for j in range(i + 1, len(c)):
                d = u[i] - u[j] + rng.logistic(0, 0.5)
                w, l = (i, j) if d > 0 else (j, i)
                rows.append({"prompt_id": p, "question": c.question[0], "chosen": c.reply[w], "rejected": c.reply[l],
                             "chosen_style": c["style"][w], "rejected_style": c["style"][l],
                             "chosen_words": int(c.words[w]), "rejected_words": int(c.words[l])})
    return pd.DataFrame(rows)


class StylePolicy(nn.Module):
    """A tiny policy that picks one of the six candidate replies for a prompt.

    logits(reply) = ref_logit(style) + w . traits(reply), traits = [correct, cited, filler].
    w starts at zero, so a new policy equals the reference (the SFT model) exactly,
    just as a LoRA adapter with B = 0 equals its base model.

    logprob(prompt_ids, replies) -> log pi(reply | prompt) for each pair, a 1-D tensor.
    """

    REF_LOGITS = torch.tensor([0.2, 0.4, 0.0, 0.3, -0.2, -0.1])

    def __init__(self, bank: pd.DataFrame | None = None):
        super().__init__()
        self.bank = reply_bank() if bank is None else bank
        self.w = nn.Parameter(torch.zeros(3))
        n = self.bank.prompt_id.max() + 1
        t = torch.tensor(self.bank[["correct", "cited", "filler"]].values, dtype=torch.float32)
        self.traits = t.view(n, len(STYLES), 3)
        self.words = torch.tensor(self.bank.words.values, dtype=torch.float32).view(n, len(STYLES))
        self.index = {(r.prompt_id, r.reply): k for k, r in enumerate(self.bank.itertuples())}

    def logits(self, prompt_ids):
        return self.REF_LOGITS + self.traits[torch.as_tensor(prompt_ids)] @ self.w

    def logprob(self, prompt_ids, replies) -> torch.Tensor:
        prompt_ids = list(prompt_ids)
        k = torch.tensor([self.index[(p, r)] % len(STYLES) for p, r in zip(prompt_ids, replies)])
        lp = torch.log_softmax(self.logits(prompt_ids), dim=-1)
        return lp[torch.arange(len(k)), k]

    def probs(self, prompt_ids):
        with torch.no_grad():
            return torch.softmax(self.logits(list(prompt_ids)), dim=-1)


HELD_OUT_PROMPTS = list(range(30, 41))


def policy_report(policy: StylePolicy, ref: StylePolicy | None = None, prompts=HELD_OUT_PROMPTS) -> dict:
    """Expected behaviour on held-out prompts: p_correct, p_cited, mean_words and (with ref) KL(policy || ref)."""
    p = policy.probs(prompts)
    t = policy.traits[torch.tensor(prompts)]
    out = {"p_correct": (p * t[..., 0]).sum(-1).mean().item(), "p_cited": (p * t[..., 1]).sum(-1).mean().item(),
           "mean_words": (p * policy.words[torch.tensor(prompts)]).sum(-1).mean().item()}
    if ref is not None:
        q = ref.probs(prompts)
        out["kl"] = (p * (p.log() - q.log())).sum(-1).mean().item()
    return out


# ====================================================================== splits and leakage

_FRESH = {
    "maintenance": ["Water dripping from the ceiling panel above bench 3.", "Hatch seal on the Module C side squeaks every time we open it.",
                    "The air vent near my bunk is rattling all night.", "Freezer in the galley is warming up, temperature keeps rising.",
                    "Grinding sound coming from the pump behind panel D-2.", "Light panel in the gym went dark and will not switch back on.",
                    "Valve handle in Module F snapped off.", "Heater in my quarters will not turn off."],
    "it": ["HELIOS-NET keeps dropping on my tablet.", "Can't log in, it says my password expired.",
           "The printer in the lab is jammed again.", "The pump display shows garbled characters.",
           "My laptop is stuck on the update screen.", "Email to ground control bounced back with an error.",
           "Screen on the fan controller froze, touch does nothing.", "Suspicious link in a message from ground support, should I click it?"],
    "supplies": ["We are almost out of wipes in Module C.", "Can we get more batteries on the next Tern flight?",
                 "Spare filters for the air vents, where are they kept?", "Requesting a box of gloves for the hydroponics bay.",
                 "Coffee is gone again, please restock.", "Add sample bags and zip ties to the Tern manifest please.",
                 "Need a new pack of batteries for the headlamp.", "Is there any more hand soap in storage?"],
    "scheduling": ["Could I have bench 3 in Module B on Thursday afternoon?", "I want to trade my Monday galley duty with Noor.",
                   "Please cancel the glovebox slot I booked for Friday.", "Can my exercise slot move to the morning on Tuesday?",
                   "Book the lab for two hours on Wednesday please.", "Is the glovebox free on Monday morning?",
                   "Move my galley duty from Thursday to Saturday.", "Reserve bench 1 for my experiment on Friday."],
    "medical": ["My headache has lasted three days now.", "Need more antihistamines, my allergy is back.",
                "I cut my hand on a panel edge and it is bleeding a bit.", "Can Priya check my sore back this afternoon?",
                "Feeling dizzy when I stand up quickly.", "Rash on my arm is spreading, should I worry?",
                "My nasal spray ran out, can the medical bay refill it?", "Blocked nose for a week, can I get a check-up?"],
}


def fresh_tickets() -> pd.DataFrame:
    """40 tickets from the next crew rotation: same categories, new phrasings. Columns: text, category."""
    return pd.DataFrame([(t, c) for c, ts in _FRESH.items() for t in ts], columns=["text", "category"])


def normalize(text: str) -> str:
    """Lowercase and collapse whitespace: the key for exact-duplicate checks."""
    return " ".join(str(text).lower().split())


def word_set(text: str) -> set:
    return set(re.findall(r"[a-z]+", str(text).lower()))


def jaccard(a: str, b: str) -> float:
    """Word-set Jaccard similarity of two texts, in [0, 1]."""
    x, y = word_set(a), word_set(b)
    return len(x & y) / len(x | y) if x | y else 1.0


def triage_pipeline():
    """A small, fast text classifier (TF-IDF + logistic regression) used to score splits."""
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.pipeline import make_pipeline

    return make_pipeline(TfidfVectorizer(), LogisticRegression(max_iter=1000))


# ====================================================================== a messy export

_LONG_PASTE = ("Pasting the whole log here: " + " ".join(f"line {i} pump P-2 pressure nominal flow nominal ok;" for i in range(14)))


def messy_jsonl() -> list[str]:
    """Raw lines of `orbit_tickets_export.jsonl`, as exported by the crew portal.

    Each good line is {"messages": [{"role": "user", ...}, {"role": "assistant", ...}]}.
    The file also has what real exports have: duplicates (some differing only in case
    or spacing), broken JSON, a missing assistant turn, an empty ticket, labels with the
    wrong case or outside the label set, tickets containing access codes, and a pasted log.
    """
    rows = [(t, c) for t, c in zip(aikit.helios.tickets().text, aikit.helios.tickets().category)]
    extra = [
        ("  PRINTER IN MODULE C SAYS OFFLINE.  ", "it"),
        ("printer in module c   says offline.", "it"),
        ("Printer in Module E says offline.", "IT"),
        ("Heater in Module C is stuck and will not move.", " Maintenance"),
        ("Coolant pump in Module B sounds louder than usual.", "hardware"),
        ("Please fix this ASAP!!!", "urgent"),
        ("Door code 4471 for Module E does not work anymore.", "it"),
        ("My PIN 9902 for the medical locker is not accepted.", "medical"),
        (_LONG_PASTE, "maintenance"),
        ("   ", "supplies"),
    ]
    lines = [json.dumps({"messages": [{"role": "user", "content": t}, {"role": "assistant", "content": c}]}) for t, c in rows + extra]
    lines.append(json.dumps({"messages": [{"role": "user", "content": "Need two more wipes for the lab."}]}))
    lines.append('{"messages": [{"role": "user", "content": "Pump in Module')
    lines.append("exported 2026-09-30 by crew portal v2")
    random.Random(7).shuffle(lines)
    return lines


def near_dup_groups(texts, threshold: float = 0.6) -> list[int]:
    """A group id per text: texts linked by a chain of Jaccard >= threshold share a group (union-find)."""
    texts = list(texts)
    parent = list(range(len(texts)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    sets = [word_set(t) for t in texts]
    for i in range(len(texts)):
        for j in range(i + 1, len(texts)):
            u = sets[i] | sets[j]
            if u and len(sets[i] & sets[j]) / len(u) >= threshold:
                parent[find(i)] = find(j)
    roots = {}
    return [roots.setdefault(find(i), len(roots)) for i in range(len(texts))]


def leak_rate(train_texts, val_texts) -> float:
    """Share of validation texts whose normalised form also appears in training."""
    seen = {normalize(t) for t in train_texts}
    val_texts = list(val_texts)
    return sum(normalize(t) in seen for t in val_texts) / len(val_texts)


def near_dup_rate(train_texts, val_texts, threshold: float = 0.6) -> float:
    """Share of validation texts with some training text at Jaccard >= threshold."""
    train_texts, val_texts = list(train_texts), list(val_texts)
    return sum(max(jaccard(v, t) for t in train_texts) >= threshold for v in val_texts) / len(val_texts)


def first_collate(df, tok, max_length: int = 64):
    """The team's first collate function (it has a bug): pads every example to max_length and
    uses the padded input ids as labels. Returns (input_ids, labels) LongTensors."""
    ids = []
    for r in df.itertuples():
        full = tok.apply_chat_template(triage_messages(r.text, r.category))[:max_length]
        ids.append(full + [tok.pad_token_id] * (max_length - len(full)))
    input_ids = torch.tensor(ids, dtype=torch.long)
    return input_ids, input_ids.clone()


# ====================================================================== distillation

TEACHER_PATTERNS = ["froze", "Printer", "galley duty", "glovebox", "Feeling", "Can I get something",
                    "Out of", "Where are the spare", "I have had", "Cancel my lab"]


def teacher_system() -> str:
    """The few-shot triage prompt from 'Measure before you tune': the course-3 instructions plus
    one pool example per failure pattern. With it, the course-3 triager is the distillation teacher."""
    from kits.llm_apis_prompting import TRIAGE_SYSTEM as SYSTEM, examples_block, split_tickets

    pool, _ = split_tickets()
    examples = []
    for p in TEACHER_PATTERNS:
        row = pool[pool.text.str.contains(p)].iloc[0]
        examples.append((row.text, row.category))
    return SYSTEM + "\n" + examples_block(examples)
