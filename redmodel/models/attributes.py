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

from datetime import datetime
import calendar

class Attribute(object):
    def __init__(self, indexed = False, unique = False, zindexed = False):
        self.indexed = indexed or unique
        self.unique = unique
        self.zindexed = zindexed

    def typecast_for_read(self, value):
        return value

    def typecast_for_write(self, value):
        return value

class BooleanField(Attribute):
    def typecast_for_read(self, value):
        return bool(int(value))

    def typecast_for_write(self, value):
        return '1' if value else '0'

class IntegerField(Attribute):
    def typecast_for_read(self, value):
        return int(value)

class FloatField(Attribute):
    def typecast_for_read(self, value):
        return float(value)

class UTCDateTimeField(Attribute):
    """ UTC datetime without microseconds. 'None' is allowed (stored as 0).
        Notice it may be better to store timestamps in IntegerField or
        FloatField to avoid conversions. """
    def typecast_for_read(self, value):
        if value == '0':
            return None
        return datetime.utcfromtimestamp(float(value))

    def typecast_for_write(self, value):
        if value is None:
            return 0
        assert isinstance(value, datetime)
        return calendar.timegm(value.utctimetuple())

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

class SortedSetField(ContainerField):
    def __init__(self, target_type, sort_field = None, indexed = False, unique = False, owned = False):
        """ If sort_field is specified, then owned = True is mandatory. """
        assert owned or sort_field is None
        ContainerField.__init__(self, target_type, indexed, unique, owned)
        self.sort_field = sort_field

class Recursive:
    pass
