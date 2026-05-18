# graph/neo4j_writer.py

from neo4j import GraphDatabase


class Neo4jWriter:

    def __init__(
        self,
        uri,
        username,
        password
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

            #
            # WRITE NODES
            #
            for node in nodes:

                try:

                    self._write_node(
                        session,
                        node
                    )

                except Exception as e:

                    print(
                        "\n[Neo4jWriter] "
                        "NODE ERROR"
                    )

                    print(node)

                    print(e)

            #
            # WRITE RELATIONSHIPS
            #
            for relationship in relationships:

                try:

                    self._write_relationship(
                        session,
                        relationship
                    )

                except Exception as e:

                    print(
                        "\n[Neo4jWriter] "
                        "RELATIONSHIP ERROR"
                    )

                    print(
                        relationship
                    )

                    print(e)

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