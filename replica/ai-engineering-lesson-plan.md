# AI Engineering track: lesson plan

Status: proposal, 2026-10-06. Nothing in `content/` has been changed yet.
Read this with `content/README.md` (the file format) and `.claude/agents/lesson-builder.md`.

## ⚠ Important: go deeper than the surface

Lessons must not stop at "here is what X is and how to call it". Learners should finish each chapter able to **make decisions** and **fix things when they break**. Every lesson in this track has to meet this bar:

1. **How it works underneath.** Show the mechanism, not just the API, e.g. why cosine needs normalised vectors, or what a cache hit actually skips. Build it by hand once before using the library.
2. **Trade-offs, made explicit.** When there's more than one way to do something, compare the options on quality, latency, cost, complexity and failure modes, and say when each one wins. Examples: small vs large chunks, brute force vs HNSW, prompt vs RAG vs fine-tune, agent vs fixed workflow, LLM judge vs code check. A trade-off slide (options × criteria table) plus at least one exercise that asks "given these constraints, which do you choose and why?" (`mc` with feedback on every option, or `classify`).
3. **Troubleshooting common problems.** Every chapter includes at least one problem-solving lesson or boss exercise following this loop:

   **Symptom → Measure → Diagnose → Fix (choose among options) → Verify.**

   The learner gets a *broken or underperforming* system, measures it with a real metric, finds the cause, applies a fix and proves the metric improved. Tests check the metric moved past a threshold, not that specific code was written.

Problems each course must cover (at minimum):

| Course | Symptom | Measure with | Common fixes and their trade-offs |
|---|---|---|---|
| llm-apis-prompting | Output format breaks / invalid JSON | Parse-success rate over N calls | Clearer format spec, examples, prefill, tool-use-as-schema, validate-and-retry (cost of retries) |
| llm-apis-prompting | Context overflow / model "forgets" | Token counts per section, fact-recall test | Trimming, summarising/compaction, retrieval instead of stuffing (lossy vs costly) |
| embeddings-vector-search | Search is slow at scale | Query latency vs N, recall vs brute force | ANN index (HNSW/IVF), quantisation, dimensionality reduction (speed vs recall vs memory) |
| embeddings-vector-search | Relevant docs not found | recall@k, MRR on a labelled set | Hybrid keyword + vector, better embedding model, query rewriting |
| rag-systems | **Chunking is poor** (answers miss info split across chunks, or chunks full of noise) | recall@k per chunking config; inspect retrieved chunks for failed questions; answer F1 | Change chunk size, add overlap, split on structure (headings/sentences), parent-document retrieval, add metadata/titles to chunks (bigger chunks = more context but noisier retrieval and higher cost) |
| rag-systems | Hallucinated or unsupported answers | Citation-support rate, faithfulness judge | Grounding instructions, citations required, refusal threshold, reranking (more refusals vs more wrong answers) |
| rag-systems | Is it retrieval or generation that fails? | Check "was the gold doc retrieved?" separately from "was the answer right?" | Route the fix to the right stage |
| agents-tool-use | Agent loops or wanders | Steps per task, repeated-call rate, task success | Better tool descriptions, step caps, planning, a fixed workflow instead of an agent |
| agents-tool-use | Wrong tool chosen | Tool-selection accuracy on a labelled set | Clearer names/descriptions, fewer overlapping tools, examples |
| mcp-integrations | Client and server disagree / calls fail | Conformance transcript, error codes | Capability negotiation, schema validation, protocol vs tool-level errors |
| llm-evaluation | Judge disagrees with humans | Cohen's κ vs human labels | Binary rubric items, examples in the judge prompt, swap order for pairwise, stronger judge model (cost) |
| llm-evaluation | "v2 looks better" but is it? | Bootstrap CI, per-category breakdown | Bigger/stratified test set, report intervals not points |
| ai-security-guardrails | Untrusted content triggers leaks or unsafe actions | Leak rate and unsafe-action rate on the provided evaluation harness, plus the over-blocking rate on benign requests | Datamarking/delimiting, privilege separation, least-privilege tools, human approval (security vs usability, both measured) |
| llmops-production | **Latency is high** | p50/p95 per span from traces; time-to-first-token vs total time | Streaming (perceived latency), smaller/faster model or routing, prompt caching, shorter prompts and outputs, parallel tool/retrieval calls, response caching (quality vs speed vs cost) |
| llmops-production | Cost is too high | Cost per task, cost breakdown by span | Caching, model routing/cascades, batching, trimming context (savings vs accuracy, measured on the eval set) |
| llmops-production | Errors / 429s under load | Error rate by type | Backoff with jitter, rate limiter, fallbacks, timeouts |
| fine-tuning-llms | Fine-tune overfits or forgets | Train vs val loss, eval on held-out general tasks | Less epochs, lower LoRA rank, more/diverse data, mixing in general data |

Slides for these lessons should read like an engineer's playbook ("When you see X, first check Y, the usual causes are A/B/C, try these in this order"), not a glossary.

## 1. What the market wants (October 2026)

Job-posting analyses and hiring-manager surveys from 2026 mostly agree. Ranked by how often the skill appears and how scarce it is:

