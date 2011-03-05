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

from redmodel import connection as ds

class Error(Exception):
    pass

class UniqueError(Error):
    pass

class ContainerHandle(object):
    def __init__(self, key, target_type):
        self.key = key
        self.target_type = target_type

    @property
    def owner_id(self):
        return self.key.split(':')[1]

    def __repr__(self):
        return '<{0}: {1}>'.format(self.__class__.__name__, self.key)

    def _transform(self, data):
        try:
            func = getattr(self.target_type, 'by_id')
        except AttributeError:
            func = self.target_type
        return map(func, data)

class ListHandle(ContainerHandle):
    def load(self):
        d = ds.lrange(self.key, 0, -1)
        return self._transform(d)

class SetHandle(ContainerHandle):
    def load(self):
        d = ds.smembers(self.key)
        return self._transform(d)

#class List(list):
#    def __init__(self, handle):
#        list.__init__(self, handle.load())

class List(tuple):
    def __new__(cls, handle):
        assert type(handle) is ListHandle
        return tuple.__new__(cls, handle.load())

#class Set(set):
#    def __init__(self, handle):
#        assert type(handle) is SetHandle
#        return set.__init__(self, handle.load())

class Set(frozenset):
    def __new__(cls, handle):
        assert type(handle) is SetHandle
        return frozenset.__new__(cls, handle.load())

class ContainerWriter(object):
    def __init__(self, target_type, index_key = None, unique_index = False):
        self.target_type = target_type
        self.target_has_id = hasattr(target_type, 'oid')
        self.index_key = index_key
        self.unique_index = unique_index

    def append(self, hcont, value):
        assert hcont.target_type is self.target_type
        assert type(value) is self.target_type or (hasattr(value, 'model') and value.model is self.target_type)
        if self.target_has_id:
            value = value.oid
        assert value is not None
        if not self.index_key:
            self.raw_append(ds, hcont, value)
        elif self.unique_index:
            #TODO watch (optimistic lock) to allow multithread?
            if ds.hexists(self.index_key, value):
                raise UniqueError(self.index_key + '<' + str(value) + '>')
            else:
                pl = ds.pipeline(True)
                self.raw_append(pl, hcont, value)
                pl.hset(self.index_key, value, hcont.owner_id)
                pl.execute()
        else:
            pl = ds.pipeline(True)
            self.raw_append(pl, hcont, value)
            ikey = self.index_key + ':' + str(value)
            pl.sadd(ikey, hcont.owner_id)
            pl.execute()

    def remove(self, hcont, value):
        assert hcont.target_type is self.target_type
        assert type(value) is self.target_type or (hasattr(value, 'model') and value.model is self.target_type)
        if self.target_has_id:
            value = value.oid
        if not self.index_key:
            return self.raw_remove(ds, hcont, value)
        else:
            pl = ds.pipeline(True)
            if self.unique_index:
                pl.hdel(self.index_key, value)
            else:
                ikey = self.index_key + ':' + str(value)
                pl.srem(ikey, hcont.owner_id)
            self.raw_remove(pl, hcont, value)
            resp = pl.execute()
            return resp[1]

class ListWriter(ContainerWriter):
    def __init__(self, target_type, index_key = None, unique_index = False):
        ContainerWriter.__init__(self, target_type, index_key, unique_index)

    def raw_append(self, conn, hlist, value):
        assert type(hlist) is ListHandle
        conn.rpush(hlist.key, value)

    def raw_remove(self, conn, hlist, value):
        assert type(hlist) is ListHandle
        return conn.lrem(hlist.key, value)

class SetWriter(ContainerWriter):
    def __init__(self, target_type, index_key = None, unique_index = False):
        ContainerWriter.__init__(self, target_type, index_key, unique_index)

    def raw_append(self, conn, hset, value):
        assert type(hset) is SetHandle
        conn.sadd(hset.key, value)

    def raw_remove(self, conn, hset, value):
        assert type(hset) is SetHandle
        return conn.srem(hset.key, value)
