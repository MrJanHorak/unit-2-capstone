# Assessment of your original version

This assessment describes the checkout before the completion work. The supplied assignment is
Claude-specific, but you confirmed Gemini is the intended adaptation because you and your
students have free access. Gemini is therefore an agreed provider deviation, not an unnoticed
implementation mistake. Strict grading against the unmodified Claude-only wording would still
need that exception recorded.

## What you had completed

You had built the main scaffold, not merely an empty prototype: a Python 3.11 virtual environment,
frozen dependencies, three agents, Chroma ingestion/retrieval, a SQLite teaching dataset, explicit
context-only qualitative prompts with refusal instructions, an NL-to-SQL pipeline with SQLite
date guidance, SELECT validation, a working CLI, environment-based credentials, and real token
logs. The historical log includes document and numeric questions. These are substantial core
deliverables.

## Requirement-by-requirement review

| Requirement | Original version | Finished version / evidence |
|---|---|---|
| Python 3.11, virtual environment, requirements | Present | Retained; Python 3.11 verified locally |
| Chunk and embed documents into Chroma | Present | Re-runnable ingestion; changed/removed chunks synchronised; tested |
| Classify and route queries | Present | Validated structured route + task plan, explicit follow-up resolution |
| Manager synthesises response | Incomplete: `both` printed two answers | One synthesis, checked against original evidence |
| Grounded document agent | Present | Citation checks plus a separate Gemini evidence reviewer |
| NL-to-SQL + SQLite + validate_sql | Present | SELECT check, read-only connection, authorizer, row/step limits, one guarded schema repair |
| Validation before release | Partial: citation presence and SQL success only | Candidate and synthesis reviews; failed answers withheld |
| Per-query tokenomics | Partial: stage records and hardcoded mismatched rates | All calls grouped by query, including reviewer, synthesis and thinking usage |
| Claude Sonnet 4.6 only | Intentional Gemini adaptation | Retained by explicit instructor direction |
| Key in ignored `.env` | Present; `.env` not tracked | Retained; a secret-free `.env.example` added |
| CLI handles all three routes | Routing present; no session memory | Session CLI + `/reset` + single-query/JSON modes |
| README Trust-but-Verify examples | Missing | Actual API transcripts and specific acceptance/rejection decisions |
| Submitted token log with >=10 queries | Logs existed, but no complete test report or evidence of all routes | New per-query live audit entries and transcript report |
| Conversation history (Silver) | Missing | Bounded validated history, independent retrieval every turn |
| Second qualitative validation strategy (Silver) | Missing | Separate evidence review API call |
| Agent unit tests (Gold) | Missing | Manager, qualitative, quantitative, validator tests |
| Workflow integration tests (Gold) | Missing | Real SQLite orchestration; real Chroma persistence tests |
| Measured token optimisation (Gold) | Missing | Paired live retrieval-budget comparison and README analysis |

## Where you fell short

1. **The assessed documentation was absent.** The repository README contained only the diagram.
   It did not include setup/usage, the assignment checklist, real Trust-but-Verify examples, or
   analysis of token consumption. The assignment explicitly says a working application alone
   is insufficient.
2. **Validation was much weaker than the name suggested.** `Source 1` could occur inside
   `Source 10`; a fabricated claim could pass by mentioning a source; any text containing
   “cannot find” could bypass a warning. The numeric validator ignored the answer and SQL,
   checking only whether execution succeeded. This closely follows the starter snippets,
   so the weakness is partly in the teaching scaffold, not solely your implementation.
3. **Mixed queries were routed but not coordinated into a final answer.** There was no
   synthesis step or synthesis validation, and neither agent had a clearly scoped subtask.
4. **None of the five listed stretch goals was implemented.** There was no session history,
   second reviewer, unit suite, workflow suite, or measured optimisation write-up.
5. **The cost claims were inaccurate for the selected model.** All agents used
   `gemini-3.5-flash-lite`, while the smoke test used a different model and the logger claimed
   another model's “actual” rates. Thinking usage was omitted. A per-agent cost multiplied
   by 1,000 is not the full cost of 1,000 multi-agent user queries.
6. **Failure handling and reproducibility needed work.** Importing modules constructed clients
   and loaded the embedding model; importing `setup_db.py` deleted and replaced the database.
   Re-ingestion used `add` with duplicate IDs; shrinking documents left stale evidence. The
   manager's invalid-route fallback silently guessed “qualitative”; API errors could end the CLI.
7. **The evidence was difficult to assess.** Historical logs record usage, not actual answers,
   flags or decisions. Repeated classifier entries and agent entries cannot reliably establish
   which end-to-end runs finished; there was no recorded mixed-route example.

## Remaining boundaries

The database is small, fictional teaching data. It has no industry benchmark, customer cohort
start dates, complaint table, or relationships linking sales to customer records. We can report
snapshot churn, but cannot establish a cohort churn rate or causal effects of policies. A second
Gemini reviewer can miss errors or over-reject valid claims; it is another check, not a truth oracle.
The completed evidence documents observed results, not a guarantee for every future question.