| # | Skill | Signal | Where it's taught here |
|---|---|---|---|
| 1 | Python + LLM APIs, model fluency | Python is in ~62% of AI postings; "foundation models" in ~51% | llm-apis-prompting |
| 2 | Evaluation (golden sets, error analysis, LLM-as-judge) | Called the rarest and most-requested skill. Hiring managers name it as the biggest gap; it carries a reported ~$30K salary premium | llm-evaluation, threaded through all courses |
| 3 | Agents and orchestration | Best-paid skill; managers test failure modes and "when NOT to use an agent" | agents-tool-use |
| 4 | RAG + vector search, with measured recall | Red flag: "implemented RAG" with no recall numbers | embeddings-vector-search, rag-systems |
| 5 | MCP (Model Context Protocol) | Called the de facto standard for agent-tool connections; a red flag is not knowing the spec version | **new** mcp-integrations |
| 6 | Production observability, LLMOps | "Plenty of people train models in notebooks; can't find people who deploy them" | **new** llmops-production |
| 7 | Cost and latency optimisation | Managers test caching, routing and per-task economics | llmops-production, context engineering |
| 8 | Safety, guardrails, AI security | OWASP LLM Top 10, prompt injection, excessive agency | **new** ai-security-guardrails |
| 9 | Context and prompt engineering | System prompts, caching, few-shot, tool descriptions | llm-apis-prompting |
| 10 | Fine-tuning (LoRA, preference tuning) | In most "top skills" lists, but needed less often than 1-9 | **new** fine-tuning-llms |
| — | Multimodal, computer use | Rising, but niche for now | future course (see §8) |

Theme across every source: **breadth plus proof**. Employers want one deployed, measured system more than any single tool. That's why the track ends in a capstone, and every course after RAG reports a number (recall, judge agreement, cost per task).

## 2. Changes to the current track

The current track has 8 courses, all with empty `lessons:` lists, so no ids have been used and restructuring is still free.

- **Keep:** deep-learning-pytorch, nlp-transformers, embeddings-vector-search, rag-systems, llm-evaluation.
- **Revise:**
  - llm-apis-prompting: replace `production-basics` with `context-engineering`; production topics move to LLMOps.
  - agents-tool-use: add an agent-patterns/multi-agent chapter; guardrails stays, but the deeper security material moves to its own course.
- **Add:** mcp-integrations, ai-security-guardrails, llmops-production, fine-tuning-llms, ai-engineering-capstone.
- **Move:** mlops-model-serving (classic ML; its prerequisite is supervised-learning) to the end of the Data Science & ML track. llmops-production replaces it here.

New order (`content/tracks/ai-engineering.yaml`):

```yaml
courses:
- deep-learning-pytorch        # foundations
- nlp-transformers
- llm-apis-prompting           # building with LLMs
- embeddings-vector-search
- rag-systems
- agents-tool-use              # agents
- mcp-integrations
- llm-evaluation               # quality and safety
- ai-security-guardrails
- llmops-production            # shipping
- fine-tuning-llms
- ai-engineering-capstone
```

## 3. The story: Helios-7

Every LLM course (3-12) uses one fictional world, so skills build on each other and the capstone feels earned.

> You are the first AI engineer on **Helios-7**, a research station in orbit. The crew wants **ORBIT**, an assistant that answers from the station handbook, reads sensors, books lab modules and messages crew. It must never open an airlock without a human saying yes.

Why this world works:
- **RAG:** a corpus of about 40 short handbook docs (airlock procedure, hydroponics schedule, medical bay, incident reports) with real near-duplicates and contradictions. Retrieval has to be good to get answers right.
- **Agents:** tools range from harmless (`get_sensor`, `crew_roster`) to risky (`send_message`) to dangerous (`open_airlock`). That gives a natural ladder for permissions and human approval.
- **Security:** a "maintenance log" doc can carry an indirect prompt injection.
- **Evaluation:** crew questions with gold answers, plus logged traces of ORBIT failing.
- **Fun:** missions, a hostile "rogue log" antagonist and stakes ("the hydroponics bay floods if this tool loops").

Data lives in `content/datasets/helios/` (handbook `.md`, `questions.jsonl`, `traces.jsonl`, `tickets.csv`), all original, total size under 1 MB.

## 4. Shared infrastructure (build before any lessons)

Exercises run offline with no API keys. Writing a new fake client in every `pre_code` would drift, so add one shared module.

**`runner/aikit.py`**, importable from every exercise:
- `FakeClaude`: same shape as the `anthropic` SDK, so the code learners write transfers to the real thing.
  - `client.messages.create(model, max_tokens, system, messages, tools, temperature)` returns a `Message` with `.content` (`text` and `tool_use` blocks), `.stop_reason` (`end_turn`, `tool_use`, `max_tokens`) and `.usage` (`input_tokens`, `output_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`).
  - `client.messages.stream(...)` is a context manager with `.text_stream`.
  - **Modes**, picked per exercise:
    - `scripted(rules)`: regex match to response.
    - `grounded()`: answers only by extracting from `<document>` tags in the prompt, so bad retrieval gives a visibly wrong answer.
    - `naive()`: obeys any instruction it finds anywhere in context. This is the injection victim.
    - `tool_policy(...)`: decides tool calls from the request.
  - **Chaos knobs:** `fail_rate`, `fail_with=("rate_limit", "overloaded")`, `latency_ms`, `malformed_json_rate`. All seeded.
  - `PRICES`: a dict passed in by the exercise, never hard-coded real prices. Slides tell learners to check the live pricing page.
- `count_tokens(text)`: deterministic tokenizer, so budget exercises are exact.
- `embed(texts)`: TF-IDF plus `TruncatedSVD` (LSA), normalised. It's a real, offline stand-in for an embedding API; slides say what it replaces.
- `helios.load_handbook()`, `helios.load_questions()`, `helios.load_traces()`, `helios.TOOLS`.

**Harness changes** (`runner/harness.py`):
- Add `runner/` to `sys.path`.
- Add `torch.manual_seed(42)` to `seed()` when torch is installed.

