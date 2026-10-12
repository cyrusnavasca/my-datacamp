"""Helpers for the llm-apis-prompting course.

Import in pre_code:  from kits.llm_apis_prompting import ...

Every responder here plugs into aikit.FakeClaude(respond=...). They simulate the
behaviour each lesson is about (persona, truncation, in-context learning, format
drift, reasoning, summarising) deterministically, so tests can check outcomes.

    orbit_chat()            first-calls: persona from `system`, memory only from
                            `messages`, long answers that truncate, continuation
                            from a prefilled assistant turn, temperature sampling
    ticket_triager()        prompting: few-shot in-context classification of crew
                            tickets (nearest example wins; recency + majority bias)
    station_math()          prompting: multi-step questions that are only solved
                            when the prompt asks the model to reason first
    incident_extractor()    structured-output: crew ticket -> JSON incident report,
                            with format drift that depends on the prompt
    memory_model()          context-engineering: answers only from what is in the
                            context; summarises transcripts (well or badly)
    WindowedClaude          FakeClaude with a hard context-window limit
"""

from __future__ import annotations

import json
import math
import re

import aikit
from aikit import FakeClaude, VirtualClock, content_words, count_tokens, helios  # noqa: F401  (re-exported for pre_code)

MODEL = "claude-sonnet-5-5"


def _system_and_context(req) -> str:
    return req.system + "\n" + req.context_text


def _last_assistant_prefill(req) -> str | None:
    """Text of a trailing assistant message (a prefill), or None."""
    if req.messages and req.messages[-1]["role"] == "assistant":
        return "".join(b.get("text", "") for b in req.messages[-1]["content"] if b.get("type") == "text")
    return None


def _continue(full: str, prefill: str | None) -> str:
    """Real API behaviour: with a prefilled assistant turn, the reply continues it.

    Matching ignores whitespace, because aikit's truncation drops the leading
    space of a continued chunk (so "cycle." + "Both" must still match "cycle. Both").
    If the prefill isn't a prefix of the full reply, the full reply is returned.
    """
    if prefill is None:
        return full
    i = j = 0
    while j < len(prefill):
        if prefill[j].isspace():
            j += 1
            continue
        while i < len(full) and full[i].isspace():
            i += 1
        if i >= len(full) or full[i] != prefill[j]:
            return full
        i += 1
        j += 1
    rest = full[i:]
    return rest if rest.strip() else "."


# ====================================================================== first-calls

ORBIT_ANSWERS = [
    (r"airlock|eva\b|spacewalk procedure",
     "To cycle airlock AL-1, two crew members must be present and the commander must approve the cycle. "
     "Both spacewalkers finish the EVA prep checklist first, including the oxygen prebreathe. "
     "Check that the inner hatch seal shows green on panel F-2 and stow loose items in the airlock bag. "
     "Lower the pressure to 0.7 bar and hold for 8 minutes as a leak check; abort if it rises by more than 0.01 bar. "
     "Then continue to vacuum, which takes about 25 minutes. To come back in, repressurise to 1.0 bar "
     "and wait for the green light on panel F-2 before opening the inner hatch."),
    (r"prebreathe",
     "Spacewalkers prebreathe 100% oxygen for 2 hours on EVA day."),
    (r"scrubber|co2",
     "CO2 must stay below 0.5%. I raise an alert at 0.4%, and the scrubber beds are swapped every 90 days."),
    (r"water",
     "The water recovery system reclaims about 93% of the station's water into a 2,400 litre tank."),
    (r"hydroponic|plants|lettuce",
     "Hydroponics in Module C runs two watering cycles a day, at 06:00 and 18:00. Lettuce is harvested every 28 days "
     "and tomatoes every 70 days. Normal humidity there is between 60% and 75%, and the pH probe is recalibrated "
     "every week. If plants wilt while the roots are wet, check the root zone pump P-2 first."),
    (r"medical|injur|bleed|burn",
     "For a medical emergency, call the medical officer, Dr. Priya Raman, on channel 3 and bring the patient to the "
     "medical bay in Module A. Stop any bleeding with direct pressure and keep the patient still. For burns, cool the "
     "skin with water from the medical bay sink for 20 minutes. Do not give medication without the medical officer's "
     "approval. If the medical officer is the patient, the commander takes charge and contacts the flight surgeon on "
     "Earth during the next comms window. Every incident is logged in the medical record within 24 hours."),
    (r"power|eclipse|batter",
     "The solar arrays charge the batteries during daylight. Each orbit includes a 36 minute eclipse, and when the "
     "battery charge drops below 30% non-essential loads are shed automatically."),
    (r"fire|smoke",
     "If you see smoke or fire, raise the alarm, put on a mask and close the hatches to the affected module. "
     "Cut power to the module from the nearest panel, then use the CO2 extinguisher. Everyone meets in Module D, "
     "the storm shelter. The commander decides when it is safe to return, after air samples show no combustion products."),
]

