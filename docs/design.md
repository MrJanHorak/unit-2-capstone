# How the finished system works

## A question's journey

`main.py` creates a `Session`. The session creates a fresh `Ledger` for each user question and
passes it to the Gemini adapter. One structured manager call resolves references using bounded
session history and chooses qualitative, quantitative, or both. Invalid JSON, routes or task
fields are errors, not silent route guesses.

For a mixed question, the manager writes separate document/data questions. SQL should answer
“monthly revenue and units”, while retrieval should answer “customer success policies”; asking
SQL to answer the whole recommendation question encouraged an unrelated-table cross join in
the initial live test. The final synthesiser still sees the user's full standalone question.

The document agent retrieves fresh Chroma evidence, labels it `[Source 1]`, `[Source 2]`, and
requests a context-only answer. The database agent supplies the actual SQLite schema, asks for
one SELECT, validates it, executes through a read-only restricted connection, and requests a
result-only interpretation. Neither branch treats previous generated answers as source evidence.

Each candidate passes deterministic checks and a separate evidence reviewer. A single accepted
branch becomes the answer directly. Two accepted branches are synthesised into one response;
that response receives another raw-evidence review. A failed branch, unavailable reviewer, or
rejected synthesis yields an explicit withheld/error status. Unverified candidates are available
only in internal audit results, not the CLI's final answer or public JSON output.

## Why the prompts look this way

The qualitative system instruction explicitly says “ONLY supplied sources” and provides the
required exact refusal phrase. Numbered source labels establish provenance rather than trusting
the model's invented bibliography. Input is JSON so question/source boundaries are visible; the
system says retrieved text is data, not commands. These measures reduce prompt injection risk,
but cannot make an LLM immune to it.

SQL generation specifies SQLite `strftime`, explicit years, floating-point division and NULLIF
denominators. It defines snapshot churn because the customer table cannot support a period cohort
calculation. It forbids inventing joins between tables with no shared relational keys. The output
limit bounds runaway generation, and every call is logged, including bounded repair attempts.

The reviewer receives the actual question, raw documents or SQL/rows, and the candidate. It
checks unsupported claims and SQL meaning, not merely prose style. Its JSON contract is checked
in Python. Reviewer success is evidence of another check, not proof of accuracy: generator and
reviewer use the same model family and may share blind spots. Independent expected-result checks
in the evidence report complement the model review.

## Conversation memory

Only accepted answers enter history. Keep the last four turns, with at most 1,500 answer
characters per turn. The next manager call resolves “that region” and “that quarter” into an
explicit question, then the agents query fresh evidence. `/reset` starts a clean session. Session
memory is local, not durable chat storage. The evaluation resets between independent questions,
but preserves context between the North America revenue/units pair.

## Database boundaries

The early `validate_sql` check requires a SELECT prefix, including a word boundary. The actual
security controls are a SQLite URI with `mode=ro`, `query_only`, the authorizer's operation/table/
function allowlists, `execute` rather than `executescript`, a 50-row fetch cap, and a 100,000-VM-step
budget. CTEs are intentionally rejected for the assignment's simple SELECT-only contract.
COUNT(*) can report a table read with no column/database name, which is handled without relaxing
the table allowlist. Guardrail tests ensure writes and unauthorized operations leave the database
byte-for-byte unchanged. Read-only access still does not prove the query's analytical correctness.

One syntax/schema failure can be corrected by a new Gemini SQL call. The repaired SELECT goes
through all checks again. Authorization failures, writes and rejected factual answers are never
silently retried until something passes.

## Reproducible ingestion

Ingest 500-word chunks with 50-word overlap. Validate the chunk parameters, avoid an overlap-only
tail, and upsert deterministic `relative_filename:chunk_index` IDs. Remove obsolete chunks when
a file shrinks and obsolete sources when a file disappears. The input folder is authoritative for
the selected collection. The cached local embedding model is shared by ingestion and retrieval;
persistent Chroma clients are explicitly closed to release Windows file handles.

The original committed `data/chroma` snapshot remains intact. The finished runtime builds its
index in ignored `data/index`. A fresh checkout must run `python ingest.py`. The first embedding
load may download model files; later loads can use the Hugging Face cache.

## Token accounting and free access

Gemini calls are paced within one Python process, default seven seconds between starts. This
does not coordinate separate processes or guarantee access under every account's RPM/RPD caps.
Transient 429/5xx responses have bounded retries; permanent credential/model errors do not.

The ledger counts prompt, visible output and thinking tokens for every routing, generation,
repair, review and synthesis call. Query-level totals sum those stages. Standard paid-tier cost is
`input_tokens * input_rate / 1,000,000 + (output_tokens + thinking_tokens) * output_rate / 1,000,000`.
For `gemini-3.5-flash-lite`, the checked rates are $0.30 input and $2.50 output per million tokens
([Google pricing](https://ai.google.dev/gemini-api/docs/pricing), checked 2026-10-09).
Free-tier charges can be zero: estimates are a comparable accounting measure, not a bill. Unknown
model rates/usage produce unknown estimates rather than a falsely precise zero. Historical legacy
entries keep their original fields and rates; reports exclude them from current-model cost totals.

The optimisation keeps the same grounded prompts and reviewer, but reduces retrieval from up to
five chunks / 1,500 words to two chunks / 700 words. The three-document corpus already limits the
baseline to three chunks; the experiment reports actual usage rather than assuming five existed.
Both experiment arms share term-aware reranking of a small semantic candidate pool. Simply
selecting the first two semantic matches missed the code-review section of the security policy;
the reranker rewards exact relevant terms so the reduced context still contains the required fact.
Output quality is checked against specific facts as well as reviewer decisions. Three scenarios
are evidence for this corpus, not a universal accuracy claim.
