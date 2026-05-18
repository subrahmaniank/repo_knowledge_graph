# parsers/common/models.py

from enum import Enum


class NodeType(Enum):

    FILE = "File"

    PACKAGE = "Package"

    CLASS = "Class"

    INTERFACE = "Interface"

    METHOD = "Method"

    FUNCTION = "Function"

    FIELD = "Field"

    LIBRARY = "Library"


class RelationshipType(Enum):

    CONTAINS = "CONTAINS"

    DECLARES = "DECLARES"

    HAS_METHOD = "HAS_METHOD"

    HAS_FIELD = "HAS_FIELD"

    IMPORTS = "IMPORTS"

    CALLS = "CALLS"

    EXTENDS = "EXTENDS"