NAME_IDEAS = [("Sprout", 2.0), ("Leafy", 1.3), ("Hydra", 0.9), ("Botbot", 0.4), ("Kelp-9", 0.1)]


def _sample(options, temperature, rng):
    if temperature <= 0:
        return max(options, key=lambda o: o[1])[0]
    m = max(l for _, l in options)
    w = [math.exp((l - m) / temperature) for _, l in options]
    r = rng.random() * sum(w)
    for (name, _), wi in zip(options, w):
        r -= wi
        if r <= 0:
            return name
    return options[-1][0]


def orbit_chat() -> callable:
    """ORBIT for the first-calls chapter.

    - Persona comes only from the `system` parameter ("You are ORBIT ...").
    - It remembers your name only if an earlier user turn in `messages` says
      "my name is X": the API is stateless.
    - Some answers are long (over 100 tokens), so a small max_tokens truncates them.
    - A trailing assistant message is continued, like the real API.
    - "Suggest a name ..." samples with `temperature` (0 = always the top choice).
    """

    def respond(req):
        text = req.last_user_text.lower()
        persona = "orbit" in req.system.lower()
        prefill = _last_assistant_prefill(req)
        if re.search(r"who are you|what are you|introduce yourself", text):
            full = ("I'm ORBIT, the station assistant on Helios-7. I answer handbook questions, read sensors and book module time."
                    if persona else "I'm an AI assistant. How can I help you today?")
            return _continue(full, prefill)
        m = re.search(r"my name is ([A-Za-z\u00c0-\u017f-]+)", req.last_user_text, re.I)
        if m:
            return _continue(f"Nice to meet you, {m.group(1)}. " + ("How can I help on Helios-7?" if persona else "How can I help?"), prefill)
        if re.search(r"what('?s| is) my name|who am i\b|do you know my name", text):
            earlier = [" ".join(b.get("text", "") for b in msg["content"] if b.get("type") == "text")
                       for msg in req.messages[:-1] if msg["role"] == "user"]
            for t in reversed(earlier):
                mm = re.search(r"my name is ([A-Za-z\u00c0-\u017f-]+)", t, re.I)
                if mm:
                    return f"Your name is {mm.group(1)}."
            return "I don't know your name. You haven't told me in this conversation."
        if re.search(r"\bsuggest\b.*\bname\b", text):
            return f"How about '{_sample(NAME_IDEAS, req.temperature, req.rng)}'?"
        for pat, ans in ORBIT_ANSWERS:
            if re.search(pat, text):
                return _continue(ans, prefill)
        return "Noted. Anything else I can help with?" if persona else "Sure. Anything else?"

    return respond


def orbit_answer(question: str) -> str:
    """The full (untruncated) answer orbit_chat gives to a handbook question."""
    for pat, ans in ORBIT_ANSWERS:
        if re.search(pat, question.lower()):
            return ans
    return "Noted. Anything else I can help with?"


