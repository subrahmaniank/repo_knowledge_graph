import re

from enrichers.base_enricher import (
    BaseEnricher
)


class ReactEnricher(BaseEnricher):

    def enrich(
        self,
        file_path,
        source_code,
        graph_data
    ):

        relationships = graph_data[
            "relationships"
        ]

        file_id = str(file_path)

        #
        # FUNCTION COMPONENTS
        #
        component_matches = re.finditer(
            r'function\s+([A-Z]\w+)',
            source_code
        )

        for match in component_matches:

            component_name = match.group(1)

            component_id = (
                f"{file_id}/{component_name}"
            )

            relationships.append({
                "from": component_id,
                "type": "IS_REACT_COMPONENT",
                "to": "framework/react"
            })

        #
        # ARROW FUNCTION COMPONENTS
        #
        arrow_matches = re.finditer(
            r'const\s+([A-Z]\w+)\s*=\s*\(',
            source_code
        )

        for match in arrow_matches:

            component_name = match.group(1)

            component_id = (
                f"{file_id}/{component_name}"
            )

            relationships.append({
                "from": component_id,
                "type": "IS_REACT_COMPONENT",
                "to": "framework/react"
            })

        #
        # HOOKS
        #
        hook_matches = re.finditer(
            r'use(State|Effect|Memo|Callback)',
            source_code
        )

        for match in hook_matches:

            hook_name = f"use{match.group(1)}"

            relationships.append({
                "from": file_id,
                "type": "USES_REACT_HOOK",
                "to": f"react_hook/{hook_name}"
            })

        return graph_data