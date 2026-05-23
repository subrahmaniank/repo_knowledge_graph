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

## Exploring the Graph with Cypher Queries

The knowledge graph exposes every node and relationship created during ingestion. Use the queries below to inspect the full relationship graph or to trace how layered code (controller → service → data access) is modeled across each supported stack.

1. **All relationships in the graph (helpful to validate node/edge labels before narrowing the scope):**

   ```cypher
   MATCH (from)-[rel]->(to)
   RETURN labels(from) AS from_labels,
          type(rel) AS relationship,
          labels(to) AS to_labels,
          COUNT(*) AS occurrences
   ORDER BY occurrences DESC
   LIMIT 200
   ```

2. **Java / Spring Boot controller → service → repository call chain:**

   ```cypher
   MATCH (ctrl:Class)-[:HAS_METHOD]->(ctrlMeth:Method)-[:CALLS]->(svcMeth:Method)<-[:HAS_METHOD]-(service:Class)
   WHERE ctrl.name ENDS WITH 'Controller' AND service.name ENDS WITH 'Service'
   OPTIONAL MATCH (svcMeth)-[:CALLS]->(repoMeth:Method)<-[:HAS_METHOD]-(repo:Class)
   WHERE repo.name ENDS WITH 'Repository'
   RETURN ctrl.name AS controller,
          ctrlMeth.name AS controller_method,
          service.name AS service,
          svcMeth.name AS service_method,
          repo.name AS repository,
          repoMeth.name AS repository_method
   ORDER BY controller, controller_method
   ```

3. **Python (Flask/Django) view → service helper → repository/ORM layer:**

   ```cypher
   MATCH (viewClass:Class)-[:HAS_METHOD]->(viewMeth:Method)-[:CALLS]->(serviceMeth:Method)<-[:HAS_METHOD]-(serviceClass:Class)
   WHERE viewClass.name CONTAINS 'View' OR viewClass.name CONTAINS 'Controller'
     AND serviceClass.name CONTAINS 'Service'
   OPTIONAL MATCH (serviceMeth)-[:CALLS]->(repoMeth:Method)<-[:HAS_METHOD]-(repoClass:Class)
   WHERE repoClass.name CONTAINS 'Repository' OR repoClass.name CONTAINS 'ORM'
   RETURN viewClass.name AS view,
          viewMeth.name AS view_method,
          serviceClass.name AS service,
          serviceMeth.name AS service_method,
          repoClass.name AS repository,
          repoMeth.name AS repository_method
   ORDER BY view, view_method
   ```

4. **Angular component/service → data access service (e.g., HTTP or repository service):**

   ```cypher
   MATCH (cmp:Class)-[:HAS_METHOD]->(cmpMeth:Method)-[:CALLS]->(svcMeth:Method)<-[:HAS_METHOD]-(service:Class)
   WHERE cmp.name ENDS WITH 'Component' AND service.name ENDS WITH 'Service'
   OPTIONAL MATCH (service)-[:HAS_METHOD]->(dataMeth:Method)-[:CALLS]->(repoMeth:Method)<-[:HAS_METHOD](repo:Class)
   WHERE repo.name ENDS WITH 'Repository' OR repo.name ENDS WITH 'DataService'
   RETURN cmp.name AS component,
          cmpMeth.name AS component_method,
          service.name AS service,
          svcMeth.name AS service_method,
          repo.name AS repository,
          repoMeth.name AS repository_method
   ORDER BY component, component_method
   ```

5. **React component / hook dispatch → service → API client layer:**

   ```cypher
   MATCH (reactCmp:Class)-[:HAS_METHOD]->(renderMeth:Method)-[:CALLS]->(svcMeth:Method)<-[:HAS_METHOD]-(service:Class)
   WHERE reactCmp.name ENDS WITH 'Component' OR reactCmp.name ENDS WITH 'Hook'
     AND service.name ENDS WITH 'Service'
   OPTIONAL MATCH (svcMeth)-[:CALLS]->(clientMeth:Method)<-[:HAS_METHOD](client:Class)
   WHERE client.name ENDS WITH 'Client' OR client.name ENDS WITH 'Api'
   RETURN reactCmp.name AS react_component_or_hook,
          renderMeth.name AS entry_method,
          service.name AS service,
          svcMeth.name AS service_method,
          client.name AS client,
          clientMeth.name AS client_method
   ORDER BY react_component_or_hook, entry_method
   ```

Adjust the `WHERE` clauses above to match your naming conventions (e.g., prefixes or suffixes used in your repo) and increase `LIMIT` if needed. These queries can be run against any Neo4j instance populated by this project to audit call chains or validate that controllers/services/repositories are correctly linked.