CREW_QUESTIONS = [
    "How long do spacewalkers prebreathe?",
    "Walk me through the airlock procedure for an EVA.",
    "At what CO2 level do you raise an alert?",
    "What should I do in a medical emergency?",
    "How much water does the station recover?",
    "Give me an overview of the hydroponics routine.",
    "What happens during the eclipse on each orbit?",
    "What do we do if there is a fire?",
]


# ====================================================================== prompting: few-shot triage

CATEGORIES = ["maintenance", "it", "supplies", "scheduling", "medical"]

_ZERO_SHOT_RULES = [  # the model's prior: what it guesses with no examples (about 70% right)
    (r"password|laptop|network|helios-net", "it"),
    (r"medical|check-up|see priya", "medical"),
    (r"\bbook|slot", "scheduling"),
    (r"\bneed|running low|manifest", "supplies"),
    (r"stuck|noise|leak|flicker|stopped working|display|froze|printer|offline", "maintenance"),
]
_SLOT_WORDS = {"module", "panel", "monday", "tuesday", "wednesday", "thursday", "friday", "again", "lab"}


def _prior(ticket: str):
    return next((c for p, c in _ZERO_SHOT_RULES if re.search(p, ticket, re.I)), None)


_EX_TAG = re.compile(r"<ticket>(.*?)</ticket>\s*<category>\s*(\w+)\s*</category>", re.S | re.I)
_EX_LINE = re.compile(r"Ticket:\s*(.+?)\s*\n\s*Category:\s*(\w+)", re.I)


def parse_examples(text: str) -> list[tuple[str, str]]:
    """Few-shot examples found in a prompt, in order: (ticket, category)."""
    found = [(m.start(), m.group(1).strip(), m.group(2).strip().lower()) for m in _EX_TAG.finditer(text)]
    found += [(m.start(), m.group(1).strip(), m.group(2).strip().lower()) for m in _EX_LINE.finditer(text)]
    return [(t, c) for _, t, c in sorted(found)]


def _words(t: str) -> set:
    return {w for w in aikit.content_words(t) if len(w) > 1 and not w.isdigit() and w not in _SLOT_WORDS}


def ticket_triager() -> callable:
    """A model doing in-context classification of crew tickets.

    The ticket to classify is the last <ticket>...</ticket> (or "Ticket: ...") in
    the final user message, or the whole message if neither is present.
    - No examples: a keyword prior (about 70% right; IT display faults and a
      few other phrasings fool it).
    - With examples: if an example covers at least half of the ticket's words,
      it copies that example's label. Ties go to the example nearest the end of
      the prompt (recency bias). Otherwise it uses the prior, and if the prior
      has no idea either, the most common label among the examples (majority bias).
    - Output: <category>x</category> if the prompt uses that tag, otherwise the
      bare label. If the prompt asks it to think first, it writes a short
      <thinking> block first (more tokens, same answer).
    - If the prompt never lists the allowed categories and has no examples, it
      answers in free text.
    """

    def respond(req):
        last = req.last_user_text
        tickets = re.findall(r"<ticket>(.*?)</ticket>", last, re.S)
        line = re.findall(r"Ticket:\s*(.+)", last)
        target = (tickets[-1] if tickets else line[-1] if line else last).strip()
        prompt = req.system + "\n" + req.context_text
        examples = parse_examples(prompt)
        allowed = [c for c in CATEGORIES if re.search(rf"\b{c}\b", prompt.replace(target, ""), re.I)]
        tw = _words(target)
        if not examples and len(allowed) < 3:
            return f"This looks like a request about {target.lower().rstrip('.?!')}. I'd route it to whoever handles that."
        label, best_s = None, 0.0
        for t, c in examples:  # nearest example; ties go to the later one (recency bias)
            s = len(tw & _words(t)) / max(1, len(tw))
            if s >= best_s and s > 0:
                label, best_s = c, s
        if best_s < 0.5:  # no close example: fall back on the prior
            label = _prior(target)
            if label is None and examples:  # still unsure: majority label of the examples
                counts = {}
                for _, c in examples:
                    counts[c] = counts.get(c, 0) + 1
                label = max(counts, key=lambda c: (counts[c], [e[1] for e in examples][::-1].index(c) * -1))
            label = label or "maintenance"
        think = re.search(r"step by step|think (first|before|carefully)|<thinking>", prompt, re.I)
        out = f"<category>{label}</category>" if "<category>" in prompt else label
        if think:
            out = (f"<thinking>The ticket says: \"{target}\". The key words are {', '.join(sorted(tw)[:4])}. "
                   f"That matches the {label} examples best, so the category is {label}.</thinking>\n" + out)
        return out

    return respond


