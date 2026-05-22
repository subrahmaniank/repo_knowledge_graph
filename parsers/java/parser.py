# parsers/java/parser.py

from pathlib import Path

from tree_sitter import Language, Parser
import tree_sitter_java as tsjava

from parsers.base_parser import BaseParser

from parsers.common.models import (
    NodeType,
    RelationshipType,
)

from graph.symbol_resolution.java_resolver import (
    JavaResolver,
)

from graph.symbol_resolution.expression_resolver import (
    JavaExpressionResolver,
)

from enrichers.spring.enricher import (
    SpringBootEnricher,
)


JAVA_LANGUAGE = Language(tsjava.language())


JAVA_STD_LIB_METHODS = {
    #
    # STREAMS
    #
    "stream",
    "map",
    "filter",
    "collect",
    "toList",
    "forEach",
    #
    # BUILDERS
    #
    "builder",
    "build",
    "of",
    "empty",
    #
    # ASSERTIONS
    #
    "assertThat",
    "isNotNull",
    "isEqualTo",
    "isInstanceOf",
    "assertThatThrownBy",
    #
    # MOCKITO
    #
    "verify",
    "any",
    #
    # COMMON JAVA
    #
    "append",
    "isBlank",
    #
    # UUID
    #
    "randomUUID",
}


JAVA_OBJECT_METHODS = {
    "equals",
    "hashCode",
    "toString",
    "clone",
    "notify",
    "wait",
    "getClass",
}


