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

from redmodel.containers import ListHandle, SetHandle, ContainerWriter, ListWriter, SetWriter
from redmodel.models.base import Handle, Model
from redmodel.models.attributes import ListField, SetField
from redmodel.models.exceptions import UniqueError, NotFoundError
from redmodel import connection as ds

class ModelWriter(object):
    def __init__(self, model):
        self.model = model
        self.modname = model.__name__

    def __check_unique(self, fld, val):
        #TODO watch (optimistic lock) to allow multithread?
        k = 'u:{0}:{1}'.format(self.modname, fld)
        if ds.hexists(k, val):
            raise UniqueError(k + '<' + str(val) + '>')

    def __index(self, pl, oid, fld, val, unique):
        if unique:
            k = 'u:{0}:{1}'.format(self.modname, fld)
            pl.hset(k, val, oid)
        else:
            k = 'i:{0}:{1}:{2}'.format(self.modname, fld, val)
            pl.sadd(k, oid)

    def __unindex(self, pl, oid, fld, val, unique):
        if unique:
            k = 'u:{0}:{1}'.format(self.modname, fld)
            pl.hdel(k, val)
        else:
            k = 'i:{0}:{1}:{2}'.format(self.modname, fld, val)
            pl.srem(k, oid)

    def __unindex_all(self, pl, obj):
        for a in obj._attributes:
            if a.indexed:
                fld = a.name
                v = obj._indexed_values[fld]
                if v is not None:
                    self.__unindex(pl, obj.oid, fld, v, a.unique)

    def __update_attrs(self, obj, data):
        if (len(data)):
            attr_dict = self.model._attr_dict
            for fld in data.iterkeys():
                a = attr_dict[fld]
                if a.unique:
                    v = data[fld]
                    oldv = obj._indexed_values[fld]
                    if v != oldv:
                        self.__check_unique(fld, v)
            pl = ds.pipeline(True)
            pl.hmset(obj.key, data)
            for fld in data.iterkeys():
                a = attr_dict[fld]
                if a.indexed:
                    v = data[fld]
                    oldv = obj._indexed_values[fld]
                    if oldv is not None:
                        self.__unindex(pl, obj.oid, fld, oldv, a.unique)
                    self.__index(pl, obj.oid, fld, v, a.unique)
                    obj._indexed_values[fld] = v
            pl.execute()

    def create(self, obj, owner = None):
        assert type(obj) is self.model and obj.oid is None
        assert owner is None or owner.oid is not None
        assert (owner is None and self.model._owner is None) or (type(owner) is self.model._owner) or (type(owner) is Handle and owner.model is self.model._owner), 'Wrong owner.'
        if owner is None:
            obj.oid = str(ds.incr(self.modname + ':id'))
        else:
            obj.oid = owner.oid
        self.__update_attrs(obj, obj.make_dict())
        key = obj.key
        for l in obj._lists:
            obj.__dict__[l.name] = ListHandle(key + ':' + l.name, l.target_type)
        for s in obj._sets:
            obj.__dict__[s.name] = SetHandle(key + ':' + s.name, s.target_type)

    def update(self, obj, **kwargs):
        assert type(obj) == self.model and obj.oid is not None
        assert len(kwargs) > 0
        data = obj.update_attributes_dict(**kwargs)
        self.__update_attrs(obj, data)

    def update_all(self, obj):
        assert type(obj) == self.model and obj.oid is not None
        self.__update_attrs(obj, obj.make_dict())

    def delete(self, obj):
        assert type(obj) == self.model and obj.oid is not None
        if not ds.exists(obj.key):
            raise NotFoundError(obj.key)
        pl = ds.pipeline(True)
        self.__unindex_all(pl, obj)
        pl.delete(obj.key)
        pl.execute()
        obj.oid = None

class ContainerFieldWriter(ContainerWriter):
    def __init__(self, field, element_writer = None):
        assert (not field.owned and element_writer is None) or (field.owned and element_writer is not None)
        self.field = field
        self.element_writer = element_writer
        index_key = None
        if field.indexed:
            index_key = 'u:' if field.unique else 'i:'
            index_key += field.model.__name__ + ':' + field.name
        ContainerWriter.__init__(self, field.target_type, index_key, field.unique)

    def append(self, hcont, value):
        if self.field.owned:
            assert value.oid is None
            self.element_writer.create(value)
            assert value.oid is not None
            value = value.handle()
        ContainerWriter.append(self, hcont, value)

    def remove(self, hcont, value):
        assert (not self.field.owned) or isinstance(value, Model)
        removed = ContainerWriter.remove(self, hcont, value)
        if self.field.owned:
            if not removed:
                raise NotFoundError('{0} in {1}'.format(value.handle(), hcont))
            assert value.oid is not None
            self.element_writer.delete(value)
            assert value.oid is None

class ListFieldWriter(ContainerFieldWriter, ListWriter):
    def __init__(self, field, element_writer = None):
        assert type(field) == ListField
        ContainerFieldWriter.__init__(self, field, element_writer)

class SetFieldWriter(ContainerFieldWriter, SetWriter):
    def __init__(self, field, element_writer = None):
        assert type(field) == SetField
        ContainerFieldWriter.__init__(self, field, element_writer)