TRIAGE_SYSTEM = ("You triage crew tickets on research station Helios-7. Classify each ticket into exactly one "
                 "category: maintenance, it, supplies, scheduling or medical. Reply with the category inside "
                 "<category></category> tags.")


def examples_block(examples) -> str:
    """Few-shot examples as XML: one <example> per (ticket, category) pair."""
    return "\n".join(f"<example><ticket>{t}</ticket><category>{c}</category></example>" for t, c in examples)


def parse_label(reply: str):
    """The label inside <category> tags, or the bare reply if it is one label, else None."""
    m = re.findall(r"<category>\s*(\w+)\s*</category>", reply)
    lab = (m[-1] if m else reply.strip()).lower()
    return lab if lab in CATEGORIES else None


def triage_accuracy(examples, tickets=None, system: str = TRIAGE_SYSTEM) -> float:
    """Reference scorer: accuracy of ticket_triager on `tickets` (default: the
    60 held-out tickets) with `examples` in the system prompt. Uses its own client."""
    if tickets is None:
        tickets = split_tickets()[1]
    client = FakeClaude(ticket_triager(), clock=VirtualClock())
    sys_prompt = system + ("\n<examples>\n" + examples_block(examples) + "\n</examples>" if examples else "")
    ok = 0
    for r in tickets.itertuples():
        reply = client.messages.create(model=MODEL, max_tokens=50, system=sys_prompt,
                                       messages=[{"role": "user", "content": f"<ticket>{r.text}</ticket>"}]).text
        ok += parse_label(reply) == r.category
    return ok / len(tickets)


def split_tickets():
    """(pool, test): 100 tickets to pick examples from, 60 held-out tickets to score on."""
    df = helios.tickets()
    return df.iloc[:100].reset_index(drop=True), df.iloc[140:200].reset_index(drop=True)


# ====================================================================== prompting: reasoning

STATION_MATH = [
    # (question, correct, snap answer without reasoning, reasoning steps, multi_step)
    ("How many minutes is the AL-1 leak-check hold?", "8", "8", "The procedure says hold for 8 minutes.", False),
    ("How many scrubbers does Helios-7 have?", "2", "2", "SCR-1 and SCR-2: two scrubbers.", False),
    ("The potable tank holds 2400 litres and the crew of 6 uses 15 litres each per day with no recycling. How many full days does the tank last?",
     "26", "160", "6 crew x 15 L = 90 L per day. 2400 / 90 = 26.7, so 26 full days.", True),
    ("A spacewalk starts after a 2 hour prebreathe that begins at 07:30 and lasts the maximum 6.5 hours. At what time must it end?",
     "16:00", "14:00", "Prebreathe ends 07:30 + 2 h = 09:30. 09:30 + 6.5 h = 16:00.", True),
    ("Lettuce is harvested every 28 days and tomatoes every 70 days. If both were harvested today, in how many days are both harvested on the same day again?",
     "140", "98", "LCM of 28 and 70: 28 = 4 x 7, 70 = 10 x 7, LCM = 140.", True),
    ("What is the CO2 alert threshold in percent?", "0.4", "0.4", "ORBIT alerts at 0.4%.", False),
    ("Each of 4 crew books 3 hours of bench time per week and the lab has 2 benches open 10 hours a day, 5 days a week. What percentage of bench time is booked?",
     "12", "30", "Booked: 4 x 3 = 12 h. Available: 2 x 10 x 5 = 100 h. 12 / 100 = 12%.", True),
    ("The eclipse lasts 36 minutes of a 92 minute orbit. How many minutes of sunlight are there per orbit?",
     "56", "56", "92 - 36 = 56 minutes.", False),
    ("Scrubber beds are swapped every 90 days. The last swap was on day 47 of the year. On which day of the year are they swapped next, and the time after that?",
     "137 and 227", "137", "47 + 90 = 137. 137 + 90 = 227.", True),
    ("Oxygen candles each give one crew member 24 hours of oxygen. There are 12 candles and a crew of 6. How many hours do they last for the whole crew?",
     "48", "288", "12 candles x 24 h = 288 crew-hours. Divided by 6 crew = 48 hours.", True),
]


