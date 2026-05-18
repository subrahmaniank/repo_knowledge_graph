# parsers/base_parser.py

class BaseParser:

    def deduplicate_nodes(
        self,
        nodes
    ):

        unique = {}

        for node in nodes:

            unique[
                node["id"]
            ] = node

        return list(
            unique.values()
        )

    def deduplicate_relationships(
        self,
        relationships
    ):

        unique = {}

        for rel in relationships:

            key = (

                rel["from"],

                rel["type"],

                rel["to"]
            )

            unique[key] = rel

        return list(
            unique.values()
        )