# AI Assistant Guide

This file defines the working rules for coding agents in this repository.

## Mission

Build and evolve a deterministic semantic code knowledge graph platform.

Do not treat this as a simple syntax parser project.

## Non-Negotiable Architecture Rules

### 1) Preserve Multi-Pass Parsing

- Keep PASS 1 for indexing/registration
- Keep PASS 2 for relationship resolution
- Do not collapse back to single-pass parsing

Current flow is orchestrated in `main.py`.

### 2) Keep Graph Generation Deterministic

Graph edges must come from:

- AST parsing
- Symbol/type/import resolution
- Registry lookups

Do not generate semantic edges via LLM guesses or regex heuristics.

### 3) Favor Semantic Edges over Syntactic Adjacency

The graph should represent real semantic relationships, not raw AST neighborhood.

## Project State (Current)

Implemented:

- Java, Python, JavaScript, TypeScript parser routing
- Neo4j graph write path
- Java symbol resolution helpers
- Framework enrichers (Spring, Flask, React, Angular, React Router)
- Registry-based method/class indexing

Common unresolved calls are expected for:

- external SDKs
- framework internals
- dynamic/runtime-only behavior
- unresolved fluent chains

## Important Files

- `main.py`: clone, scan, PASS 1, PASS 2, Neo4j write lifecycle
- `parsers/java/parser.py`: core Java AST extraction and invocation handling
- `graph/symbol_resolution/java_resolver.py`: Java semantic linking logic
- `graph/neo4j_writer.py`: merge writes, constraints, cleanup, stats
- `parsers/parser_factory.py`: extension -> parser mapping
- `enrichers/spring/enricher.py`: Spring repository method enrichment

## Engineering Guardrails

### Do

- Keep registries as the source of semantic truth
- Maintain language-agnostic graph contracts where possible
- Keep parser responsibilities separate from DB writer responsibilities
- Classify unresolved nodes before treating them as regressions

### Do Not

- Bypass registries with ad hoc string matching
- Write repository-specific hacks that do not generalize
- Directly push Neo4j operations from parser internals
- Re-introduce recursion-breaking logic in AST walks

## Known Pitfalls

- Avoid early `return` patterns that stop recursive traversal when skipping unresolved invocations
- Ensure synthetic methods are connected with `HAS_METHOD`
- Keep database cleanup behavior explicit across ingestion runs

## Validation Expectations

When changing parser or resolver logic, validate with graph queries and counters:

- unresolved call volume and categories
- orphan methods/classes
- call-chain reachability
- resolution rate changes between runs

### Agent Validation Checklist (Required)

When an agent modifies parser, resolver, enricher, or write-path logic, run this end-to-end validation before marking work complete.

1. Ingestion run

- Ensure `.env` has `REPO_URL`, `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`.
- Run:
  - `uv run python -u main.py`

2. Core Cypher metrics (must capture before/after for resolver changes)

- Total calls:
  - `MATCH ()-[r:CALLS]->() RETURN count(r) AS total_calls`
- Resolved calls:
  - `MATCH ()-[r:CALLS]->() WHERE r.resolved = true RETURN count(r) AS resolved_calls`
- Unresolved calls:
  - `MATCH ()-[r:CALLS]->() WHERE r.resolved = false RETURN count(r) AS unresolved_calls`
- Unresolved hotspots:
  - `MATCH ()-[r:CALLS {resolved:false}]->(u:UnresolvedFunction) RETURN u.object AS object, u.method AS method, count(*) AS c ORDER BY c DESC LIMIT 25`

3. Graph integrity checks

- Orphan methods:
  - `MATCH (m:Method) WHERE NOT (()-[:HAS_METHOD]->(m)) RETURN count(m) AS orphan_methods`
- Orphan classes:
  - `MATCH (c:Class) WHERE NOT ((:File)-[:DECLARES]->(c)) RETURN count(c) AS orphan_classes`
- CALLS edges to missing targets (should be 0):
  - `MATCH ()-[r:CALLS]->(t) WHERE t.id IS NULL RETURN count(r) AS bad_calls`

4. Language breakdown checks

- Python:
  - `MATCH (m)-[r:CALLS]->() WHERE m.id STARTS WITH 'python:' AND r.resolved = true RETURN count(r) AS py_resolved`
  - `MATCH (m)-[r:CALLS]->() WHERE m.id STARTS WITH 'python:' AND r.resolved = false RETURN count(r) AS py_unresolved`
- Java:
  - `MATCH (m)-[r:CALLS]->() WHERE m.id STARTS WITH 'java:' AND r.resolved = true RETURN count(r) AS java_resolved`
  - `MATCH (m)-[r:CALLS]->() WHERE m.id STARTS WITH 'java:' AND r.resolved = false RETURN count(r) AS java_unresolved`

5. Pass/fail criteria

- No regression in resolved-call rate for touched language(s).
- No increase in orphan classes/methods for touched language(s).
- `bad_calls = 0`.
- If unresolved increases, agent must include top unresolved categories and root-cause explanation in output.

## Preferred Change Strategy

1. Update registries and resolver behavior first.
2. Keep parser changes minimal and AST-driven.
3. Preserve PASS 1/PASS 2 contracts.
4. Verify graph shape and key traversals in Neo4j.

## Near-Term Priorities

- Fluent invocation chain resolution
- Constructor DI semantics
- Inheritance and polymorphic linking
- External dependency indexing
- Lambda/method-reference support
- Incremental and parallel ingestion