def station_math() -> callable:
    """Answers STATION_MATH questions. Single-step ones are right either way.
    Multi-step ones are only right when the prompt asks for reasoning first
    ("step by step", "think", "<thinking>") or `thinking=` is passed; the
    reasoning costs output tokens (and so latency)."""

    def respond(req):
        q = req.last_user_text
        prompt = req.system + "\n" + req.context_text
        row = next((r for r in STATION_MATH if r[0][:40] in q), None)
        if row is None:
            return "I can only help with Helios-7 station arithmetic."
        _, right, snap, steps, multi = row
        reason = bool(req.extra.get("thinking")) or bool(re.search(r"step by step|think|<thinking>|reason", prompt, re.I))
        tagged = "<answer>" in prompt
        ans = right if reason else snap
        out = f"<answer>{ans}</answer>" if tagged else f"Answer: {ans}"
        if reason:
            pad = " Let me double-check each quantity against the question before answering." * (3 if multi else 1)
            out = f"<thinking>{steps}{pad}</thinking>\n{out}"
        return out

    return respond


# ====================================================================== structured output

_MODULE_RE = re.compile(r"\bmodule\s+([A-F])\b|\bpanel\s+([A-F])-\d", re.I)


def incident_records(n: int | None = None) -> list[dict]:
    """Crew tickets (maintenance and IT) with the gold incident fields."""
    df = helios.tickets()
    df = df[df.category.isin(["maintenance", "it"])].drop_duplicates("text").reset_index(drop=True)
    out = []
    for r in df.itertuples():
        m = _MODULE_RE.search(r.text)
        out.append({"ticket_id": r.ticket_id, "crew": r.crew, "text": r.text,
                    "module": (m.group(1) or m.group(2)).upper() if m else None,
                    "severity": r.priority, "category": r.category})
    return out[:n] if n else out


def _incident_json(rec: dict, spec: str, errors: str) -> dict:
    """What the model 'extracts' from a ticket. Some fields come out wrong unless
    the prompt (or an earlier validation error) says how they should look."""
    text = rec["text"]
    module = rec["module"]
    severity = rec["severity"]
    if severity == "high" and not (re.search(r"\blow\b.*\bnormal\b.*\bhigh\b|\bhigh\b.*\bnormal\b.*\blow\b", spec, re.I)
                                   or "severity" in errors):
        severity = "urgent"  # the model's own word for it
    if module and not (re.search(r"single letter|one letter|letter A", spec, re.I) or "module" in errors):
        module = f"Module {module}"
    summary = re.sub(r"\s+", " ", text).strip().rstrip(".")
    return {"crew": rec["crew"], "module": module, "severity": severity, "summary": summary}


