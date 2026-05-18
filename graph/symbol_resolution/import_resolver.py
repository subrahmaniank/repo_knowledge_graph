class ImportResolver:

    def __init__(self):

        #
        # file_id ->
        # {
        #   short_name:
        #   fully_qualified_name
        # }
        #
        self.imports = {}

    #
    # REGISTER IMPORT
    #
    def add_import(
        self,
        file_id,
        fqcn
    ):

        short_name = (
            fqcn.split(".")[-1]
        )

        if file_id not in self.imports:

            self.imports[file_id] = {}

        self.imports[
            file_id
        ][short_name] = fqcn

    #
    # RESOLVE IMPORT
    #
    def resolve_import(
        self,
        file_id,
        short_name
    ):

        return (
            self.imports
            .get(file_id, {})
            .get(short_name)
        )