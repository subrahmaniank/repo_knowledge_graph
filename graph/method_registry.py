# graph/method_registry.py


class MethodRegistry:

    def __init__(self):

        self.methods = {}

    #
    # ADD METHOD
    #
    def add_method(
        self,
        method_id,
        method_node
    ):

        self.methods[
            method_id
        ] = method_node

    #
    # FIND METHOD
    #
    def find_method(
        self,
        method_id
    ):

        return self.methods.get(
            method_id
        )

    #
    # DEBUG
    #
    def size(self):

        return len(
            self.methods
        )