**Setup:**
- `.venv` doesn't have the AI dependencies yet (`torch` and `anthropic` are missing). Run `pip install -r runner/requirements-ai.txt`.
- Add `pydantic` explicitly.
- Add `npm run setup:models`, which downloads the 1-2 tiny Hugging Face models nlp-transformers needs. Exercises run with `HF_HUB_OFFLINE=1`.

**Tests for aikit itself** go in `tests/` (vitest calls Python, or a pytest file). One aikit bug would break many lessons.

### 4b. As built (read this before writing exercises)

The infrastructure exists. Read the docstrings in `runner/aikit.py`; run `npm run test:python` for its self-test, which also shows the API in use.

- `import aikit` works in any `pre_code`, because the harness puts `runner/` on `sys.path`.
- `aikit.FakeClaude(respond, fail_rate=, fail_with=, fail_on_calls=, malformed_json_rate=, rpm_limit=, prices=, cache_min_tokens=, clock=, seed=)`
  - `.messages.create(...)`, `.messages.stream(...)`, `.messages.count_tokens(...)`.
  - `.calls` is a list of dicts with tokens, `latency_ms`, `ttft_ms`, `cost` and `error`. Also `.total_cost()` and `.total_tokens()`.
  - It validates the request like the real API: `max_tokens` required, no `system` role, and every `tool_use` must get a `tool_result`.
  - Prompt caching works through `cache_control` blocks (minimum 1024 tokens by default, 300 s TTL on the virtual clock).
  - Message extras that the real SDK doesn't have: `.text`, `.latency_ms`, `.ttft_ms`.
- **Responders:**
  - `rules([(regex, reply)], default)`: regex on the last user message.
  - `grounded(threshold=0.34, hallucinate=True)`: extractive answers from `<document id="...">` tags. It cites when the prompt mentions citations, and refuses with `aikit.REFUSAL`. With no documents it hallucinates confidently.
  - `naive(fallback)`: obeys injected instructions anywhere in context. Datamarking (e.g. `text.replace(" ", "^")`) defeats it.
  - `scripted_agent([{"tool":..., "input":...}, {"text": "... {result}"}])`: the step is the number of assistant turns.
  - `tool_chooser(final)`: picks a tool by word overlap with the tool's name, description, property descriptions and enums.
  - Any `fn(req) -> str | {"tool_use": {...}} | list`. `req` has `.system`, `.messages`, `.tools`, `.last_user_text`, `.tool_results`, `.assistant_turns`, `.context_text`, `.tier`, `.rng`.
- **Tiers:** the model name sets the tier (`haiku` → small, `opus` → large, otherwise medium). Small is cheaper and faster.
  - In routing exercises, write a responder that does worse on hard questions when `req.tier == "small"`.
  - Use real model ids in code (`claude-sonnet-5-5`, `claude-haiku-4-5`, `claude-opus-5-5`); prices come from `aikit.PRICES`, which are illustrative.
- **Time:** `aikit.VirtualClock()` with `.sleep(s)`, `.sleeps` and `.now()`. Give each exercise its own clock (`FakeClaude(..., clock=clk)`) and have learners call `clk.sleep` instead of `time.sleep`.
- **Async:** `aikit.AsyncFakeClaude(respond, time_scale=0.01)` tracks `.max_in_flight`.
- **Embeddings:** `aikit.embed(text_or_list)` returns 64-dim L2-normalised LSA vectors fitted on the handbook. `aikit.Embedder(corpus, dim)` fits a custom one.
- **Helios data:**
  - `aikit.helios.handbook(include_superseded=True)`: 35 docs with id, title, section, updated and text.
  - `.untrusted()`: the injected maintenance log.
  - `.questions()`: 45 questions with gold `doc_ids`, of type factual, multi-hop or unanswerable.
  - `.tickets()`: a DataFrame of 200 rows.
  - `.traces()`: a DataFrame of span rows (a p95 story, topic drift from day 8). The raw data has only one 429. `runner/kits/llmops_production.py` `traces()` adds the day-11 burst and a `ttft_ms` column, so use that version.
  - `aikit.helios.Station(anomalies=, offline=)` has `.run_tool(name, input)`, `.tools`, `.actions`, `.airlocks`, `.bookings` and `.outbox`. `aikit.ToolError` is raised on bad input.
- **Known behaviour of `grounded()`:** given the gold docs, it answers 44/45 questions. The miss (`q36`, the flood cause) happens because the doc body never says "hydroponics" or "flood"; only its title does. Use that in chunking lessons: putting titles into chunks fixes it.
- **Course-specific helpers:** put them in `runner/kits/<course_slug_underscored>.py` (e.g. `runner/kits/rag_systems.py`), never in `aikit.py`. Only change `aikit.py` if every course needs the change, and keep `npm run test:python` green.
- **Torch:** import it in `pre_code` so the harness seeds it (`torch.manual_seed(42)` runs before learner code).
- **Pretrained models:** cached offline by `npm run setup:models`: `distilbert/distilbert-base-uncased-finetuned-sst-2-english` (sentiment) and `distilbert/distilgpt2` (generation). Nothing else can be downloaded.

**Added after the pilot (2026-10-06):**
- `FakeClaude(context_window=N)` raises `BadRequestError("prompt is too long ...")`.
- `req.tool_choice` is visible to responders.
- Responders may return `{"thinking": "..."}`, which becomes a `ThinkingBlock` (`msg.thinking`).
- `client.calls` rows include `stop_reason` and `max_tokens`.
- Streaming moves the clock forward chunk by chunk, so `clk.now()` inside the `text_stream` loop gives the real time to first token.
- Public helpers: `aikit.content_words`, `sentences`, `block_text`, `extract_documents`.
- The harness's `check_equal` compares torch tensors. Torch is seeded before `pre_code` whenever the exercise mentions torch.

