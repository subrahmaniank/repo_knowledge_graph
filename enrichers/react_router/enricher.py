import re

from enrichers.base_enricher import (
    BaseEnricher
)


class ReactRouterEnricher(BaseEnricher):

    def enrich(
        self,
        file_path,
        source_code,
        graph_data
    ):

        nodes = graph_data["nodes"]

        relationships = graph_data[
            "relationships"
        ]

        file_id = str(file_path)

        #
        # DETECT ROUTES
        #
        route_pattern = re.compile(
            r'<Route\s+path=["\']([^"\']+)["\']'
            r'.*?element=\{<(\w+)',
            re.DOTALL
        )

        route_matches = route_pattern.finditer(
            source_code
        )

        for match in route_matches:

            route_path = match.group(1)

            component_name = match.group(2)

            #
            # ROUTE NODE
            #
            route_id = f"route/{route_path}"

            nodes.append({
                "type": "Route",
                "id": route_id,
                "name": route_path,
                "metadata": {
                    "framework": "react-router"
                }
            })

            #
            # COMPONENT ID
            #
            component_id = (
                f"{file_id}/"
                f"{component_name}"
            )

            #
            # ROUTE -> COMPONENT
            #
            relationships.append({
                "from": route_id,
                "type": "RENDERS",
                "to": component_id
            })

        #
        # NESTED ROUTES
        #
        nested_pattern = re.compile(
            r'<Route\s+path=["\']([^"\']+)["\']',
            re.DOTALL
        )

        routes = [
            match.group(1)
            for match in nested_pattern.finditer(
                source_code
            )
        ]

        #
        # SIMPLE HIERARCHY DETECTION
        #
        for route in routes:

            parts = route.strip("/").split("/")

            if len(parts) > 1:

                parent_route = "/" + "/".join(
                    parts[:-1]
                )

                child_route = route

                relationships.append({
                    "from": f"route/{child_route}",
                    "type": "NESTED_UNDER",
                    "to": f"route/{parent_route}"
                })

        #
        # LAZY LOADED COMPONENTS
        #
        lazy_pattern = re.compile(
            r'lazy\s*\(\s*\(\)\s*=>\s*import'
            r'\(["\']([^"\']+)["\']\)',
            re.DOTALL
        )

        lazy_matches = lazy_pattern.finditer(
            source_code
        )

        for match in lazy_matches:

            import_path = match.group(1)

            lazy_id = f"lazy/{import_path}"

            nodes.append({
                "type": "LazyComponent",
                "id": lazy_id,
                "name": import_path
            })

            relationships.append({
                "from": file_id,
                "type": "LAZY_LOADS",
                "to": lazy_id
            })

        return graph_data