class JavaParser(BaseParser):
    def __init__(
        self, symbol_table, import_resolver, method_registry=None, class_registry=None
    ):

        self.parser = Parser(JAVA_LANGUAGE)

        self.symbol_table = symbol_table

        self.import_resolver = import_resolver

        self.method_registry = method_registry

        self.class_registry = class_registry

        self.java_resolver = JavaResolver(
            symbol_table, import_resolver, class_registry, method_registry
        )

        self.expression_resolver = JavaExpressionResolver()

        self.spring_enricher = SpringBootEnricher()

    #
    # PARSE
    #
    def parse(self, file_path, definition_only=False):

        file_path = Path(file_path)

        print(f"\n[JavaParser] Parsing: {file_path}")

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            source_code = f.read()

        source_bytes = source_code.encode("utf8")

        tree = self.parser.parse(source_bytes)

        root = tree.root_node

        current_package = self._extract_package(root, source_bytes)

        nodes = []
        relationships = []

        file_id = f"java:file:{file_path}"

        #
        # FILE NODE
        #
        nodes.append(
            {
                "type": NodeType.FILE.value,
                "id": file_id,
                "name": file_path.name,
                "metadata": {"path": str(file_path), "language": "java"},
            }
        )

        #
        # WALK TREE
        #
        self._walk_tree(
            node=root,
            source_bytes=source_bytes,
            file_id=file_id,
            nodes=nodes,
            relationships=relationships,
            current_package=current_package,
            current_class=None,
            current_method=None,
            definition_only=definition_only,
        )

        nodes = self.deduplicate_nodes(nodes)

        relationships = self.deduplicate_relationships(relationships)

        print(f"[JavaParser] Nodes: {len(nodes)}")

        print(f"[JavaParser] Relationships: {len(relationships)}")

        return {"nodes": nodes, "relationships": relationships}

    #
    # EXTRACT TYPE NODE
    #
    def _extract_type_node(self, node, source_bytes):

        for child in node.children:
            if "type" in child.type:
                return self._text(source_bytes, child)

        return None

    def _extract_package(self, root, source_bytes):

        for child in root.children:
            if child.type == "package_declaration":
                return (
                    self._text(source_bytes, child)
                    .replace("package", "")
                    .replace(";", "")
                    .strip()
                )

        return ""

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
        current_package,
        current_class,
        current_method,
        definition_only=False,
    ):

        node_type = node.type

        #
        # PACKAGE
        #
        if node_type == "package_declaration":
            current_package = (
                self._text(source_bytes, node)
                .replace("package", "")
                .replace(";", "")
                .strip()
            )

        #
        # IMPORT
        #
        elif node_type == "import_declaration":
            import_name = (
                self._text(source_bytes, node)
                .replace("import", "")
                .replace(";", "")
                .strip()
            )

            self.import_resolver.add_import(file_id, import_name)

        #
        # CLASS / INTERFACE
        #
        elif node_type in ["class_declaration", "interface_declaration"]:
            name_node = node.child_by_field_name("name")

            if name_node:
                class_name = self._text(source_bytes, name_node)

                fqcn = f"{current_package}.{class_name}"

                class_id = f"java:{fqcn}"

                current_class = class_id

                #
                # REGISTER CLASS
                #
                self.class_registry.add_class(class_name, fqcn)

                class_node = {
                    "type": (
                        "Interface" if node_type == "interface_declaration" else "Class"
                    ),
                    "id": class_id,
                    "name": class_name,
                    "metadata": {},
                }

                nodes.append(class_node)

                #
                # SPRING ENRICHMENT
                #
                enriched = self.spring_enricher.enrich(
                    class_node, nodes, relationships, self.method_registry
                )

                nodes = enriched["nodes"]

                relationships = enriched["relationships"]

        #
        # FIELD DECLARATION
        #
        elif node_type == "field_declaration":
            if current_class:
                field_type = self._extract_type_node(node, source_bytes)

                for child in node.children:
                    if child.type == "variable_declarator":
                        name_node = child.child_by_field_name("name")

                        if name_node:
                            field_name = self._text(source_bytes, name_node)

                            #
                            # REGISTER FIELD
                            #
                            self.symbol_table.add_variable(
                                current_class, field_name, field_type
                            )

                            #
                            # SYNTHETIC ACCESSORS
                            #
                            self._generate_accessor_methods(
                                nodes, relationships, current_class, field_name
                            )

        #
        # METHOD
        #
        elif node_type == "method_declaration":
            if current_class:
                name_node = node.child_by_field_name("name")

                if name_node:
                    method_name = self._text(source_bytes, name_node)

                    method_id = f"{current_class}.{method_name}"

                    current_method = method_id

                    method_node = {
                        "type": "Method",
                        "id": method_id,
                        "name": method_name,
                        "metadata": {},
                    }

                    nodes.append(method_node)

                    relationships.append(
                        {"from": current_class, "type": "HAS_METHOD", "to": method_id}
                    )

                    #
                    # REGISTER METHOD
                    #
                    self.method_registry.add_method(method_id, method_node)

        #
        # FORMAL PARAMETER
        #
        elif node_type == "formal_parameter":
            if current_method:
                param_type = self._extract_type_node(node, source_bytes)

                name_node = node.child_by_field_name("name")

                if param_type and name_node:
                    param_name = self._text(source_bytes, name_node)

                    self.symbol_table.add_variable(
                        current_method, param_name, param_type
                    )

        #
        # CATCH PARAMETER
        #
        elif node_type == "catch_formal_parameter":
            if current_method:
                exception_type = self._extract_type_node(node, source_bytes)

                name_node = node.child_by_field_name("name")

                if not name_node:
                    for child in node.children:
                        if child.type == "identifier":
                            name_node = child
                            break

                if exception_type and name_node:
                    exception_name = self._text(source_bytes, name_node)

                    self.symbol_table.add_variable(
                        current_method,
                        exception_name,
                        exception_type,
                    )

        #
        # LOCAL VARIABLE
        #
        elif node_type == "local_variable_declaration":
            if current_method:
                variable_type = self._extract_type_node(node, source_bytes)

                for child in node.children:
                    if child.type == "variable_declarator":
                        name_node = child.child_by_field_name("name")

                        if name_node:
                            variable_name = self._text(source_bytes, name_node)

                            self.symbol_table.add_variable(
                                current_method, variable_name, variable_type
                            )

        #
        # FIELD ACCESS
        #
        elif node_type == "field_access":
            if definition_only:
                return

            object_node = node.child_by_field_name("object")

            field_node = node.child_by_field_name("field")

            if object_node and field_node:
                object_name = self._text(source_bytes, object_node)

                field_name = self._text(source_bytes, field_node)

                #
                # OPTIONAL:
                # CREATE FIELD ACCESS EDGE
                #
                relationships.append(
                    {
                        "from": current_method,
                        "type": "ACCESSES",
                        "to": f"{object_name}.{field_name}",
                        "metadata": {"line_number": (node.start_point[0] + 1)},
                    }
                )

        #
        # METHOD INVOCATION
        #
        elif node_type == "method_invocation":
            #
            # PASS 1:
            # INDEXING ONLY
            #
            if definition_only:
                return

            if current_method:
                object_node = node.child_by_field_name("object")

                method_node = node.child_by_field_name("name")

                object_name = None
                method_name = None

                #
                # OBJECT
                #
                if object_node:
                    object_name = self.expression_resolver.extract_root_object(
                        object_node, source_bytes, self._text
                    )

                #
                # METHOD
                #
                if method_node:
                    method_name = self._text(source_bytes, method_node)

                #
                # IGNORE STDLIB
                #
                skip_resolution = False

                if method_name in JAVA_STD_LIB_METHODS:
                    skip_resolution = True

                if method_name in JAVA_OBJECT_METHODS:
                    skip_resolution = True

                #
                # IMPORTANT:
                # DO NOT RETURN
                #
                if not skip_resolution:
                    resolved_call = None
                    existing_method = None

                    #
                    # SAME CLASS
                    #
                    if not object_name and method_name:
                        candidate = f"{current_class}.{method_name}"

                        existing_method = self.method_registry.find_method(candidate)

                        if existing_method:
                            resolved_call = candidate
                        else:
                            imported_static = self.import_resolver.resolve_import(
                                file_id,
                                method_name,
                            )

                            if imported_static:
                                resolved_call = f"java:{imported_static}"
                                existing_method = self.method_registry.find_method(
                                    resolved_call
                                )
                            else:
                                static_candidates = (
                                    self.import_resolver.resolve_static_wildcard_candidates(
                                        file_id,
                                        method_name,
                                    )
                                )

                                for candidate_fq in static_candidates:
                                    wildcard_candidate = f"java:{candidate_fq}"
                                    existing_method = self.method_registry.find_method(
                                        wildcard_candidate
                                    )

                                    if existing_method:
                                        resolved_call = wildcard_candidate
                                        break

                    #
                    # NORMAL RESOLUTION
                    #
                    elif object_name and method_name:
                        resolved_call = self.java_resolver.resolve_call(
                            file_id,
                            current_class,
                            current_method,
                            object_name,
                            method_name,
                        )

                        if resolved_call:
                            existing_method = self.method_registry.find_method(
                                resolved_call
                            )

                    #
                    # RESOLVED (EXISTING METHOD)
                    #
                    if existing_method:
                        called_id = existing_method["id"]

                        resolved = True

                    #
                    # RESOLVED (TYPE KNOWN, METHOD NOT INDEXED)
                    #
                    elif resolved_call:
                        called_id = resolved_call

                        resolved = True

                        synthetic_method = {
                            "type": "Method",
                            "id": called_id,
                            "name": method_name,
                            "metadata": {
                                "synthetic": True,
                                "inferred": True,
                                "resolution": "type_based",
                                "object": object_name,
                            },
                        }

                        nodes.append(synthetic_method)

                        self.method_registry.add_method(
                            called_id,
                            synthetic_method,
                        )

                    #
                    # UNRESOLVED
                    #
                    else:
                        called_name = (
                            f"{object_name}.{method_name}"
                            if object_name
                            else method_name
                        )

                        called_id = f"java:function:{called_name}"

                        resolved = False

                        nodes.append(
                            {
                                "type": "UnresolvedFunction",
                                "id": called_id,
                                "name": called_name,
                                "metadata": {
                                    "object": object_name,
                                    "method": method_name,
                                    "resolved": False,
                                },
                            }
                        )

                    #
                    # CALL RELATIONSHIP
                    #
                    relationships.append(
                        {
                            "from": current_method,
                            "type": RelationshipType.CALLS.value,
                            "to": called_id,
                            "metadata": {
                                "resolved": resolved,
                                "line_number": (node.start_point[0] + 1),
                            },
                        }
                    )

        #
        # RECURSE
        #
        for child in node.children:
            self._walk_tree(
                node=child,
                source_bytes=source_bytes,
                file_id=file_id,
                nodes=nodes,
                relationships=relationships,
                current_package=current_package,
                current_class=current_class,
                current_method=current_method,
                definition_only=definition_only,
            )

    #
    # SYNTHETIC ACCESSORS
    #
    def _generate_accessor_methods(
        self, nodes, relationships, current_class, field_name
    ):

        capitalized = field_name[0].upper() + field_name[1:]

        methods = [f"get{capitalized}", f"is{capitalized}", f"set{capitalized}"]

        for method_name in methods:
            method_id = f"{current_class}.{method_name}"

            method_node = {
                "type": "Method",
                "id": method_id,
                "name": method_name,
                "metadata": {"synthetic": True},
            }

            nodes.append(method_node)

            relationships.append(
                {"from": current_class, "type": "HAS_METHOD", "to": method_id}
            )

            self.method_registry.add_method(method_id, method_node)

    #
    # TEXT
    #
    def _text(self, source_bytes, node):

        return source_bytes[node.start_byte : node.end_byte].decode(
            "utf8", errors="ignore"
        )