def incident_extractor(noise: bool = True) -> callable:
    """Turns the crew ticket in the last user message into a JSON incident report.

    Format drift (only when `noise` is True), drawn from the client's seeded RNG:
      - prompt never says JSON: a prose answer
      - prompt says JSON loosely: ~35% preamble ("Here is..."), ~35% ```json fences
      - prompt says ONLY JSON / no prose / no markdown: ~15% fences
      - prefilled "{" assistant turn: the reply continues the object, no wrapper
    Field drift (always): severity "urgent" unless the prompt lists low/normal/high;
    module "Module E" unless the prompt asks for a single letter. An earlier
    validation error in the conversation that names the field fixes it too.
    With `tools`, it calls the first tool with the fields as input (never broken
    JSON, but the same field drift applies).
    """
    recs = {r["text"]: r for r in incident_records()}

    def respond(req):
        user_msgs = [m for m in req.messages if m["role"] == "user"]
        first_user = " ".join(b.get("text", "") for b in user_msgs[0]["content"] if b.get("type") == "text") if user_msgs else ""
        rec = next((r for t, r in recs.items() if t in first_user), None)
        if rec is None:
            return "I couldn't find a crew ticket in your message."
        spec = req.system + "\n" + first_user
        tool_text = " ".join(json.dumps(t) for t in req.tools)
        errors = "\n".join(aikit._block_text(b) for m in req.messages[1:] if m["role"] == "user" for b in m["content"])
        fields = _incident_json(rec, spec + "\n" + tool_text, errors)
        if req.tools:
            return {"tool_use": {"name": req.tools[0]["name"], "input": fields}}
        body = json.dumps(fields)
        prefill = _last_assistant_prefill(req)
        if prefill is not None and prefill.strip().startswith("{"):
            return _continue(body, prefill.strip())
        if not re.search(r"\bjson\b", spec + errors, re.I):
            sev = fields["severity"]
            return f"{rec['crew']} reports a {sev}-severity issue: {fields['summary'].lower()}."
        if not noise:
            return body
        strict = re.search(r"\bonly\b.*json|json\b.*\bonly\b|no prose|no markdown|nothing else|no other text|no code fences?", spec + errors, re.I | re.S)
        r = req.rng.random()
        if strict:
            return f"```json\n{body}\n```" if r < 0.15 else body
        if r < 0.35:
            return f"Here is the incident report:\n{body}"
        if r < 0.70:
            return f"```json\n{body}\n```"
        return body

    return respond


# ====================================================================== context engineering

class WindowedClaude(FakeClaude):
    """FakeClaude with a context window: a request whose input tokens plus
    max_tokens exceed `context_window` fails with BadRequestError, like the real
    API's "prompt is too long" error."""

    def __init__(self, respond=None, *, context_window: int = 2000, **kw):
        super().__init__(respond, **kw)
        self.context_window = context_window

    def _create(self, **kw):
        msgs = kw.get("messages") or []
        if msgs:
            n = self._count_input(kw.get("system"), msgs, kw.get("tools") or [])
            mt = kw.get("max_tokens") or 0
            if n + mt > self.context_window:
                self._record(kw.get("model"), len(self.calls), 0, 0, 0, 0, 20, "context_overflow")
                raise aikit.BadRequestError(
                    f"prompt is too long: {n} input tokens + max_tokens {mt} > {self.context_window} token context window")
        return super()._create(**kw)


_KEEP_WORDS = re.compile(r"\b(agreed|decided|scheduled|moved|allergic|never|always|must|locker|password|deadline)\b", re.I)


def _summarise(transcript: str, faithful: bool) -> str:
    lines = [re.sub(r"^\s*(user|assistant|crew|orbit)\s*:\s*", "", l, flags=re.I) for l in transcript.splitlines()]
    sents = [s for l in lines for s in aikit._sentences(l)]
    if faithful:
        keep = [s for s in sents if re.search(r"\d", s) or _KEEP_WORDS.search(s)
                or re.search(r"(?<!^)(?<![.!?] )\b[A-Z][a-z]{2,}\b", s[1:])]
        return "Summary of the earlier conversation: " + " ".join(keep)
    counts: dict[str, int] = {}
    for w in aikit.content_words(" ".join(sents)):
        if len(w) > 4 and not w.isdigit():
            counts[w] = counts.get(w, 0) + 1
    topics = sorted(counts, key=lambda w: (-counts[w], w))[:6]
    return "Summary of the earlier conversation: the crew and ORBIT chatted about " + ", ".join(topics) + " and other station matters."


