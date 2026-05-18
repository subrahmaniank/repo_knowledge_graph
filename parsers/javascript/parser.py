# parsers/javascript/parser.py

from pathlib import Path

from tree_sitter import (
    Language,
    Parser
)

import tree_sitter_javascript as tsjs

from parsers.base_parser import BaseParser

from parsers.common.models import (
    NodeType,
    RelationshipType
)


JS_LANGUAGE = Language(
    tsjs.language()
)


class JavaScriptParser(BaseParser):

    def __init__(self):

        self.parser = Parser(
            JS_LANGUAGE
        )

    #
    # MAIN PARSE
    #
    def parse(self, file_path):

        file_path = Path(file_path)

        with open(
            file_path,
            "r",
            encoding="utf-8",
            errors="ignore"
        ) as f:

            source_code = f.read()

        source_bytes = (
            source_code.encode("utf8")
        )

        tree = self.parser.parse(
            source_bytes
        )

        root = tree.root_node

        file_id = (
            f"javascript:file:"
            f"{file_path}"
        )

        nodes = []
        relationships = []

        #
        # FILE NODE
        #
        nodes.append({

            "type":
                NodeType.FILE.value,

            "id":
                file_id,

            "name":
                file_path.name,

            "metadata": {

                "language":
                    "javascript",

                "path":
                    str(file_path)
            }
        })

        #
        # WALK TREE
        #
        self._walk_tree(
            root,
            source_bytes,
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

    #
    # WALK TREE
    #
    def _walk_tree(
        self,
        node,
        source_bytes,
        file_id,
        nodes,
        relationships,
        current_function=None,
        current_class=None
    ):

        node_type = node.type

        #
        # IMPORTS
        #
        if node_type == "import_statement":

            import_text = (
                self._text(
                    source_bytes,
                    node
                )
            )

            library_id = (
                f"javascript:library:"
                f"{import_text}"
            )

            nodes.append({

                "type":
                    NodeType
                    .LIBRARY
                    .value,

                "id":
                    library_id,

                "name":
                    import_text
            })

            relationships.append({

                "from":
                    file_id,

                "type":
                    RelationshipType
                    .IMPORTS
                    .value,

                "to":
                    library_id
            })

        #
        # CLASS
        #
        elif (
            node_type
            == "class_declaration"
        ):

            name_node = (
                node.child_by_field_name(
                    "name"
                )
            )

            if name_node:

                class_name = (
                    self._text(
                        source_bytes,
                        name_node
                    )
                )

                class_id = (
                    f"javascript:"
                    f"{class_name}"
                )

                nodes.append({

                    "type":
                        NodeType
                        .CLASS
                        .value,

                    "id":
                        class_id,

                    "name":
                        class_name,

                    "metadata": {

                        "language":
                            "javascript",

                        **self._position(
                            node
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

                current_class = (
                    class_id
                )

        #
        # FUNCTIONS
        #
        elif (
            node_type
            == "function_declaration"
        ):

            name_node = (
                node.child_by_field_name(
                    "name"
                )
            )

            if name_node:

                function_name = (
                    self._text(
                        source_bytes,
                        name_node
                    )
                )

                #
                # CLASS METHOD
                #
                if current_class:

                    function_id = (
                        f"{current_class}."
                        f"{function_name}"
                    )

                    relationships.append({

                        "from":
                            current_class,

                        "type":
                            RelationshipType
                            .HAS_METHOD
                            .value,

                        "to":
                            function_id
                    })

                    node_type_name = (
                        NodeType
                        .METHOD
                        .value
                    )

                #
                # TOP LEVEL FUNCTION
                #
                else:

                    function_id = (
                        f"javascript:"
                        f"{function_name}"
                    )

                    relationships.append({

                        "from":
                            file_id,

                        "type":
                            RelationshipType
                            .DECLARES
                            .value,

                        "to":
                            function_id
                    })

                    node_type_name = (
                        NodeType
                        .FUNCTION
                        .value
                    )

                nodes.append({

                    "type":
                        node_type_name,

                    "id":
                        function_id,

                    "name":
                        function_name,

                    "metadata": {

                        "language":
                            "javascript",

                        **self._position(
                            node
                        )
                    }
                })

                current_function = (
                    function_id
                )

        #
        # METHOD DEFINITIONS
        #
        elif (
            node_type
            == "method_definition"
        ):

            if current_class:

                name_node = (
                    node.child_by_field_name(
                        "name"
                    )
                )

                if name_node:

                    method_name = (
                        self._text(
                            source_bytes,
                            name_node
                        )
                    )

                    method_id = (
                        f"{current_class}."
                        f"{method_name}"
                    )

                    nodes.append({

                        "type":
                            NodeType
                            .METHOD
                            .value,

                        "id":
                            method_id,

                        "name":
                            method_name,

                        "metadata": {

                            "language":
                                "javascript",

                            **self._position(
                                node
                            )
                        }
                    })

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

                    current_function = (
                        method_id
                    )

        #
        # CALL EXPRESSIONS
        #
        elif (
            node_type
            == "call_expression"
        ):

            if current_function:

                function_node = (
                    node.child_by_field_name(
                        "function"
                    )
                )

                object_name = None
                method_name = None

                #
                # repo.save()
                #
                if (
                    function_node
                    and function_node.type
                    == "member_expression"
                ):

                    object_node = (
                        function_node
                        .child_by_field_name(
                            "object"
                        )
                    )

                    property_node = (
                        function_node
                        .child_by_field_name(
                            "property"
                        )
                    )

                    if object_node:

                        object_name = (
                            self._text(
                                source_bytes,
                                object_node
                            )
                        )

                    if property_node:

                        method_name = (
                            self._text(
                                source_bytes,
                                property_node
                            )
                        )

                #
                # foo()
                #
                elif function_node:

                    method_name = (
                        self._text(
                            source_bytes,
                            function_node
                        )
                    )

                #
                # BUILD CALL
                #
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
                        f"javascript:function:"
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
                            called_name,

                        "metadata": {

                            "language":
                                "javascript",

                            "object":
                                object_name,

                            "method":
                                method_name,

                            "line_number":
                                (
                                    node
                                    .start_point[0]
                                    + 1
                                )
                        }
                    })

                    relationships.append({

                        "from":
                            current_function,

                        "type":
                            RelationshipType
                            .CALLS
                            .value,

                        "to":
                            called_id,

                        "metadata": {

                            "line_number":
                                (
                                    node
                                    .start_point[0]
                                    + 1
                                )
                        }
                    })

        #
        # RECURSION
        #
        for child in node.children:

            self._walk_tree(
                child,
                source_bytes,
                file_id,
                nodes,
                relationships,
                current_function,
                current_class
            )

    #
    # NODE TEXT
    #
    def _text(
        self,
        source_bytes,
        node
    ):

        return source_bytes[
            node.start_byte:
            node.end_byte
        ].decode(
            "utf8",
            errors="ignore"
        )

    #
    # POSITION
    #
    def _position(
        self,
        node
    ):

        return {

            "start_line":
                node.start_point[0] + 1,

            "end_line":
                node.end_point[0] + 1
        }