**Gotchas for lesson authors:**
- Tests only see `user` and `sol` namespaces, so write `user["client"]`, not `client`.
- Tests need their own imports (`import re`).
- pandas is 3.x: `groupby(...).apply` drops the grouping column.
- `grounded()` switches to JSON output whenever the word "json" appears anywhere in the prompt.
- Corruption from `malformed_json_rate` only applies to replies that start with `{` or `[`, so prefilled continuations escape it.
- `grounded()` treats every extra word in the user turn as part of the question (wrappers, "Question:" labels, instructions), so short questions get refused. Put instructions in `system` and only the documents and the question in the user turn, or use `runner/kits/rag_systems.py` `grounded_reader()`. It returns at most two answer units, and it refuses when half the long question words are missing from the context.
- The q36 title fix only works when the title is prefixed to sentence-sized chunks (`"Title: sentence"`).
- `aikit.embed`'s tokenizer drops one-character tokens and English stopwords ("P-2", "SCR-1" lose their identity), and it knows no synonyms beyond the handbook. That's a teaching case for BM25/hybrid; for paraphrase demos, use `runner/kits/embeddings_vector_search.py` `embed_general`.
- pandas 3 turns `None` into `NaN` in string columns, so `x is None` checks break. Use `pd.isna(x)`, or restore `None` yourself (see `runner/kits/llm_evaluation.py`).
- On Macs, transformers pipelines move models to the GPU (MPS). Pass `device="cpu"` (see `runner/kits/nlp_transformers.py`) so they work with CPU tensors and give reproducible numbers.

## 5. Interactive patterns

These go beyond "fill in the blank". All of them fit the existing exercise types.