def memory_model() -> callable:
    """A model that only knows what is in its context window.

    - "Summarise ..." requests: summarises the transcript in the message (or
      in <transcript> tags). If the instruction asks to keep facts, numbers,
      names, dates or decisions, it keeps those sentences verbatim; otherwise it
      writes a vague topic list and drops the details.
    - Questions (ending in "?"): answers with the best-matching sentence from the
      system prompt and earlier messages, or says it doesn't know.
    - Anything else: a short acknowledgement.
    """

    def respond(req):
        last = req.last_user_text
        if re.match(r"\s*(please\s+)?summari[sz]e|\s*write a summary", last, re.I):
            m = re.search(r"<transcript>(.*?)</transcript>", last, re.S)
            transcript = m.group(1) if m else "\n".join(
                aikit._block_text(b) for msg in req.messages[:-1] for b in msg["content"])
            instr = last[: m.start()] if m else last
            faithful = bool(re.search(r"fact|number|name|date|time|decision|detail|exact|verbatim|preserve", instr, re.I))
            return _summarise(transcript, faithful)
        if last.strip().endswith("?"):
            q = set(aikit.content_words(last))
            context = req.system + "\n" + "\n".join(aikit._block_text(b) for msg in req.messages[:-1] for b in msg["content"])
            best, best_s = None, 0.0
            for s in aikit._sentences(context):
                if s.strip().endswith("?"):
                    continue
                sw = set(aikit.content_words(s))
                sc = len(q & sw) / max(1, len(q))
                if sc > best_s:
                    best, best_s = s, sc
            if best is None or best_s < 0.5:
                return "I don't have that information in our conversation."
            return best
        return "Got it."

    return respond


KEY_FACTS = [
    # (turn index of the user message, fact sentence, question, expected substring)
    (2, "The spare scrubber cartridge is stored in locker D-14.", "Which locker holds the spare scrubber cartridge?", "D-14"),
    (7, "Kenji is allergic to penicillin, so note that for the medical bay.", "What is Kenji allergic to?", "penicillin"),
    (13, "We agreed to run the hydroponics grow lights for 16 hours a day.", "How many hours a day do the hydroponics grow lights run?", "16"),
    (20, "The comms window with Meridian Control moved to 14:20 station time.", "When is the comms window with Meridian Control?", "14:20"),
    (27, "Tomas will do the solar array inspection EVA on Thursday.", "Who will do the solar array inspection EVA?", "Tomas"),
]

