'''
Created on 12/12/2010

@author: mad
'''
class Attribute(object):
    def __init__(self, indexed = False, unique = False):
        self.indexed = indexed or unique
        self.unique = unique

    def typecast_for_read(self, value):
        return value

    def typecast_for_write(self, value):
        return value

class IntegerField(Attribute):
    def typecast_for_read(self, value):
        return int(value)

class ReferenceField(Attribute):
    def __init__(self, target_type, indexed = False, unique = False):
        self.target_type = target_type
        Attribute.__init__(self, indexed, unique)

    def typecast_for_read(self, value):
        return self.target_type.by_id(value)

    def typecast_for_write(self, value):
        return value.oid

class ContainerField(object):
    def __init__(self, target_type, indexed = False, unique = False, owned = False):
        self.target_type = target_type
        self.indexed = indexed or unique
        self.unique = unique
        self.owned = owned

class ListField(ContainerField):
    def __init__(self, target_type, indexed = False, unique = False, owned = False):
        ContainerField.__init__(self, target_type, indexed, unique, owned)

class SetField(ContainerField):
    def __init__(self, target_type, indexed = False, unique = False, owned = False):
        ContainerField.__init__(self, target_type, indexed, unique, owned)

class Recursive:
    pass
