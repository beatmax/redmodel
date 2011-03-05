"""
    Copyright (C) 2011 Maximiliano Pin

    Redmodel is free software: you can redistribute it and/or modify
    it under the terms of the GNU Lesser General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    Redmodel is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU Lesser General Public License for more details.

    You should have received a copy of the GNU Lesser General Public License
    along with Redmodel.  If not, see <http://www.gnu.org/licenses/>.
"""

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
