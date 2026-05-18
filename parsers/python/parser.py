# parsers/python/parser.py

import ast
from pathlib import Path

from parsers.base_parser import BaseParser

from parsers.common.models import (
    NodeType,
    RelationshipType
)


class PythonParser(BaseParser):

    def parse(self, file_path):

        file_path = Path(file_path)

        with open(
            file_path,
            "r",
            encoding="utf-8",
            errors="ignore"
        ) as f:

            source_code = f.read()

        tree = ast.parse(
            source_code
        )

        file_id = (
            f"python:file:"
            f"{file_path}"
        )

        nodes = []
        relationships = []

        nodes.append({

            "type":
                NodeType.FILE.value,

            "id":
                file_id,

            "name":
                file_path.name
        })

        self._walk(
            tree,
            file_id,
            nodes,
            relationships
        )

        return {

            "nodes":
                self.deduplicate_nodes(
                    nodes
                ),

            "relationships":
                self.deduplicate_relationships(
                    relationships
                )
        }

    def _walk(
        self,
        tree,
        file_id,
        nodes,
        relationships,
        current_class=None,
        current_method=None
    ):

        for node in ast.iter_child_nodes(
            tree
        ):

            #
            # CLASS
            #
            if isinstance(
                node,
                ast.ClassDef
            ):

                class_id = (
                    f"python:"
                    f"{node.name}"
                )

                nodes.append({

                    "type":
                        NodeType
                        .CLASS
                        .value,

                    "id":
                        class_id,

                    "name":
                        node.name,

                    "metadata": {

                        "start_line":
                            node.lineno,

                        "end_line":
                            getattr(
                                node,
                                "end_lineno",
                                node.lineno
                            )
                    }
                })

                relationships.append({

                    "from":
                        file_id,

                    "type":
                        RelationshipType
                        .DECLARES
                        .value,

                    "to":
                        class_id
                })

                self._walk(
                    node,
                    file_id,
                    nodes,
                    relationships,
                    class_id
                )

            #
            # METHOD/FUNCTION
            #
            elif isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef
                )
            ):

                method_name = (
                    node.name
                )

                if current_class:

                    method_id = (
                        f"{current_class}."
                        f"{method_name}"
                    )

                    relationships.append({

                        "from":
                            current_class,

                        "type":
                            RelationshipType
                            .HAS_METHOD
                            .value,

                        "to":
                            method_id
                    })

                    node_type = (
                        NodeType
                        .METHOD
                        .value
                    )

                else:

                    method_id = (
                        f"python:"
                        f"{method_name}"
                    )

                    node_type = (
                        NodeType
                        .FUNCTION
                        .value
                    )

                nodes.append({

                    "type":
                        node_type,

                    "id":
                        method_id,

                    "name":
                        method_name,

                    "metadata": {

                        "start_line":
                            node.lineno,

                        "end_line":
                            getattr(
                                node,
                                "end_lineno",
                                node.lineno
                            )
                    }
                })

                self._walk(
                    node,
                    file_id,
                    nodes,
                    relationships,
                    current_class,
                    method_id
                )

            #
            # CALLS
            #
            elif isinstance(
                node,
                ast.Call
            ):

                if current_method:

                    object_name = None
                    method_name = None

                    #
                    # foo()
                    #
                    if isinstance(
                        node.func,
                        ast.Name
                    ):

                        method_name = (
                            node.func.id
                        )

                    #
                    # repo.save()
                    #
                    elif isinstance(
                        node.func,
                        ast.Attribute
                    ):

                        method_name = (
                            node.func.attr
                        )

                        if isinstance(
                            node.func.value,
                            ast.Name
                        ):

                            object_name = (
                                node
                                .func
                                .value
                                .id
                            )

                    if method_name:

                        if object_name:

                            called_name = (
                                f"{object_name}."
                                f"{method_name}"
                            )

                        else:

                            called_name = (
                                method_name
                            )

                        called_id = (
                            f"python:function:"
                            f"{called_name}"
                        )

                        nodes.append({

                            "type":
                                NodeType
                                .FUNCTION
                                .value,

                            "id":
                                called_id,

                            "name":
                                called_name
                        })

                        relationships.append({

                            "from":
                                current_method,

                            "type":
                                RelationshipType
                                .CALLS
                                .value,

                            "to":
                                called_id,

                            "metadata": {

                                "line_number":
                                    node.lineno
                            }
                        })

                self._walk(
                    node,
                    file_id,
                    nodes,
                    relationships,
                    current_class,
                    current_method
                )

            else:

                self._walk(
                    node,
                    file_id,
                    nodes,
                    relationships,
                    current_class,
                    current_method
                )