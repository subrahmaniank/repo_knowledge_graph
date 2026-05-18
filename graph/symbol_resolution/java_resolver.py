# graph/symbol_resolution/java_resolver.py


class JavaResolver:
    def __init__(self, symbol_table, import_resolver, class_registry, method_registry):

        self.symbol_table = symbol_table

        self.import_resolver = import_resolver

        self.class_registry = class_registry

        self.method_registry = method_registry

    #
    # NORMALIZE TYPE
    #
    def _normalize_type(self, variable_type):

        if not variable_type:
            return None

        #
        # REMOVE GENERICS
        #
        normalized = variable_type.split("<")[0].strip()

        #
        # REMOVE ARRAYS
        #
        normalized = normalized.replace("[]", "")

        #
        # REMOVE PACKAGE
        #
        if "." in normalized:
            normalized = normalized.split(".")[-1]

        return normalized

    #
    # RESOLVE CALL
    #
    def resolve_call(
        self, file_id, current_class, current_method, object_name, method_name
    ):

        #
        # this.method()
        #
        if object_name == "this":
            return f"{current_class}.{method_name}"

        #
        # METHOD SCOPE
        #
        variable_type = self.symbol_table.resolve_variable(current_method, object_name)

        #
        # CLASS SCOPE
        #
        if not variable_type:
            variable_type = self.symbol_table.resolve_variable(
                current_class, object_name
            )

        #
        # STATIC CALL
        #
        if not variable_type and object_name and object_name[0].isupper():
            variable_type = object_name

        #
        # FAILED
        #
        if not variable_type:
            return None

        #
        # NORMALIZE
        #
        normalized_type = self._normalize_type(variable_type)

        #
        # IMPORT LOOKUP
        #
        fqcn = self.import_resolver.resolve_import(file_id, normalized_type)

        #
        # CLASS REGISTRY
        #
        if not fqcn:
            fqcn = self.class_registry.find_class(normalized_type)

        #
        # FALLBACK
        #
        if not fqcn:
            fqcn = normalized_type

        resolved = f"java:{fqcn}.{method_name}"

        #
        # DIRECT MATCH
        #
        existing = self.method_registry.find_method(resolved)

        if existing:
            return resolved

        #
        # SPRING DYNAMIC METHODS
        #
        dynamic_prefixes = ["findBy", "existsBy", "deleteBy", "countBy", "searchBy"]

        for prefix in dynamic_prefixes:
            if method_name.startswith(prefix):
                return resolved

        #
        # ACCESSORS
        #
        accessor_prefixes = ["get", "set", "is"]

        for prefix in accessor_prefixes:
            if method_name.startswith(prefix):
                return resolved

        return resolved
