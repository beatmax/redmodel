# -*- coding: utf-8 -*-
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

import redis

class Client(object):
    def __init__(self, **kwargs):
        self.connection_settings = kwargs or {'host': 'localhost',
                'port': 6379, 'db': 0}

    def redis(self):
        return redis.Redis(**self.connection_settings)

    def update(self, d):
        self.connection_settings.update(d)

class ClientProxy(object):
    def __getattr__(self, name):
        return getattr(get_client(), name)

def connection_setup(**kwargs):
    global connection_real, client
    if client:
        client.update(kwargs)
    else:
        client = Client(**kwargs)
    connection_real = client.redis()

def get_client():
    global connection_real
    return connection_real

client = Client()
connection_real = client.redis()
connection = ClientProxy()

__all__ = ['connection_setup', 'get_client']
