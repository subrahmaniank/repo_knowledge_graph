# parsers/parser_factory.py

from graph.symbol_resolution.import_resolver import ImportResolver

from parsers.java.parser import JavaParser
from parsers.python.parser import PythonParser
from parsers.javascript.parser import JavaScriptParser
from parsers.typescript.parser import TypeScriptParser


class ParserFactory:
    def __init__(self, symbol_table, class_registry, method_registry):

        self.symbol_table = symbol_table

        self.class_registry = class_registry

        self.method_registry = method_registry

        #
        # SHARED IMPORT RESOLVER
        #
        self.import_resolver = ImportResolver()

        #
        # PARSER MAP
        #
        self.parsers = {
            ".java": JavaParser(
                symbol_table=self.symbol_table,
                import_resolver=self.import_resolver,
                method_registry=self.method_registry,
                class_registry=self.class_registry,
            ),
            ".py": PythonParser(
                method_registry=self.method_registry,
                class_registry=self.class_registry,
            ),
            ".js": JavaScriptParser(),
            ".jsx": JavaScriptParser(),
            ".ts": TypeScriptParser(),
            ".tsx": TypeScriptParser(),
        }

    #
    # GET PARSER
    #
    def get_parser(self, file_extension):

        return self.parsers.get(file_extension)
