# main.py

from pathlib import Path
import os

from dotenv import load_dotenv

from ingestion.clone_repo import clone_repository
from ingestion.scanner import scan_repository

from parsers.parser_factory import ParserFactory

from graph.neo4j_writer import Neo4jWriter

from graph.class_registry import ClassRegistry
from graph.method_registry import MethodRegistry

from graph.symbol_resolution.symbol_table import SymbolTable

load_dotenv()

#
# CONFIG
#
REPO_URL = os.getenv("REPO_URL")

REPOS_DIR = "repos"


def main():

    if not REPO_URL:
        raise ValueError("REPO_URL is not set. Add it to your .env file.")

    print("\n=== CLONING REPOSITORY ===")

    repo_path = clone_repository(REPO_URL, REPOS_DIR)

    print(f"\nRepository path: {repo_path}")

    print("\n=== SCANNING FILES ===")

    files = scan_repository(repo_path)

    print(f"\nDiscovered {len(files)} files")

    #
    # GLOBAL REGISTRIES
    #
    symbol_table = SymbolTable()

    class_registry = ClassRegistry()

    method_registry = MethodRegistry()

    #
    # PARSER FACTORY
    #
    parser_factory = ParserFactory(
        symbol_table=symbol_table,
        class_registry=class_registry,
        method_registry=method_registry,
    )

    #
    # NEO4J WRITER
    #
    writer = Neo4jWriter(
        os.getenv("NEO4J_URI"),
        os.getenv("NEO4J_USERNAME"),
        os.getenv("NEO4J_PASSWORD"),
        os.getenv("NEO4J_BATCH_SIZE", "500"),
    )

    #
    # CLEAN DATABASE
    #
    writer.clear_database()

    writer.create_constraints()

    #
    # PASS 1 — INDEXING
    #
    print("\n=== PASS 1: INDEXING ===")

    for file_path in files:
        try:
            extension = Path(file_path).suffix

            parser = parser_factory.get_parser(extension)

            if not parser:
                continue

            result = parser.parse(file_path, definition_only=True)

            writer.write_graph(result["nodes"], result["relationships"])

        except Exception as e:
            print(f"\n[PASS1 ERROR] {file_path}")

            print(str(e))

    #
    # PASS 2 — RELATIONSHIPS
    #
    print("\n=== PASS 2: RESOLUTION ===")

    for file_path in files:
        try:
            extension = Path(file_path).suffix

            parser = parser_factory.get_parser(extension)

            if not parser:
                continue

            result = parser.parse(file_path, definition_only=False)

            writer.write_graph(result["nodes"], result["relationships"])

        except Exception as e:
            print(f"\n[PASS2 ERROR] {file_path}")

            print(str(e))

    #
    # DEBUG STATS
    #
    print("\n=== REGISTRY STATS ===")

    print(f"Classes: {class_registry.size()}")

    print(f"Methods: {method_registry.size()}")

    print(f"Symbols: {symbol_table.size()}")

    writer.graph_stats()

    print("\n=== KNOWLEDGE GRAPH INGESTION COMPLETE ===")


if __name__ == "__main__":
    main()
