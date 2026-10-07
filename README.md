# Multi-Agent RAG System with Gemini
----
## System Architecture
```
User Query (CLI)
      │
      ▼
┌─────────────────┐
│  Manager Agent  │  ── classifies query ──► qualitative / quantitative / both
└─────────────────┘
      │                          │
      ▼                          ▼
┌──────────────────┐    ┌────────────────────┐
│ Qualitative Agent│    │ Quantitative Agent │
│                  │    │                    │
│ • Vector DB      │    │ • SQLite DB        │
│   (ChromaDB)     │    │ • NL → SQL         │
│ • Semantic search│    │ • Query execution  │
│ • Gemini for     │    │ • Gemini for       │
│   generation     │    │   interpretation   │
└──────────────────┘    └────────────────────┘
      │                          │
      └──────────┬───────────────┘
                 ▼
      ┌─────────────────────┐
      │  Validation Layer   │  ── checks grounding, flags issues
      └─────────────────────┘
                 │
                 ▼
      ┌─────────────────────┐
      │  Tokenomics Logger  │  ── logs token usage and cost per query
      └─────────────────────┘
                 │
                 ▼
        Response to User

```


