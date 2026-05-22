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

        variable_type = None

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
        # COMMON LOGGER CONVENTIONS
        #
        if not variable_type and object_name in {"log", "logger"}:
            variable_type = "Logger"

        #
        # COMMON FRAMEWORK RECEIVER ALIASES
        #
        if not variable_type and object_name:
            framework_aliases = {
                "root": "jakarta.persistence.criteria.Root",
                "cb": "jakarta.persistence.criteria.CriteriaBuilder",
                "auth": "org.springframework.security.config.annotation.web.builders.HttpSecurity",
                "session": "org.springframework.security.config.annotation.web.configurers.SessionManagementConfigurer",
                "cors": "org.springframework.web.cors.CorsConfiguration",
            }

            variable_type = framework_aliases.get(object_name)

        #
        # STATIC CALL
        #
        if not variable_type and object_name and object_name[0].isupper():
            variable_type = object_name

        #
        # FAILED
        #
        if not variable_type:
            if object_name and method_name:
                accessor_prefixes = ["get", "set", "is", "has"]

                fluent_methods = {
                    "equal",
                    "lessThanOrEqualTo",
                    "anyRequest",
                    "permitAll",
                    "sessionCreationPolicy",
                    "configurationSource",
                }

                if any(method_name.startswith(prefix) for prefix in accessor_prefixes):
                    return f"java:inferred:{object_name}.{method_name}"

                if method_name in fluent_methods:
                    return f"java:framework:{object_name}.{method_name}"

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
