# graph/class_registry.py


class ClassRegistry:
    def __init__(self):

        self.classes = {}

    #
    # ADD CLASS
    #
    def add_class(self, class_name, fqcn):

        self.classes[class_name] = fqcn

    #
    # FIND CLASS
    #
    def find_class(self, class_name):

        return self.classes.get(class_name)

    #
    # DEBUG
    #
    def size(self):

        return len(self.classes)
