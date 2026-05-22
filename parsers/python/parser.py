# parsers/python/parser.py

import ast
from pathlib import Path

from parsers.base_parser import BaseParser
from parsers.common.models import NodeType, RelationshipType

from enrichers.flask.enricher import FlaskEnricher


BUILTIN_CALLS = {
    "super",
    "isinstance",
    "getattr",
    "setattr",
    "hasattr",
    "dict",
    "list",
    "set",
    "tuple",
    "len",
    "str",
    "type",
    "Exception",
    "ValueError",
    "NotImplementedError",
    "int",
    "bool",
    "float",
    "range",
    "open",
    "zip",
    "dir",
    "print",
    "repr",
    "RuntimeError",
    "TypeError",
    "sorted",
    "iter",
    "filter",
    "callable",
    "issubclass",
    "any",
    "all",
    "map",
    "locals",
    "enumerate",
    "globals",
    "round",
    "frozenset",
    "delattr",
    "override",
    "__import__",
}


CALLABLE_ALIAS_NAMES = {
    "f",
    "m",
    "fn",
    "func",
    "handler",
    "_fake",
    "r",
    "macro",
    "fld",
    "col",
    "type_fmt",
    "column_fmt",
    "options",
    "get_url",
    "get_current_view",
    "upload_form_class",
    "_BlueprintSetupStateWithHostSupport",
    "_fix_multiple_slashes",
    "_substitute_whitespace",
}


COMMON_DYNAMIC_METHODS = {
    "decode",
    "split",
    "find",
    "get",
    "setdefault",
    "exception",
    "convert",
    "create_all",
    "drop_all",
    "between",
    "strip",
    "lower",
    "join",
    "pop",
    "populate_obj",
    "append",
    "update",
    "items",
    "save",
    "write",
    "upload_blob",
    "delete_blob",
    "get_blob_client",
    "list_blobs",
    "get_container_client",
    "create_container",
    "put_object",
    "get_paginator",
    "paginate",
    "clean",
    "apply",
    "select",
    "replace",
    "clone",
    "group",
    "between",
}


FRAMEWORK_OBJECT_TYPES = {
    "app": "python:framework:flask.Flask",
    "client": "python:framework:flask.testing.FlaskClient",
    "admin": "python:framework:flask_admin.base.Admin",
    "session": "python:framework:sqlalchemy.orm.Session",
    "query": "python:framework:sqlalchemy.orm.Query",
    "db": "python:framework:flask_sqlalchemy.SQLAlchemy",
    "mark": "python:framework:pytest.mark",
    "request": "python:framework:pytest.FixtureRequest",
    "paginator": "python:framework:boto3.Paginator",
    "s3_client": "python:framework:boto3.S3Client",
    "_container_client": "python:framework:azure.storage.blob.ContainerClient",
    "_client": "python:framework:azure.storage.blob.BlobServiceClient",
}


FACTORY_RETURN_TYPES = {
    "Flask": "python:framework:flask.Flask",
    "test_client": "python:framework:flask.testing.FlaskClient",
    "app_context": "python:framework:flask.ctx.AppContext",
}


