# enrichers/spring/enricher.py


SPRING_REPOSITORY_METHODS = [
    "save",
    "saveAll",
    "findById",
    "findAll",
    "delete",
    "deleteById",
    "deleteAll",
    "count",
    "existsById",
    "flush",
]


class SpringBootEnricher:
    def enrich(self, class_node, nodes, relationships, method_registry=None):

        class_id = class_node["id"]

        #
        # REPOSITORY DETECTION
        #
        if "Repository" in class_node["name"]:
            for method_name in SPRING_REPOSITORY_METHODS:
                method_id = f"{class_id}.{method_name}"

                method_node = {
                    "type": "Method",
                    "id": method_id,
                    "name": method_name,
                    "metadata": {"synthetic": True, "framework": "spring-data"},
                }

                nodes.append(method_node)

                relationships.append(
                    {"from": class_id, "type": "HAS_METHOD", "to": method_id}
                )

                if method_registry:
                    method_registry.add_method(method_id, method_node)

        return {"nodes": nodes, "relationships": relationships}
