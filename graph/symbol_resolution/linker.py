class MethodRegistry:

    def __init__(self):

        #
        # fq_method ->
        # node
        #
        self.methods = {}

    #
    # REGISTER METHOD
    #
    def add_method(
        self,
        method_id,
        node
    ):

        self.methods[
            method_id
        ] = node

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