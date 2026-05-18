# graph/symbol_resolution/symbol_table.py


class SymbolTable:
    def __init__(self):

        self.scopes = {}

    #
    # ADD VARIABLE
    #
    def add_variable(self, scope, variable_name, variable_type):

        if not scope:
            return

        if not variable_name:
            return

        if scope not in self.scopes:
            self.scopes[scope] = {}

        self.scopes[scope][variable_name] = variable_type

    #
    # RESOLVE VARIABLE
    #
    def resolve_variable(self, scope, variable_name):

        if not scope:
            return None

        if not variable_name:
            return None

        if scope not in self.scopes:
            return None

        return self.scopes[scope].get(variable_name)

    #
    # DEBUG
    #
    def size(self):

        total = 0

        for scope in self.scopes.values():
            total += len(scope)

        return total
