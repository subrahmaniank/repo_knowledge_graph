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
        # file_id -> [fully qualified owner]
        # for imports like:
        # import static a.b.C.*
        #
        self.static_wildcards = {}

    #
    # REGISTER IMPORT
    #
    def add_import(
        self,
        file_id,
        fqcn
    ):

        normalized = fqcn.strip()

        is_static = normalized.startswith("static ")

        if is_static:
            normalized = normalized[len("static "):].strip()

        if normalized.endswith(".*"):
            if is_static:
                owner = normalized[:-2]

                if file_id not in self.static_wildcards:
                    self.static_wildcards[file_id] = []

                self.static_wildcards[file_id].append(owner)

            return

        short_name = (
            normalized.split(".")[-1]
        )

        if file_id not in self.imports:

            self.imports[file_id] = {}

        self.imports[
            file_id
        ][short_name] = normalized

    #
    # RESOLVE IMPORT
    #
    def resolve_import(
        self,
        file_id,
        short_name
    ):

        direct = (
            self.imports
            .get(file_id, {})
            .get(short_name)
        )

        if direct:
            return direct

        return None

    def resolve_static_wildcard_candidates(
        self,
        file_id,
        short_name,
    ):

        candidates = []

        for owner in self.static_wildcards.get(file_id, []):
            candidates.append(f"{owner}.{short_name}")

        return candidates