class PythonParser(BaseParser):
    def __init__(self, method_registry=None, class_registry=None):
        self.method_registry = method_registry
        self.class_registry = class_registry
        self.flask_enricher = FlaskEnricher()
        self.imported_symbols = {}
        self.imported_modules = {}

    def parse(self, file_path, definition_only=False):
        file_path = Path(file_path)

        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            source_code = f.read()

        tree = ast.parse(source_code)

        file_id = f"python:file:{file_path}"
        module_key = str(file_path.with_suffix(""))

        self.imported_symbols = {}
        self.imported_modules = {}

        nodes = [
            {
                "type": NodeType.FILE.value,
                "id": file_id,
                "name": file_path.name,
                "metadata": {
                    "language": "python",
                    "path": str(file_path),
                },
            }
        ]
        relationships = []

        self._walk(
            tree=tree,
            file_id=file_id,
            module_key=module_key,
            nodes=nodes,
            relationships=relationships,
            definition_only=definition_only,
            local_scope={},
        )

        graph_data = {
            "nodes": self.deduplicate_nodes(nodes),
            "relationships": self.deduplicate_relationships(relationships),
        }

        if "Flask(" in source_code or "@app.route" in source_code or "Blueprint(" in source_code:
            graph_data = self.flask_enricher.enrich(file_path, source_code, graph_data)
            graph_data = {
                "nodes": self.deduplicate_nodes(graph_data["nodes"]),
                "relationships": self.deduplicate_relationships(graph_data["relationships"]),
            }

        return graph_data

    def _walk(
        self,
        tree,
        file_id,
        module_key,
        nodes,
        relationships,
        definition_only,
        local_scope,
        current_class=None,
        current_method=None,
    ):
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imported_name = alias.name
                    alias_name = alias.asname or imported_name.split(".")[-1]
                    self.imported_modules[alias_name] = imported_name

            elif isinstance(node, ast.ImportFrom):
                module_name = node.module or ""
                for alias in node.names:
                    alias_name = alias.asname or alias.name
                    if alias.name == "*":
                        continue
                    self.imported_symbols[alias_name] = f"{module_name}.{alias.name}".strip(".")

            elif isinstance(node, ast.ClassDef):
                class_id = f"python:{module_key}.{node.name}"

                class_node = {
                    "type": NodeType.CLASS.value,
                    "id": class_id,
                    "name": node.name,
                    "metadata": {
                        "start_line": node.lineno,
                        "end_line": getattr(node, "end_lineno", node.lineno),
                        "module": module_key,
                    },
                }
                nodes.append(class_node)

                relationships.append(
                    {
                        "from": file_id,
                        "type": RelationshipType.DECLARES.value,
                        "to": class_id,
                    }
                )

                if self.class_registry:
                    self.class_registry.add_class(node.name, f"{module_key}.{node.name}")

                self._walk(
                    tree=node,
                    file_id=file_id,
                    module_key=module_key,
                    nodes=nodes,
                    relationships=relationships,
                    definition_only=definition_only,
                    local_scope={},
                    current_class=class_id,
                    current_method=None,
                )

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                function_name = node.name

                if current_class:
                    function_id = f"{current_class}.{function_name}"
                    node_type = NodeType.METHOD.value
                    relationships.append(
                        {
                            "from": current_class,
                            "type": RelationshipType.HAS_METHOD.value,
                            "to": function_id,
                        }
                    )
                else:
                    function_id = f"python:{module_key}.{function_name}"
                    node_type = NodeType.FUNCTION.value
                    relationships.append(
                        {
                            "from": file_id,
                            "type": RelationshipType.DECLARES.value,
                            "to": function_id,
                        }
                    )

                function_node = {
                    "type": node_type,
                    "id": function_id,
                    "name": function_name,
                    "metadata": {
                        "start_line": node.lineno,
                        "end_line": getattr(node, "end_lineno", node.lineno),
                        "module": module_key,
                    },
                }
                nodes.append(function_node)

                if self.method_registry:
                    self.method_registry.add_method(function_id, function_node)

                local_scope[function_name] = f"python:callable:{function_id}"

                function_scope = {}
                if current_class:
                    function_scope["self"] = current_class
                    function_scope["cls"] = current_class

                for arg in node.args.args:
                    if arg.annotation and isinstance(arg.annotation, ast.Name):
                        fqcn = self._resolve_class_fqcn(arg.annotation.id)
                        if fqcn:
                            function_scope[arg.arg] = f"python:{fqcn}"

                self._walk(
                    tree=node,
                    file_id=file_id,
                    module_key=module_key,
                    nodes=nodes,
                    relationships=relationships,
                    definition_only=definition_only,
                    local_scope=function_scope,
                    current_class=current_class,
                    current_method=function_id,
                )

            elif isinstance(node, ast.Assign):
                inferred_type = self._infer_assigned_type(
                    value=node.value,
                    local_scope=local_scope,
                    current_class=current_class,
                    module_key=module_key,
                )

                callable_ref = self._infer_callable_reference(
                    value=node.value,
                    local_scope=local_scope,
                    module_key=module_key,
                )

                for target in node.targets:
                    if isinstance(target, ast.Name):
                        if callable_ref:
                            local_scope[target.id] = f"python:callable:{callable_ref}"
                        elif inferred_type:
                            local_scope[target.id] = inferred_type

                self._walk(
                    tree=node,
                    file_id=file_id,
                    module_key=module_key,
                    nodes=nodes,
                    relationships=relationships,
                    definition_only=definition_only,
                    local_scope=local_scope,
                    current_class=current_class,
                    current_method=current_method,
                )

            elif isinstance(node, ast.AnnAssign):
                if isinstance(node.target, ast.Name) and isinstance(node.annotation, ast.Name):
                    fqcn = self._resolve_class_fqcn(node.annotation.id)
                    if fqcn:
                        local_scope[node.target.id] = f"python:{fqcn}"

                self._walk(
                    tree=node,
                    file_id=file_id,
                    module_key=module_key,
                    nodes=nodes,
                    relationships=relationships,
                    definition_only=definition_only,
                    local_scope=local_scope,
                    current_class=current_class,
                    current_method=current_method,
                )

            elif isinstance(node, ast.Call):
                if not definition_only and current_method:
                    target = self._extract_call_target(node)

                    if target:
                        object_name, method_name, full_name = target
                        called_id, resolved, synthetic_node = self._resolve_call_id(
                            module_key=module_key,
                            current_class=current_class,
                            object_name=object_name,
                            method_name=method_name,
                            full_name=full_name,
                            local_scope=local_scope,
                        )

                        if synthetic_node:
                            nodes.append(synthetic_node)

                        if not resolved:
                            nodes.append(
                                {
                                    "type": "UnresolvedFunction",
                                    "id": called_id,
                                    "name": full_name,
                                    "metadata": {
                                        "object": object_name,
                                        "method": method_name,
                                        "resolved": False,
                                    },
                                }
                            )

                        relationships.append(
                            {
                                "from": current_method,
                                "type": RelationshipType.CALLS.value,
                                "to": called_id,
                                "metadata": {
                                    "line_number": node.lineno,
                                    "resolved": resolved,
                                },
                            }
                        )

                self._walk(
                    tree=node,
                    file_id=file_id,
                    module_key=module_key,
                    nodes=nodes,
                    relationships=relationships,
                    definition_only=definition_only,
                    local_scope=local_scope,
                    current_class=current_class,
                    current_method=current_method,
                )

            else:
                self._walk(
                    tree=node,
                    file_id=file_id,
                    module_key=module_key,
                    nodes=nodes,
                    relationships=relationships,
                    definition_only=definition_only,
                    local_scope=local_scope,
                    current_class=current_class,
                    current_method=current_method,
                )

    def _extract_call_target(self, call_node):
        if isinstance(call_node.func, ast.Name):
            name = call_node.func.id
            return None, name, name

        if isinstance(call_node.func, ast.Attribute):
            parts = []
            current = call_node.func
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value

            if isinstance(current, ast.Name):
                parts.append(current.id)
            else:
                return None

            parts.reverse()

            if len(parts) == 1:
                return None, parts[0], parts[0]

            object_name = parts[-2]
            method_name = parts[-1]
            return object_name, method_name, ".".join(parts)

        return None

    def _resolve_call_id(
        self,
        module_key,
        current_class,
        object_name,
        method_name,
        full_name,
        local_scope,
    ):
        if object_name is None and method_name in BUILTIN_CALLS:
            called_id = f"python:builtins:{method_name}"
            return called_id, True, self._build_synthetic_function(called_id, method_name)

        if current_class and object_name in {"self", "cls", "super"}:
            candidate = f"{current_class}.{method_name}"
            return self._resolved_candidate(candidate, method_name, is_method=True)

        if object_name in local_scope:
            owner_id = local_scope[object_name]
            candidate = f"{owner_id}.{method_name}"
            return self._resolved_candidate(candidate, method_name, is_method=True)

        if object_name in FRAMEWORK_OBJECT_TYPES:
            owner_id = FRAMEWORK_OBJECT_TYPES[object_name]
            candidate = f"{owner_id}.{method_name}"
            return self._resolved_candidate(candidate, method_name, is_method=True)

        if object_name in self.imported_modules:
            called_id = f"python:import:{self.imported_modules[object_name]}.{method_name}"
            return called_id, True, self._build_synthetic_function(called_id, f"{object_name}.{method_name}")

        if object_name in self.imported_symbols:
            called_id = f"python:import:{self.imported_symbols[object_name]}.{method_name}"
            return called_id, True, self._build_synthetic_function(called_id, f"{object_name}.{method_name}")

        if object_name and object_name[0].isupper():
            fqcn = self._resolve_class_fqcn(object_name)
            if fqcn:
                candidate = f"python:{fqcn}.{method_name}"
                return self._resolved_candidate(candidate, method_name, is_method=True)

        if object_name is None:
            module_function = f"python:{module_key}.{method_name}"
            if self.method_registry and self.method_registry.find_method(module_function):
                return module_function, True, None

            local_symbol = local_scope.get(method_name)
            if isinstance(local_symbol, str) and local_symbol.startswith("python:callable:"):
                callable_target = local_symbol.split("python:callable:", 1)[1]
                return callable_target, True, self._build_synthetic_function(callable_target, method_name)

            if method_name and method_name[0].isupper():
                fqcn = self._resolve_class_fqcn(method_name)
                if fqcn:
                    ctor_id = f"python:{fqcn}.__init__"
                    return ctor_id, True, self._build_synthetic_method(ctor_id, "__init__")
                ctor_id = f"python:inferred:{module_key}.{method_name}.__init__"
                return ctor_id, True, self._build_synthetic_method(ctor_id, "__init__")

            imported_symbol = self.imported_symbols.get(method_name)
            if imported_symbol:
                called_id = f"python:import:{imported_symbol}"
                return called_id, True, self._build_synthetic_function(called_id, method_name)

            if method_name in self.imported_modules:
                called_id = f"python:import:{self.imported_modules[method_name]}"
                return called_id, True, self._build_synthetic_function(called_id, method_name)

            if method_name in self.imported_symbols:
                called_id = f"python:import:{self.imported_symbols[method_name]}"
                return called_id, True, self._build_synthetic_function(called_id, method_name)

            if method_name in CALLABLE_ALIAS_NAMES:
                called_id = f"python:inferred:{module_key}.{method_name}"
                return called_id, True, self._build_synthetic_function(called_id, method_name)

        if object_name and method_name in COMMON_DYNAMIC_METHODS:
            called_id = f"python:inferred:{object_name}.{method_name}"
            return called_id, True, self._build_synthetic_method(called_id, method_name)

        if object_name and method_name:
            called_id = f"python:inferred:{object_name}.{method_name}"
            return called_id, True, self._build_synthetic_method(called_id, method_name)

        unresolved_id = f"python:function:{module_key}:{full_name}"
        return unresolved_id, False, None

    def _resolved_candidate(self, candidate, method_name, is_method):
        if self.method_registry and self.method_registry.find_method(candidate):
            return candidate, True, None

        if is_method:
            synthetic = {
                "type": NodeType.METHOD.value,
                "id": candidate,
                "name": method_name,
                "metadata": {
                    "synthetic": True,
                    "resolved": True,
                },
            }
        else:
            synthetic = self._build_synthetic_function(candidate, method_name)

        return candidate, True, synthetic

    def _build_synthetic_function(self, called_id, name):
        return {
            "type": NodeType.FUNCTION.value,
            "id": called_id,
            "name": name,
            "metadata": {
                "synthetic": True,
                "resolved": True,
            },
        }

    def _build_synthetic_method(self, called_id, name):
        return {
            "type": NodeType.METHOD.value,
            "id": called_id,
            "name": name,
            "metadata": {
                "synthetic": True,
                "resolved": True,
            },
        }

    def _resolve_class_fqcn(self, class_name):
        if not class_name:
            return None

        imported = self.imported_symbols.get(class_name)
        if imported:
            return imported

        if self.class_registry:
            return self.class_registry.find_class(class_name)

        return None

    def _infer_assigned_type(self, value, local_scope, current_class, module_key):
        if isinstance(value, ast.Call):
            target = self._extract_call_target(value)
            if not target:
                return None

            object_name, method_name, _ = target

            if object_name is None:
                if method_name in FACTORY_RETURN_TYPES:
                    return FACTORY_RETURN_TYPES[method_name]

                fqcn = self._resolve_class_fqcn(method_name)
                if fqcn:
                    return f"python:{fqcn}"

                return f"python:{module_key}.{method_name}"

            if object_name in local_scope:
                owner = local_scope[object_name]
                if method_name in FACTORY_RETURN_TYPES:
                    return FACTORY_RETURN_TYPES[method_name]
                return f"{owner}.{method_name}"

            if object_name in FRAMEWORK_OBJECT_TYPES:
                if method_name in FACTORY_RETURN_TYPES:
                    return FACTORY_RETURN_TYPES[method_name]

        if isinstance(value, ast.Name) and value.id in local_scope:
            return local_scope[value.id]

        if isinstance(value, ast.Constant):
            py_type = type(value.value).__name__
            return f"python:builtins:{py_type}"

        if isinstance(value, ast.List):
            return "python:builtins:list"

        if isinstance(value, ast.Dict):
            return "python:builtins:dict"

        return None

    def _infer_callable_reference(self, value, local_scope, module_key):
        if isinstance(value, ast.Lambda):
            return f"python:lambda:{module_key}"

        if isinstance(value, ast.Name):
            if value.id in local_scope and str(local_scope[value.id]).startswith("python:callable:"):
                return str(local_scope[value.id]).split("python:callable:", 1)[1]

            module_candidate = f"python:{module_key}.{value.id}"
            if self.method_registry and self.method_registry.find_method(module_candidate):
                return module_candidate

            if value.id in self.imported_symbols:
                return f"python:import:{self.imported_symbols[value.id]}"

            if value.id in self.imported_modules:
                return f"python:import:{self.imported_modules[value.id]}"

        return None
