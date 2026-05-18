import re

from enrichers.base_enricher import BaseEnricher

from parsers.common.models import NodeType, RelationshipType


class AngularEnricher(BaseEnricher):
    def enrich(self, file_path, source_code, graph_data):

        nodes = graph_data["nodes"]
        relationships = graph_data["relationships"]

        file_id = str(file_path)

        #
        # ANGULAR COMPONENT
        #
        component_matches = re.finditer(r"@Component\s*\(", source_code)

        for _ in component_matches:
            class_match = re.search(r"export\s+class\s+(\w+)", source_code)

            if class_match:
                class_name = class_match.group(1)

                class_id = f"{file_id}/{class_name}"

                relationships.append(
                    {
                        "from": class_id,
                        "type": "IS_ANGULAR_COMPONENT",
                        "to": "framework/angular",
                    }
                )

        #
        # ANGULAR SERVICE
        #
        service_matches = re.finditer(r"@Injectable\s*\(", source_code)

        for _ in service_matches:
            class_match = re.search(r"export\s+class\s+(\w+)", source_code)

            if class_match:
                class_name = class_match.group(1)

                class_id = f"{file_id}/{class_name}"

                relationships.append(
                    {
                        "from": class_id,
                        "type": "IS_ANGULAR_SERVICE",
                        "to": "framework/angular",
                    }
                )

        #
        # ANGULAR MODULE
        #
        module_matches = re.finditer(r"@NgModule\s*\(", source_code)

        for _ in module_matches:
            class_match = re.search(r"export\s+class\s+(\w+)", source_code)

            if class_match:
                class_name = class_match.group(1)

                class_id = f"{file_id}/{class_name}"

                relationships.append(
                    {
                        "from": class_id,
                        "type": "IS_ANGULAR_MODULE",
                        "to": "framework/angular",
                    }
                )

        return graph_data
