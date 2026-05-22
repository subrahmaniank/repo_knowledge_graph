import re

from enrichers.base_enricher import (
    BaseEnricher
)


class FlaskEnricher(BaseEnricher):

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

        file_id = f"python:file:{file_path}"

        function_id_by_name = {}

        for node in nodes:
            if node.get("type") == "Function":
                function_id_by_name[node.get("name")] = node.get("id")

        #
        # DETECT FLASK APP
        #
        if "Flask(" in source_code:

            app_id = f"flask:app:{file_path}"

            nodes.append({
                "type": "Framework",
                "id": app_id,
                "name": "Flask"
            })

            relationships.append({
                "from": file_id,
                "type": "USES_FRAMEWORK",
                "to": app_id,
            })

        #
        # DETECT BLUEPRINTS
        #
        blueprint_matches = re.finditer(
            r'Blueprint\s*\(\s*[\'"]([^\'"]+)',
            source_code
        )

        for match in blueprint_matches:

            blueprint_name = match.group(1)

            blueprint_id = f"flask:blueprint:{file_path}:{blueprint_name}"

            nodes.append({
                "type": "Blueprint",
                "id": blueprint_id,
                "name": blueprint_name
            })

            relationships.append({
                "from": file_id,
                "type": "DECLARES_BLUEPRINT",
                "to": blueprint_id
            })

        #
        # DETECT ROUTES
        #
        route_pattern = re.compile(
            r'@(?:\w+\.)?route\s*'
            r'\(\s*[\'"]([^\'"]+)'
            r'(?:,\s*methods\s*=\s*\[([^\]]+)\])?',
            re.MULTILINE
        )

        function_pattern = re.compile(
            r'def\s+(\w+)\s*\('
        )

        route_matches = list(
            route_pattern.finditer(source_code)
        )

        function_matches = list(
            function_pattern.finditer(
                source_code
            )
        )

        #
        # MAP ROUTES TO FUNCTIONS
        #
        for route_match in route_matches:

            route_path = route_match.group(1)

            methods = route_match.group(2)

            #
            # FIND NEXT FUNCTION
            #
            route_end = route_match.end()

            target_function = None

            for fn_match in function_matches:

                if fn_match.start() > route_end:

                    target_function = (
                        fn_match.group(1)
                    )

                    break

            #
            # API NODE
            #
            api_id = f"flask:api:{file_path}:{route_path}"

            nodes.append({
                "type": "API",
                "id": api_id,
                "name": route_path,
                "metadata": {
                    "framework": "flask"
                }
            })

            #
            # API METHODS
            #
            http_methods = []

            if methods:

                http_methods = [
                    m.strip()
                    .replace('"', '')
                    .replace("'", '')
                    for m in methods.split(",")
                ]

            else:

                http_methods = ["GET"]

            #
            # CREATE METHOD NODES
            #
            for method in http_methods:

                method_id = f"flask:http_method:{method}"

                nodes.append({
                    "type": "HTTPMethod",
                    "id": method_id,
                    "name": method
                })

                relationships.append({
                    "from": api_id,
                    "type": "SUPPORTS_METHOD",
                    "to": method_id
                })

            #
            # CONNECT TO FUNCTION
            #
            if target_function:
                function_id = function_id_by_name.get(target_function)

                if function_id:
                    relationships.append({
                        "from": api_id,
                        "type": "HANDLED_BY",
                        "to": function_id
                    })

        return graph_data
