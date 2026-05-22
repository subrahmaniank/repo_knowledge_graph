class JavaExpressionResolver:

    #
    # EXTRACT ROOT OBJECT
    #
    def extract_root_object(
        self,
        node,
        source_bytes,
        text_extractor
    ):

        if not node:

            return None

        #
        # SIMPLE IDENTIFIER
        #
        if node.type == "identifier":

            return text_extractor(
                source_bytes,
                node
            )

        #
        # FIELD ACCESS
        #
        if node.type == "field_access":

            object_node = (
                node.child_by_field_name(
                    "object"
                )
            )

            field_node = (
                node.child_by_field_name(
                    "field"
                )
            )

            object_name = (
                self.extract_root_object(
                    object_node,
                    source_bytes,
                    text_extractor
                )
            )

            #
            # this.repo.save() -> receiver should be "repo"
            #
            if (
                object_name in ["this", "super"]
                and field_node
            ):
                return text_extractor(
                    source_bytes,
                    field_node
                )

            return (
                object_name
            )

        #
        # METHOD INVOCATION
        #
        if node.type == "method_invocation":

            object_node = (
                node.child_by_field_name(
                    "object"
                )
            )

            return (
                self.extract_root_object(
                    object_node,
                    source_bytes,
                    text_extractor
                )
            )

        #
        # FALLBACK
        #
        return None
