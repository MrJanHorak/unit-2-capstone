# What each file does

Read `README.md` first, then `agents/manager.py`. Source comments explain why prompts, guards,
history limits and resource ownership exist. The table covers source/configuration files and
generated-data families; virtual-environment internals and `.git` are tool-managed, not project code.

| File | Responsibility and how it is used |
|---|---|
| `main.py` | User-facing CLI; creates one session, accepts questions, handles exit/EOF and `/reset`, displays verified answers, source filenames, SQL and usage. `--query` is scriptable; `--json` omits raw rejected candidates. |
| `config.py` | Immutable defaults for model, paths and budgets. Loads `.env` relative to the repository rather than the launch directory. The new runtime index is `data/index`. |
| `llm.py` | Sole Gemini API adapter. Lazily creates the client, sends system instructions, caps output, requests JSON for routing/review, meters responses before parsing, rejects empty/truncated/malformed output, paces calls and retries transient errors. |
| `agents/__init__.py` | Marks the agent directory as a Python package; no API calls on import. |
| `agents/manager.py` | Owns bounded session history, asks for a structured route and standalone/split questions, calls the specialist agents, withholds failed results, synthesises mixed answers, reviews synthesis, and finalises the query ledger. |
| `agents/qualitative.py` | Retrieves context, builds a JSON prompt with stable source labels, generates a grounded cited candidate, calls citation and evidence checks. Empty indexes produce an explicit refusal. |
| `agents/quantitative.py` | Reads the real database schema, generates SQL, validates before execution, optionally repairs one syntax/schema error, interprets bounded rows, then reviews numeric accuracy and SQL semantics. |
| `retrieval.py` | Shared embedding model and Chroma client lifecycle. Retrieves a small semantic candidate pool, reranks with term coverage, and caps selected chunks/words. Always closes persistent clients so Windows file handles are released. |
| `safe_sql.py` | SELECT prefix checker and read-only SQLite execution. Authorizer allows reads only from the three teaching tables and approved functions; blocks other operations. Limits fetched rows and SQLite VM work. Also strips code fences and reads schema. |
| `ingest.py` | Reads UTF-8 `.txt`/`.md` files recursively; creates 500-word chunks with 50-word overlap, embeds, upserts deterministic IDs, removes stale chunks/files, closes the index. CLI chooses a document directory. |
| `setup_db.py` | Creates sales/customers/employees tables and the original example rows only at a new path. Existing databases are kept. `create_database` supports temporary test databases; importing is inert. |
| `smoke_test.py` | Explicit live API connectivity check with the configured model and usage logging. No requests occur when imported. |
| `validation/__init__.py` | Marks the validation package. |
| `validation/validator.py` | Checks exact citations/refusals and SQL execution status, then performs an independent model review against raw evidence. Validates the review JSON contract and returns flags before release. |
| `tokenomics/__init__.py` | Marks the token accounting package. |
| `tokenomics/logger.py` | Query-scoped ledger for all API stages, thinking tokens, latency and estimated paid-tier cost. Appends schema-version-2 JSONL records while preserving earlier legacy lines. Unknown usage/prices remain unknown. |
| `scripts/evaluate.py` | Explicit live runner for eleven scenarios, including the eight original query examples with a year specified for Q4, a reference follow-up pair, and an unsupported-topic refusal. Saves full audit candidates. `--optimisation` runs three paired retrieval budgets. |
| `scripts/__init__.py` | Marks the evaluation/report utilities as a Python package. |
| `scripts/report.py` | Summarises versioned logs and evidence, independently checks expected SQL results and source-backed facts, and emits the measured token comparison. Makes no API calls. |
| `tests/__init__.py` | Marks the regression-test package. |
| `tests/helpers.py` | Scripted model responses, small source fixture, and isolated temporary SQLite datasets. Fake output here is never counted as live submission evidence. |
| `tests/test_agents.py` | Manager classification/history/task-plan and both specialist agent unit tests, including blocked writes, incorrect numbers and bounded SQL repair. |
| `tests/test_validation.py` | Citation mismatch, missing citation, refusal bypass, irrelevant evidence, unjustified refusal and malformed reviewer tests. |
| `tests/test_workflows.py` | Multi-agent orchestration integration with real SQLite and scripted Gemini: synthesis, split tasks, conversation/reset, withholding, failed reviewer accounting and history limits. |
| `tests/test_infrastructure.py` | Exact SQLite aggregates, read-only/multi-statement/function/table guards, resource budgets, ingestion chunk boundaries, setup preservation and token-cost arithmetic. |
| `tests/test_ingestion.py` | Real Chroma integration with deterministic local vectors: repeat ingestion, document shrinking/removal, retrieval context budgets and clean client shutdown. Does not claim to measure semantic quality. |
| `tests/test_retrieval.py` | Regressions for term-aware reranking so code-review evidence remains selected despite broader documents receiving better semantic scores. |
| `tests/test_cli.py` | Ensures rejected audit candidates are omitted from public JSON and that reset/EOF do not trigger model calls. |
| `requirements.txt` | Original frozen dependency environment, including transitive dependencies. Retained to reproduce the working installed versions. Tests use `unittest`; Chroma integration requires its installed dependency. |
| `.env` | Your untracked local API credentials/configuration. Contents are intentionally excluded from documentation and Git. |
| `.env.example` | Safe template for a user's own credentials, model and free-tier pacing, with optional price overrides for a different model. |
| `.gitignore` | Ignores credentials, virtual environments, bytecode and the regenerable runtime index; permits `.env.example`. |
| `README.md` | Setup, architecture, adapted rubric checklist, actual Trust-but-Verify decisions, live evidence and token optimisation. |
| `docs/assessment.md` | Honest original-versus-finished assessment, with the original omissions and the explicit Gemini adaptation. |
| `docs/file-guide.md` | This map of the entire project. |
| `docs/design.md` | Data flow, prompts, validation decisions, conversation behavior, SQL boundaries and cost model explained for students. |
| `docs/evidence/live_queries.json` | Latest real API scenario outputs, raw retrieved evidence, executed SQL, validation results and query IDs matching the ledger. Audit-only; may include rejected candidates. |
| `docs/evidence/initial_live_queries.json` | Preserved earlier live evaluation that exposed the bad cross join, misspelled column and free-tier quota errors. These were genuine Gemini responses, not test doubles. |
| `docs/evidence/optimisation.json` | Paired real API baseline/optimised outputs and usage for a reproducible budget comparison. |
| `docs/evidence/report.json` | Offline computed independent evidence checks, query counts and measured savings generated by `scripts/report.py`. |
| `tokenomics_log.jsonl` | Historical legacy agent entries plus new query entries. Contains actual API consumption, including error/flagged runs. It is included because the assignment requires it. |
| `data/database.sqlite` | Original structured teaching dataset: 15 sales, 12 customers, 14 employees. Read-only for agent queries. Recreate elsewhere with `setup_db.py --output`. |
| `data/documents/security_policy.txt` | Fictional security facts: data classes, MFA/password rules, code reviews and incident response. Retrieved evidence, not executable rules for this development session. |
| `data/documents/customer_service_handbook.txt` | Fictional SLAs, complaints/refunds and engineering escalation. Supports customer-policy answers and mixed recommendations. |
| `data/documents/engineering_onboarding.txt` | Original fictional onboarding/RAG guidance; mentions Claude/Anthropic because it describes the supplied original architecture. This project's executable code/config use the agreed Gemini adaptation. |
| `data/chroma/chroma.sqlite3` | Preserved original vector-index catalog, not used by the finished default configuration. |
| `data/chroma/<UUID>/data_level0.bin` | Original Chroma vector records; generated binary data, not hand-edited source. |
| `data/chroma/<UUID>/header.bin` | Original Chroma index header. |
| `data/chroma/<UUID>/length.bin` | Original Chroma record-length metadata. |
| `data/chroma/<UUID>/link_lists.bin` | Original Chroma graph links used for approximate nearest-neighbor search. |
| `data/index/**` | New ignored Chroma index regenerated by `ingest.py`; stores the current document embeddings and metadata. |
| `.venv/**` | Local Python interpreter and installed dependencies. Never committed. |

All application paths are anchored to `config.ROOT`. Test paths are isolated temporary directories;
they do not modify your submitted database, documents, vector snapshot or token log.
