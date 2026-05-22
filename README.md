# Enterprise Semantic Code Knowledge Graph

This project builds a deterministic semantic knowledge graph from source code and writes it to Neo4j.

It clones a target repository, scans source files, parses supported languages with tree-sitter, and performs two-pass semantic linking.

## What It Produces

- Cross-language code entities (files, classes, interfaces, methods)
- Semantic call edges (`CALLS`) and ownership edges (`HAS_METHOD`)
- Field/property access edges (`ACCESSES`)
- Unresolved call placeholders for diagnostics (`UnresolvedFunction`)

## Current Architecture

```text
Repository URL (.env)
    -> clone to repos/
    -> recursive file scan
    -> PASS 1 (indexing only)
    -> PASS 2 (resolution and links)
    -> Neo4j graph write
```

Entry point: `main.py`

## Supported Languages

- Java (`.java`)
- Python (`.py`)
- JavaScript (`.js`, `.jsx`)
- TypeScript (`.ts`, `.tsx`)

Parser routing is implemented in `parsers/parser_factory.py`.

## Key Components

- `main.py` - orchestration for clone, scan, parse, and graph ingestion
- `ingestion/clone_repo.py` - clones target repository into `repos/`
- `ingestion/scanner.py` - recursively scans repository files
- `parsers/` - language parsers and parser factory
- `graph/neo4j_writer.py` - Neo4j writes, constraints, cleanup, and stats
- `graph/class_registry.py` / `graph/method_registry.py` - semantic registries
- `graph/symbol_resolution/` - Java resolution helpers
- `enrichers/` - framework-specific enrichment (Spring, Flask, React, Angular, React Router)

## Graph Model

### Node labels

- `File`
- `Class`
- `Interface`
- `Method`
- `Field`
- `UnresolvedFunction`

### Relationship types

- `HAS_METHOD`
- `CALLS`
- `ACCESSES`

## Environment Configuration

Use `.env` (not committed) and `sample.env` as a template.

Required by current runtime (`main.py`):

- `REPO_URL`
- `NEO4J_URI`
- `NEO4J_USERNAME`
- `NEO4J_PASSWORD`

Common optional fields used for Aura or documentation:

- `NEO4J_DATABASE`
- `AURA_INSTANCEID`
- `AURA_INSTANCENAME`

## Run Locally

1. Install dependencies (Python 3.11+):

```bash
uv sync
```

2. Configure `.env` from `sample.env`.

3. Run ingestion:

```bash
uv run python main.py
```

The pipeline clears Neo4j before each ingestion (`writer.clear_database()`) and then recreates constraints.

## Current Behavior Notes

- Parsing is intentionally multi-pass (index first, resolve second)
- Unresolved calls are expected for external SDK/framework/runtime paths
- Existing cloned repos are reused unless removed from `repos/`

## Roadmap (Current Priorities)

- Fluent invocation-chain resolution
- Constructor injection semantics
- Inheritance graph edges (`EXTENDS`, `IMPLEMENTS`)
- External dependency indexing (Maven/SDK)
- Lambda and method-reference support
- Incremental and parallel indexing

## Agent Guidance

If you are using an AI coding assistant in this repository, see `AGENTS.md` for implementation constraints and architectural guardrails.