_CHAT = [
    ("Morning ORBIT, how is everything looking today?", "Good morning. All modules are reporting normal readings."),
    ("The coffee in the galley tastes a bit burnt again.", "Sorry to hear that. I will add a note for the galley crew."),
    (None, "Thanks, I have noted where it is stored."),
    ("Did anyone fix the squeaky hatch near the gym?", "It was oiled yesterday, so it should be quieter now."),
    ("I watched the sunrise from the cupola, it was stunning.", "It sounds beautiful. Sunrises up here never get old."),
    ("Can you remind me to drink more water today?", "Of course. Staying hydrated helps a lot up here."),
    ("The music in the gym was way too loud this morning.", "I will ask the crew to keep the volume lower."),
    (None, "Thank you, I have passed that on to the medical officer."),
    ("How is the weather on Earth looking for the launch site?", "Clear skies are forecast there all week."),
    ("I finally finished that novel about the ocean.", "Nice. Was the ending worth the wait?"),
    ("It was okay, a bit slow in the middle.", "That happens with long books. Maybe the next one will be faster."),
    ("My sleeping bag strap is loose again.", "There are spare straps in the crew quarters cabinet."),
    ("Thanks, that worked fine.", "Glad to hear it."),
    (None, "Understood. I will keep the grow lights on that schedule."),
    ("The lettuce looks really healthy this week.", "The plants are doing well. Kenji will be pleased."),
    ("Is it movie night tonight or tomorrow?", "Movie night is tomorrow evening in the galley."),
    ("I keep losing my pen in zero gravity.", "Velcro on the pen and the wall usually helps."),
    ("Good idea, I will try that.", "Let me know if it works."),
    ("The view of the aurora last night was amazing.", "It must have been quite a sight from orbit."),
    ("I am a bit tired after the long shift.", "Rest well. Your next shift starts after the sleep period."),
    (None, "Thanks, I have updated the communication schedule."),
    ("Is there any chocolate left in storage?", "There is a small supply left, so enjoy it slowly."),
    ("The new crew photo turned out nicely.", "It looks great. The whole crew is smiling."),
    ("My tablet battery drains too fast.", "Try lowering the screen brightness when you read."),
    ("That helped a bit, thank you.", "You are welcome."),
    ("The galley smells like garlic bread today.", "Someone must be cooking something tasty."),
    ("Can you play some quiet music in the lab?", "Playing a calm playlist in the lab now."),
    (None, "Noted. I will add the inspection to the EVA plan."),
    ("I saw a satellite pass by the window earlier.", "Several pass close by each day."),
    ("The exercise bike seat keeps slipping down.", "Tighten the clamp under the seat by hand."),
    ("All good now, the seat holds.", "Great, enjoy your workout."),
    ("I am looking forward to the next resupply.", "It should bring fresh fruit and mail from home."),
    ("Do we have any more puzzle books?", "There are two left on the shelf in Module A."),
    ("I will grab one after dinner.", "Enjoy the puzzles."),
    ("The lights in my quarters flicker at night.", "I have logged it for the next maintenance round."),
    ("Thanks, it is only a little annoying.", "Understood. It is on the list."),
    ("I miss the smell of rain.", "Many crew members say the same thing."),
    ("Okay, I am heading to bed now.", "Good night. Sleep well."),
    ("Good morning again, ORBIT.", "Good morning. Breakfast is ready in the galley."),
    ("Anything new I should know before my shift?", "Nothing urgent. All systems are running normally."),
]


def crew_conversation() -> list[dict]:
    """A 40-exchange (80-message) chat between a crew member and ORBIT. Five
    key facts (KEY_FACTS) are buried in it among a lot of chit-chat."""
    facts = {i: f for i, f, _, _ in KEY_FACTS}
    msgs = []
    for i, (u, a) in enumerate(_CHAT):
        msgs.append({"role": "user", "content": facts.get(i, u)})
        msgs.append({"role": "assistant", "content": a})
    return msgs


def recall_test(client, messages, system: str = "", model: str = MODEL, max_tokens: int = 100) -> float:
    """Ask each KEY_FACTS question after `messages`; return the share answered
    correctly. Does not change `messages`. A request that overflows the
    context window counts as a miss."""
    hits = 0
    for _, _, q, expected in KEY_FACTS:
        try:
            kw = dict(model=model, max_tokens=max_tokens, messages=list(messages) + [{"role": "user", "content": q}])
            if system:
                kw["system"] = system
            r = client.messages.create(**kw)
            hits += expected.lower() in r.text.lower()
        except aikit.BadRequestError:
            pass
    return hits / len(KEY_FACTS)


def station_time(minute: int) -> str:
    """Station clock string for minute `minute` of the day shift (from 08:00)."""
    h, m = divmod(8 * 60 + minute, 60)
    return f"{h:02d}:{m:02d}"


def time_echo() -> callable:
    """For caching lessons: replies with the station time it was told, found
    anywhere in the request ("Station time: HH:MM"), or says it doesn't know."""

    def respond(req):
        m = re.findall(r"station time:?\s*(\d\d:\d\d)", req.system + "\n" + req.context_text, re.I)
        return f"It is {m[-1]} station time." if m else "I don't know the current station time."

    return respond
