# graph/neo4j_writer.py

from collections import defaultdict

from neo4j import GraphDatabase


class Neo4jWriter:

    def __init__(
        self,
        uri,
        username,
        password,
        batch_size=500,
    ):

        self.driver = (
            GraphDatabase.driver(
                uri,
                auth=(
                    username,
                    password
                )
            )
        )

        self.batch_size = max(1, int(batch_size))

    #
    # CLOSE
    #
    def close(self):

        self.driver.close()

    #
    # WRITE GRAPH
    #
    def write_graph(
        self,
        nodes,
        relationships
    ):

        with self.driver.session() as session:

            self._write_nodes_batch(
                session,
                nodes
            )

            self._write_relationships_batch(
                session,
                relationships
            )

    def _write_nodes_batch(self, session, nodes):

        if not nodes:
            return

        grouped = defaultdict(list)

        for node in nodes:
            try:
                label = self._sanitize_cypher_token(node["type"])
                grouped[label].append(self._node_row(node))
            except Exception as e:
                print("\n[Neo4jWriter] NODE PREP ERROR")
                print(node)
                print(e)

        for label, rows in grouped.items():
            query = f"""
            UNWIND $rows AS row
            MERGE (n:{label} {{
                id: row.id
            }})
            SET n += row.properties
            """

            for chunk in self._chunked(rows, self.batch_size):
                try:
                    session.run(query, rows=chunk)
                except Exception as e:
                    print("\n[Neo4jWriter] NODE BATCH ERROR")
                    print(f"Label: {label}")
                    print(e)
                    for row in chunk:
                        try:
                            self._write_node(
                                session,
                                {
                                    "type": label,
                                    "id": row["id"],
                                    "name": row["properties"].get("name"),
                                    "metadata": {
                                        k: v
                                        for k, v in row["properties"].items()
                                        if k not in {"id", "name"}
                                    },
                                },
                            )
                        except Exception as fallback_error:
                            print("\n[Neo4jWriter] NODE ERROR")
                            print(row)
                            print(fallback_error)

    def _write_relationships_batch(self, session, relationships):

        if not relationships:
            return

        grouped = defaultdict(list)

        for relationship in relationships:
            try:
                rel_type = self._sanitize_cypher_token(relationship["type"])
                grouped[rel_type].append(self._relationship_row(relationship))
            except Exception as e:
                print("\n[Neo4jWriter] RELATIONSHIP PREP ERROR")
                print(relationship)
                print(e)

        for rel_type, rows in grouped.items():
            query = f"""
            UNWIND $rows AS row
            MATCH (a {{
                id: row.from_id
            }})
            MATCH (b {{
                id: row.to_id
            }})
            MERGE (a)-[r:{rel_type}]->(b)
            SET r += row.properties
            """

            for chunk in self._chunked(rows, self.batch_size):
                try:
                    session.run(query, rows=chunk)
                except Exception as e:
                    print("\n[Neo4jWriter] RELATIONSHIP BATCH ERROR")
                    print(f"Type: {rel_type}")
                    print(e)
                    for row in chunk:
                        try:
                            self._write_relationship(
                                session,
                                {
                                    "from": row["from_id"],
                                    "to": row["to_id"],
                                    "type": rel_type,
                                    "metadata": row["properties"],
                                },
                            )
                        except Exception as fallback_error:
                            print("\n[Neo4jWriter] RELATIONSHIP ERROR")
                            print(row)
                            print(fallback_error)

    def _node_row(self, node):

        node_id = node["id"]

        properties = {
            "id": node_id,
            "name": node.get("name"),
        }

        metadata = node.get("metadata", {})
        properties.update(metadata)

        properties = {
            k: v
            for k, v in properties.items()
            if v is not None
        }

        return {
            "id": node_id,
            "properties": properties,
        }

    def _relationship_row(self, relationship):

        properties = relationship.get("metadata", {})

        properties = {
            k: v
            for k, v in properties.items()
            if v is not None
        }

        return {
            "from_id": relationship["from"],
            "to_id": relationship["to"],
            "properties": properties,
        }

    def _chunked(self, values, chunk_size):

        for i in range(0, len(values), chunk_size):
            yield values[i : i + chunk_size]

    def _sanitize_cypher_token(self, token):

        if not token:
            raise ValueError("Empty Cypher token")

        sanitized = str(token)

        if not sanitized.replace("_", "").isalnum():
            raise ValueError(f"Unsafe Cypher token: {token}")

        return sanitized

    #
    # WRITE NODE
    #
    def _write_node(
        self,
        session,
        node
    ):

        label = node["type"]

        node_id = node["id"]

        properties = {

            "id":
                node_id,

            "name":
                node.get(
                    "name"
                )
        }

        #
        # MERGE METADATA
        #
        metadata = node.get(
            "metadata",
            {}
        )

        properties.update(
            metadata
        )

        #
        # CLEAN NONE VALUES
        #
        properties = {

            k: v
            for k, v
            in properties.items()
            if v is not None
        }

        query = f"""
        MERGE (n:{label} {{
            id: $id
        }})

        SET n += $properties
        """

        session.run(

            query,

            id=node_id,

            properties=properties
        )

    #
    # WRITE RELATIONSHIP
    #
    def _write_relationship(
        self,
        session,
        relationship
    ):

        from_id = (
            relationship["from"]
        )

        to_id = (
            relationship["to"]
        )

        rel_type = (
            relationship["type"]
        )

        properties = (
            relationship.get(
                "metadata",
                {}
            )
        )

        #
        # CLEAN NONE VALUES
        #
        properties = {

            k: v
            for k, v
            in properties.items()
            if v is not None
        }

        query = f"""
        MATCH (a {{
            id: $from_id
        }})

        MATCH (b {{
            id: $to_id
        }})

        MERGE (a)-[r:{rel_type}]->(b)

        SET r += $properties
        """

        session.run(

            query,

            from_id=from_id,

            to_id=to_id,

            properties=properties
        )

    #
    # CLEAR DATABASE
    #
    def clear_database(
        self
    ):

        with self.driver.session() as session:

            session.run(
                """
                MATCH (n)
                DETACH DELETE n
                """
            )

        print(
            "[Neo4jWriter] "
            "Database cleared"
        )

    #
    # CREATE CONSTRAINTS
    #
    def create_constraints(
        self
    ):

        constraints = [

            #
            # FILE
            #
            """
            CREATE CONSTRAINT file_id
            IF NOT EXISTS
            FOR (n:File)
            REQUIRE n.id IS UNIQUE
            """,

            #
            # PACKAGE
            #
            """
            CREATE CONSTRAINT package_id
            IF NOT EXISTS
            FOR (n:Package)
            REQUIRE n.id IS UNIQUE
            """,

            #
            # CLASS
            #
            """
            CREATE CONSTRAINT class_id
            IF NOT EXISTS
            FOR (n:Class)
            REQUIRE n.id IS UNIQUE
            """,

            #
            # INTERFACE
            #
            """
            CREATE CONSTRAINT interface_id
            IF NOT EXISTS
            FOR (n:Interface)
            REQUIRE n.id IS UNIQUE
            """,

            #
            # METHOD
            #
            """
            CREATE CONSTRAINT method_id
            IF NOT EXISTS
            FOR (n:Method)
            REQUIRE n.id IS UNIQUE
            """,

            #
            # FUNCTION
            #
            """
            CREATE CONSTRAINT function_id
            IF NOT EXISTS
            FOR (n:Function)
            REQUIRE n.id IS UNIQUE
            """,

            #
            # FIELD
            #
            """
            CREATE CONSTRAINT field_id
            IF NOT EXISTS
            FOR (n:Field)
            REQUIRE n.id IS UNIQUE
            """,

            #
            # LIBRARY
            #
            """
            CREATE CONSTRAINT library_id
            IF NOT EXISTS
            FOR (n:Library)
            REQUIRE n.id IS UNIQUE
            """
        ]

        with self.driver.session() as session:

            for constraint in constraints:

                try:

                    session.run(
                        constraint
                    )

                except Exception as e:

                    print(
                        "\n"
                        "[Neo4jWriter] "
                        "Constraint error"
                    )

                    print(e)

        print(
            "[Neo4jWriter] "
            "Constraints created"
        )

    #
    # REMOVE DUPLICATES
    #
    def remove_duplicates(
        self
    ):

        labels = [

            "File",

            "Package",

            "Class",

            "Interface",

            "Method",

            "Function",

            "Field",

            "Library"
        ]

        with self.driver.session() as session:

            for label in labels:

                query = f"""
                MATCH (n:{label})

                WITH
                    n.id AS id,
                    collect(n) AS nodes

                WHERE size(nodes) > 1

                FOREACH (
                    node IN tail(nodes) |
                    DETACH DELETE node
                )
                """

                try:

                    session.run(
                        query
                    )

                except Exception as e:

                    print(
                        "\n"
                        "[Neo4jWriter] "
                        "Duplicate cleanup error"
                    )

                    print(
                        label
                    )

                    print(e)

        print(
            "[Neo4jWriter] "
            "Duplicate cleanup complete"
        )

    #
    # GRAPH STATS
    #
    def graph_stats(
        self
    ):

        with self.driver.session() as session:

            #
            # NODE COUNT
            #
            node_result = (
                session.run(
                    """
                    MATCH (n)
                    RETURN count(n) AS count
                    """
                )
            )

            node_count = (
                node_result.single()[
                    "count"
                ]
            )

            #
            # REL COUNT
            #
            rel_result = (
                session.run(
                    """
                    MATCH ()-[r]->()
                    RETURN count(r) AS count
                    """
                )
            )

            rel_count = (
                rel_result.single()[
                    "count"
                ]
            )

            print(
                "\n"
                "[Neo4jWriter] "
                "GRAPH STATS"
            )

            print(
                f"Nodes: {node_count}"
            )

            print(
                f"Relationships: "
                f"{rel_count}"
            )