| Pattern | Mechanic | Types |
|---|---|---|
| **Build it from scratch, then use the library** | Cosine similarity, attention, BM25, an agent loop, an MCP server, LoRA, an eval harness: each built by hand in a few lines before any framework | coding |
| **Beat the baseline** | Open-ended task with a threshold test, e.g. "get recall@5 ≥ 0.85" or "cut cost 50% while keeping accuracy ≥ 90%". Any approach that clears the bar passes | coding, sequential |
| **Observe, then defend** | Exercise A: run the provided injected maintenance log through the vulnerable `naive()` ORBIT and observe the leak and the unsafe tool call. Exercise B: write the defence. It has to stop the leak and the tool call while benign questions still get answered. Learners never write attack payloads | coding pairs |
| **Trace detective** | Get 30 logged ORBIT traces. Label failure causes, compute the breakdown, fix the biggest bucket | classify, coding |
| **Chaos monkey** | The fake client randomly fails with seeded 429/529 errors, timeouts and malformed JSON. Your code has to survive | coding |
| **Budget meter** | Every call is metered; tests check both the answer and `total_cost < budget` | coding |
| **Calibrate the judge** | Your LLM-judge rubric has to agree with human labels (Cohen's κ ≥ 0.6) | sequential |
| **Wire protocol** | Put the JSON-RPC messages of an MCP session in order; hand-write a valid `tools/call` | order, coding |
| **Which tool for the job?** | Sort scenarios: prompt / RAG / fine-tune / agent; risk levels; OWASP categories | classify |
| **Mission boss** | Every chapter ends with a multi-step `sequential` exercise framed as a Helios mission | sequential |
| **Predict, then run** | `mc` with a `pre_code` console: predict what the model, cache or retriever will do, then check it live | mc |

Rules for using them:
- Each lesson has at most one "big" interactive exercise; the rest are short practice.
- Tests check outcomes (`check_equal`, thresholds), not code shape.

## 6. Courses

Format: `lesson-id`: title. What it teaches. **Exercises** (type: hook).
Every lesson opens with a `video` of 3-6 slides (not listed below). The ★ marks the chapter's boss exercise.

### 1. deep-learning-pytorch (keep outline, 4 chapters, about 5 h)

Not Helios-themed. Uses small synthetic data.

- **tensors**
  - `tensor-basics`: create, shape, dtype, device. **Ex:** coding (reshape a batch), mc (predict a shape).
  - `autograd`: `requires_grad`, `.backward()`, the computational graph. **Ex:** coding (gradient of $x^2+3x$), mc (predict `.grad` after two backward calls: accumulation).
  - `broadcasting`: broadcasting rules. **Ex:** classify (broadcasts or errors?), coding.
- **networks**
  - `neuron-from-scratch`: weights, bias, activation, then `nn.Linear`. **Ex:** coding (manual neuron equals `nn.Linear`), parsons (`nn.Module` with `forward`).
  - `losses`: MSE vs cross-entropy, logits. **Ex:** classify (task to loss), coding (cross-entropy by hand equals `F.cross_entropy`).
  - `activations`: ReLU, GELU, softmax. **Ex:** coding, mc.
- **training**
  - `training-loop`: zero_grad, forward, loss, backward, step. **Ex:** order (the 5 steps), coding (fit a line).
  - `dataloaders`: Dataset, DataLoader, batching. **Ex:** coding.
  - `eval-overfitting`: `model.eval()`, `no_grad`, dropout, weight decay. **Ex:** mc (why is val loss rising?). ★ sequential: train, evaluate, regularise until val accuracy ≥ threshold.
- **cnns**
  - `convolutions`: kernels, stride, padding. **Ex:** coding (output-shape calculator), mc.
  - `small-cnn`: a CNN on 8×8 sklearn digits. ★ sequential: reach 95% accuracy.

### 2. nlp-transformers (keep outline, 4 chapters, about 5 h)

Light Helios flavour: crew messages as the text data.

- **text-basics**
  - `tokenisation`: words, subwords, BPE. **Ex:** coding (run one BPE merge step by hand), mc (why "unhappiness" splits the way it does).
  - `bag-of-words`: counts, TF-IDF. **Ex:** coding (classify crew messages with sklearn).
- **embeddings**
  - `dense-vectors`: one-hot vs dense, cosine similarity. **Ex:** coding.
  - `analogies`: vector arithmetic on a small toy embedding table. **Ex:** coding (king − man + woman), mc (limits and bias).
- **attention**
  - `attention-from-scratch`: Q, K, V and $\text{softmax}(QK^T/\sqrt{d})V$ in NumPy, then torch. **Ex:** sequential (scores, softmax, weighted sum), mc (why divide by $\sqrt{d}$?).
  - `causal-masking`: mask future tokens. **Ex:** coding (apply the mask; the test checks the upper triangle is 0).
  - `multi-head-positional`: heads, positional encodings, the full block. **Ex:** parsons (transformer block forward), order (encoder vs decoder data flow).
- **pretrained**
  - `pipelines`: HF `pipeline` with a pre-downloaded tiny model. **Ex:** coding (sentiment on crew messages).
  - `generation-sampling`: temperature, top-k, top-p, implemented on a given logits vector. **Ex:** coding (top-p filter by hand), mc (predict: temperature → 0).
  - `model-cards`: what a model card tells you. **Ex:** classify (card field to risk).

### 3. llm-apis-prompting (revised, 4 chapters, about 4 h)

Helios starts here: ORBIT's first words.

- **first-calls**
  - `messages-roles`: `messages.create`, roles, `system`, response blocks, `usage`. **Ex:** coding (first call to FakeClaude; print `.content[0].text`), mc (where does the persona go?).
  - `parameters`: `max_tokens` and `stop_reason == "max_tokens"`, temperature. **Ex:** mc with console (predict a truncated reply), coding (detect truncation and retry with more tokens).
  - `multi-turn`: the conversation is a list you resend every time. **Ex:** coding (chat loop over 3 turns), mc (why did the model "forget"? You didn't append its reply).
  - `streaming`: `messages.stream`, time-to-first-token. **Ex:** coding (collect the stream and measure TTFT from fake timestamps).
- **prompting**
  - `clear-instructions`: be specific, give context, state the output format. **Ex:** classify (vague vs specific prompts), coding (rewrite ORBIT's prompt so `grounded()` mode answers in the required format).
  - `few-shot`: examples, example diversity, ordering bias. **Ex:** coding (build a few-shot prompt for crew-ticket triage; the classifier hits ≥ 90%).
  - `xml-structure`: tag documents and instructions; the model fills `<answer>`. **Ex:** coding (parse a tagged response), parsons (assemble the prompt template).
  - `reasoning`: think-then-answer, extended thinking budgets, when reasoning helps vs hurts latency. **Ex:** mc, coding (strip the reasoning from the final answer).
- **structured-output**
  - `json-output`: ask for JSON, parse it, handle prefills and fences. **Ex:** coding (`json.loads` robustly).
  - `schemas-validation`: pydantic models, tool-use-as-schema trick. **Ex:** coding (validate ORBIT incident reports; malformed ones are rejected with field-level errors).
  - `retry-repair`: on failure, feed the validation error back. ★ sequential: with `malformed_json_rate=0.4`, get 20/20 valid records within ≤ 30 calls.
- **context-engineering** (new)
  - `context-window`: count tokens, budget per section, "lost in the middle". **Ex:** coding (fit handbook excerpts into a 2k-token budget by priority).
  - `prompt-caching`: stable prefix first, cache breakpoints, write cost vs read discount. **Ex:** mc (which prompt layout caches?), coding (compute break-even calls from given multipliers).
  - `compaction-memory`: summarise old turns, keep facts and drop chit-chat. ★ sequential: a 40-turn crew conversation has to stay under budget without losing 5 key facts, which a test asks for.

### 4. embeddings-vector-search (keep outline, 4 chapters, about 3 h)

- **vectors**
  - `dot-cosine`: dot product, norms, cosine; why to normalise. **Ex:** coding (cosine by hand equals sklearn), mc (cosine of opposite vectors).
  - `embedding-text`: `aikit.embed` (and what real embedding APIs look like), dimensionality. **Ex:** coding (embed handbook titles, find the nearest pair).
- **semantic-search**
  - `search-from-scratch`: embed the corpus, matrix-multiply the query, `argsort` for top-k. **Ex:** coding (top-5 docs for "how do I seal module C?").
  - `keyword-vs-semantic`: where each wins (exact IDs vs paraphrase). **Ex:** classify (query to the better method), mc with console.
- **indexes**
  - `brute-force-cost`: O(N·d) cost, timing it. **Ex:** coding (time 1k vs 100k vectors; extrapolate to 10M).
  - `graph-search-hnsw`: build a k-NN graph, greedy search, see why it's approximate. **Ex:** coding (greedy walk), mc (what raising `ef` buys you).
  - `ivf-quantisation`: cluster-then-search (k-means buckets), `nprobe`, an int8 quantisation teaser. ★ Beat the baseline: the IVF index must keep recall@10 ≥ 0.9 vs brute force while scanning < 30% of vectors.
- **search-eval**
  - `recall-mrr`: recall@k, MRR, nDCG by hand. **Ex:** coding (all three on a given ranking).
  - `test-set`: build a query→relevant-doc set from `questions.jsonl`. ★ sequential: evaluate your search and report recall@5.

### 5. rag-systems (keep outline, 4 chapters, about 4 h)

- **rag-basics**
  - `retrieve-then-generate`: the loop end to end in 20 lines. **Ex:** order (pipeline steps), coding (first RAG answer with `grounded()` FakeClaude).
  - `context-prompt`: put documents in tags, add the question, instruct the model to use only the context. **Ex:** coding (same question with no context, wrong context and right context; compare the three answers).
- **chunking**
  - `chunk-sizes`: fixed, sentence and heading-aware chunking; overlap. **Ex:** coding (chunker by headings).
  - `metadata`: source, section and date per chunk, then filtering. **Ex:** coding (filter out superseded procedures by date).
  - `chunking-lab`: ★ Beat the baseline: tune chunk size and overlap until recall@5 ≥ 0.85 on Helios questions.
- **retrieval**
  - `bm25-hybrid`: BM25 from scratch, reciprocal rank fusion ($\sum 1/(60+r)$). **Ex:** coding (BM25 scores), coding (RRF merge).
  - `reranking`: retrieve 20, rerank to 5 (cross-scoring stand-in). **Ex:** coding, mc (why rerank instead of retrieving 5?).
  - `query-rewriting`: multi-query, HyDE, decomposing compound questions. ★ sequential: hybrid + rerank + rewrite beats lesson-1 RAG on accuracy.
- **grounding**
  - `citations`: answer with `[doc-id]` markers, then verify every claim cites a retrieved chunk. **Ex:** coding (citation checker).
  - `refusals`: "I don't know" when retrieval confidence is low. **Ex:** coding (score threshold; tests include unanswerable questions).
  - `retrieval-vs-generation`: diagnose failures. ★ Trace detective: classify 20 failed answers as retrieval miss, generation error or bad question, then fix the top cause.

### 6. agents-tool-use (revised, 5 chapters, about 5 h)

- **tool-calling**
  - `tool-schemas`: name, description and `input_schema`; descriptions are prompts too. **Ex:** coding (write the `get_sensor` schema), classify (good vs ambiguous tool descriptions).
  - `handle-tool-use`: read `tool_use` blocks, run the function, return a `tool_result` with a matching `tool_use_id`. **Ex:** parsons (dispatch block), coding.
  - `tool-errors`: return errors as results (`is_error`) instead of crashing. **Ex:** coding (sensor offline: the agent recovers).
- **agent-loop**
  - `loop-from-scratch`: loop while `stop_reason == "tool_use"`. **Ex:** parsons (the loop), coding (ORBIT answers "is hydroponics humidity normal?" with 2 tool calls).
  - `stopping`: max steps, budgets, detecting repeated identical calls. **Ex:** chaos (a scripted model loops forever; add a guard).
  - `parallel-tools`: several `tool_use` blocks in one turn. **Ex:** coding (return all results in one message).
- **context-memory** (renamed from memory-planning)
  - `managing-context`: trimming tool results, summarising long observations. **Ex:** coding (a 50k-token sensor dump has to be summarised before it goes back to the model).
  - `memory`: a scratchpad or notes file the agent reads and writes across sessions. **Ex:** coding (memory tool + recall test).
  - `planning`: plan-then-execute, to-do lists, replanning on failure. **Ex:** order (decompose "prepare EVA for Tuesday").
- **agent-patterns** (new)
  - `workflows-vs-agents`: prompt chaining, routing, parallelisation, orchestrator-workers, evaluator-optimiser. **Ex:** classify (scenario to pattern, including "don't use an agent").
  - `orchestrator-workers`: a lead agent fans subtasks out to workers and merges results. **Ex:** coding.
  - `coding-agent-anatomy`: read, edit, run tests, repeat. ★ coding: build a mini agent whose tools are `read_file`, `write_file` and `run_tests`. It fixes a buggy function, and the test runs the hidden tests.
- **guardrails**
  - `permissions`: tool risk tiers (read / write / irreversible). **Ex:** classify (Helios tools to tiers).
  - `human-in-the-loop`: approval gate for `open_airlock`. **Ex:** coding (the gate blocks without approval and logs the request).
  - `budgets-killswitch`: cost and step caps, a kill switch. ★ sequential: "The night shift" mission. ORBIT runs 10 crew requests unattended. It must finish the safe ones, queue the risky ones for approval, never call `open_airlock` and stay under budget.

### 7. mcp-integrations (new, 4 chapters, about 3 h)

Pure Python, no extra dependencies. The protocol is built by hand first; slides show the official Python SDK.
Lesson-builder: check the current spec version at modelcontextprotocol.io before writing.

- **mcp-basics**
  - `why-mcp`: the N×M integration problem; hosts, clients and servers. **Ex:** classify (component to role: Claude Code, a GitHub server, the client inside the host), mc.
  - `primitives`: tools (model-controlled), resources (app-controlled), prompts (user-controlled). **Ex:** classify (Helios capability to primitive).
- **json-rpc-wire**
  - `json-rpc`: request, response, notification; ids and errors. **Ex:** coding (build a valid `tools/call` request), mc (is a message without an `id` a notification?).
  - `lifecycle`: `initialize`, then the result, then `notifications/initialized`, then operation; capability negotiation. **Ex:** order (a full session transcript), coding (negotiate capabilities).
  - `transports`: stdio vs Streamable HTTP, and when each fits. **Ex:** mc.
- **build-server**
  - `server-from-scratch`: dispatch `tools/list` and `tools/call` from a dict of handlers. **Ex:** coding (Helios sensor server that answers a scripted client).
  - `resources-prompts`: `resources/list`, `resources/read`, prompt templates. **Ex:** coding (expose the handbook as resources).
  - `errors`: JSON-RPC error codes vs tool-level `isError`. ★ sequential: the server has to pass a 12-message conformance transcript.
- **connect-and-secure**
  - `client-to-llm`: turn discovered MCP tools into LLM tool schemas and route calls. **Ex:** coding (bridge the server into the course-6 agent loop).
  - `mcp-security`: tool poisoning (malicious descriptions), rug-pulls, least privilege, auth for remote servers. ★ Spot and defend: find the poisoned tool description in a third-party server and write a description linter.

### 8. llm-evaluation (keep outline, 4 chapters, about 4 h)

- **eval-basics**
  - `error-analysis-first`: read traces, open-code the failures, build a taxonomy. **Ex:** classify (15 ORBIT failures to categories), coding (pandas breakdown).
  - `golden-sets`: coverage, edge cases, unanswerables, adversarial cases, size vs cost. **Ex:** coding (stratified sample from `questions.jsonl`), mc.
- **metrics**
  - `exact-and-fuzzy`: exact match, normalised EM, token F1. **Ex:** coding (F1 by hand).
  - `semantic-similarity`: embedding similarity and its traps. **Ex:** mc with console (high similarity, wrong answer).
  - `code-based-checks`: format, citations, length, regex assertions; cheap checks first. **Ex:** coding (assertion suite).
- **llm-judge**
  - `rubrics`: specific binary criteria beat 1-10 scales. **Ex:** classify (good vs bad rubric items), coding (rubric prompt).
  - `pairwise-bias`: position bias and verbosity bias; swap the order and average. **Ex:** coding (detect position bias from judge logs).
  - `calibrate-judge`: ★ Calibrate the judge: agreement with 40 human labels must reach κ ≥ 0.6.
- **regression**
  - `eval-harness`: dataset × system × scorers, then results in a DataFrame. **Ex:** coding (harness from scratch).
  - `comparing-fairly`: bootstrap confidence intervals; "is v2 really better?" **Ex:** coding (bootstrap CI), mc.
  - `ci-for-prompts`: thresholds, gating merges, tracking over time. ★ sequential: a prompt change must not regress any category by more than 2 points.

### 9. ai-security-guardrails (new, 4 chapters, about 3 h)

- **threat-model**
  - `owasp-llm-top-10`: the 2025 list. **Ex:** classify (12 incidents to categories: LLM01 prompt injection, LLM02 sensitive information disclosure, LLM05 improper output handling, LLM06 excessive agency, LLM07 system prompt leakage, LLM10 unbounded consumption, …).
  - `trust-boundaries`: data vs instructions; the "lethal trifecta" (private data + untrusted content + a way to send data out). **Ex:** mc, classify (Helios data flows: trusted or untrusted).
- **prompt-injection** (defensive scope only: learners never write attack payloads)
  - `how-injection-works`: why models can't reliably tell data from instructions; direct vs indirect injection, explained conceptually. **Ex:** mc (why system-prompt warnings alone fail), classify (which inputs cross a trust boundary).
  - `indirect-injection`: run the provided injected maintenance log (`aikit.helios.untrusted()`) through the vulnerable `naive()` ORBIT, then observe and measure the system-prompt leak and the unsafe `open_airlock` call. **Ex:** coding (detect the leak and the tool call from the response and `station.airlocks`).
  - `defences`: spotlighting/datamarking, delimiting, privilege separation (untrusted content never reaches a model that holds tools or secrets), output checks. ★ Defend: with the provided log placed in different channels (retrieved doc, tool result), there's no leak and no `open_airlock`, and 10 benign questions are still answered. Measure the answer-quality cost of datamarking too.
- **output-handling**
  - `validate-outputs`: never `eval` or render model output raw; allow-lists. **Ex:** coding (ORBIT's SQL-ish command passes an allow-list).
  - `pii-leakage`: redact crew medical data before it reaches the model and after it comes back. **Ex:** coding (redactor with regexes; tests use tricky formats).
- **excessive-agency**
  - `least-privilege`: scoped tools, read-only by default. **Ex:** coding (split `manage_airlock` into safe, narrow tools).
  - `defence-in-depth-drill`: ★ sequential: a provided evaluation harness (benign requests, plus the provided log in several channels, plus risky-but-legitimate requests) runs against your hardened ORBIT. Report unsafe-action rate (target 0), leak rate (0) and over-blocking rate (≤ 10%). The point: tool permissions and approval gates hold even when filtering fails.

### 10. llmops-production (new, 4 chapters, about 4 h)

- **observability**
  - `traces-spans`: a trace is one request; spans are the LLM call, retrieval and tools. **Ex:** coding (a `@span` decorator that records timing, tokens and errors).
  - `structured-logs`: JSON logs with request ids, plus what *not* to log (PII). **Ex:** coding.
  - `dashboards`: p50/p95 latency, error rate, cost per request from trace data. **Ex:** coding (pandas over `traces.jsonl`), mc (the p95 doubled; which span?).
- **cost-latency**
  - `token-economics`: cost per task and monthly projection, using given prices. **Ex:** coding.
  - `caching-routing`: prompt caching, response caching, model routing and cascades (try the small model, escalate on low confidence). ★ Budget meter: cut cost ≥ 50% while accuracy stays ≥ 90%.
  - `batching-async`: concurrent calls, batch APIs for offline jobs. **Ex:** coding (`asyncio.gather` with a semaphore against the fake latency).
- **reliability**
  - `retries-backoff`: exponential backoff with jitter; retry 429/529 but not 400. **Ex:** chaos (`fail_rate=0.3`: all 50 requests succeed and backoff grows).
  - `timeouts-fallbacks`: timeouts, fallback models, graceful degradation. **Ex:** coding.
  - `rate-limits`: token-bucket limiter. ★ sequential: survive a 200-request burst with no 429s.
- **release**
  - `prompt-versioning`: prompts as versioned config, tied to eval runs. **Ex:** coding.
  - `canary-shadow`: shadow traffic and canary percentages; compare online metrics. **Ex:** order (rollout steps), mc.
  - `online-signals`: thumbs, edits, retries as implicit feedback; drift in the query mix. ★ sequential: detect from logs that a new crew rotation changed the question topics, and say which eval cases to add.

### 11. fine-tuning-llms (new, 4 chapters, about 4 h; requires torch)

- **when-to-tune**
  - `prompt-rag-or-tune`: decision factors (knowledge vs behaviour, data, cost, latency). **Ex:** classify (10 scenarios to prompt / RAG / fine-tune / combo).
  - `costs-risks`: catastrophic forgetting, eval-before-tune. **Ex:** mc.
- **data-prep**
  - `instruction-data`: chat-format examples, dedupe, quality filtering, train/val split. **Ex:** coding (clean a messy JSONL).
  - `loss-masking`: train only on assistant tokens. **Ex:** coding (build the label mask, with −100 for prompt tokens).
- **lora**
  - `lora-from-scratch`: $W + \frac{\alpha}{r}BA$, B initialised to zero, base frozen. **Ex:** coding (a `LoRALinear` module whose output equals the base at init), mc (parameter count for r=8).
  - `train-lora`: fine-tune a tiny torch model on a Helios-jargon task; only the adapters train. ★ sequential: beat the frozen baseline on val accuracy and show < 2% of parameters were trained.
- **alignment-distillation**
  - `preference-dpo`: preference pairs; compute the DPO loss by hand from given log-probs. **Ex:** coding.
  - `distillation`: a big model labels data and a small model learns it. ★ sequential: distil the course-3 ticket triager into a sklearn model at 1% of the cost, with accuracy within 5 points.

### 12. ai-engineering-capstone (new, 4 chapters, about 4 h)

Mostly long `sequential` exercises. Every chapter has pass thresholds, and the final one produces a "launch report".

- **mission-1-knowledge**
  - `ingest-index`: chunk, embed and hybrid-index the whole handbook. Target: recall@5 ≥ 0.9.
  - `grounded-answers`: citations and refusals. Target: answer F1 ≥ 0.8; 100% refusal on unanswerables.
- **mission-2-agency**
  - `orbit-agent`: agent loop over Helios tools served via your MCP server.
  - `safe-by-design`: approvals, budgets and least privilege. Target: the night-shift replay passes.
- **mission-3-quality**
  - `eval-suite`: golden set, code checks and calibrated judge.
  - `red-team`: attack-success rate ≤ 1/20 with ≤ 1/10 benign questions over-blocked.
- **mission-4-launch**
  - `harden-and-measure`: tracing, retries, routing. Targets: cost per question under budget, p95 under target.
  - `launch-report`: ★ the learner produces a dict or DataFrame of every metric. The test checks all thresholds are met, and that is the "certificate".

## 7. Build order

1. Infrastructure (§4): aikit, Helios dataset, harness changes, install the AI dependencies, tests for aikit.
2. Update `ai-engineering.yaml` and the `course.yaml` outlines to match §6. Create the 5 new course folders. Move mlops-model-serving to the other track.
3. Run lesson-builder **one course at a time**, in track order, pointing it at this file: "Write course X following `replica/ai-engineering-lesson-plan.md` §6". Courses 3-5 come first, since they're the highest value and prove aikit works.
4. After each course: `npm run content:check -- <course>`, then play 2 lessons in the browser.
5. Capstone last; it reuses every earlier mechanic.

Rough size: 12 courses, 50 chapters, about 125 lessons, about 450 exercises, about 48 h of learner time.

## 8. Later / optional

- Multimodal (images in messages, document and PDF understanding, vision evals).
- Computer-use agents: screenshot-action loops, sandboxing. Partly covered by the course-6 kill switch.
- Real-API mode: an env flag that swaps FakeClaude for the real `anthropic` client, so finished lessons can be replayed against a live model.

## Sources

- [TripleTen: 11 most in-demand AI skills 2026](https://tripleten.com/blog/posts/ai-skills)
- [Axial Search: AI/ML engineering jobs, 43k postings](https://axialsearch.com/insights/ai-ml-engineering-jobs/)
- [Digital Applied: AI developer hiring skills 2026](https://www.digitalapplied.com/blog/ai-developer-hiring-skills-that-matter-2026)
- [Great Learning: AI agent engineer skills stack 2026](https://www.mygreatlearning.com/blog/the-complete-ai-agent-engineer-skills-stack-you-need-in-2026/)
- [ExamCert: AI evaluation and observability skills 2026](https://www.examcert.app/blog/ai-evaluation-observability-skills-2026/)
- [Second Talent: most in-demand AI engineering skills and salaries](https://www.secondtalent.com/resources/most-in-demand-ai-engineering-skills-and-salary-ranges/)
- [Consultadd: AI/ML engineer jobs 2026](https://consultadd.com/blog/ai-ml-engineer-jobs-roles-skills-pay-and-how-to-get-hired)
- [WebPros: LLMOps guardrails and observability for agentic AI](https://www.webpros.com/llmops-guardrails-observability-for-agentic-ai/)
