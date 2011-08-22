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

import unittest
import sys
from datetime import datetime
from test import example_data
from test.example_models import City, Weapon, Fighter, Gang, Skill, SkillInstance, FighterSkillList
from redmodel.models import SetField, ModelWriter, ListFieldWriter, SetFieldWriter, SortedSetFieldWriter, NotFoundError, UniqueError, BadArgsError
from redmodel.containers import List, Set, SortedSet, ListHandle, SetHandle, SortedSetHandle, ListWriter, SetWriter, SortedSetWriter
from redmodel import connection as ds


class ModelTestCase(unittest.TestCase):
    pass

class ContainersTestCase(ModelTestCase):

    def setUp(self):
        ds.flushdb()

    def tearDown(self):
        pass

    def test_strlist(self):
        writer = ListWriter(str)
        hlist = ListHandle('mylist', str)
        writer.append(hlist, 'spam')
        writer.append(hlist, 'eggs')
        writer.append(hlist, 'hello world')
        mylist = List(hlist)
        self.assertEqual(mylist, ('spam', 'eggs', 'hello world'))

    def test_intset(self):
        writer = SetWriter(int)
        hset = SetHandle('myset', int)
        writer.append(hset, 11)
        writer.append(hset, 13)
        writer.append(hset, 17)
        myset = Set(hset)
        self.assertEqual(myset, set([11, 13, 17]))

    def test_model_list(self):
        writer = ListWriter(Fighter)
        hlist = ListHandle('mylist', Fighter)
        f1, f2, f3 = map(Fighter.by_id, [21, 33, 47])
        for f in f1, f2, f3:
            writer.append(hlist, f)
        mylist = List(hlist)
        self.assertEqual(mylist, (f1, f2, f3))

    def test_sorted_set(self):
        writer = SortedSetWriter(str)
        hzset = SortedSetHandle('myzset', str)
        writer.append(hzset, 'spam', 3.25)
        writer.append(hzset, 'eggs', 3.24)
        self.assertEqual(SortedSet(hzset), ('eggs', 'spam'))
        self.assertEqual(SortedSet(hzset, lte = 3.24), ('eggs',))
        self.assertEqual(SortedSet.zrange(hzset, 0, 0), ('eggs',))
        self.assertEqual(SortedSet.zfind(hzset, gt = 3.24), ('spam',))

    def test_model_sorted_set(self):
        writer = SortedSetWriter(Fighter)
        hzset = SortedSetHandle('myzset', Fighter)
        f1, f2, f3 = map(Fighter.by_id, [21, 33, 47])
        writer.append(hzset, f1, 3.25)
        writer.append(hzset, f2, 3.24)
        writer.append(hzset, f3, 4)
        self.assertEqual(SortedSet.zrange(hzset), (f2, f1, f3))
        self.assertEqual(SortedSet.zrevrange(hzset, 0, 0), (f3,))
        self.assertEqual(SortedSet(hzset, gt = 3.24), (f1, f3))

    def test_indexed_set(self):
        writer = SetWriter(int, index_key = 'myindex')
        hset1 = SetHandle('myset:1', int)
        hset2 = SetHandle('myset:2', int)
        for i in 1, 2, 3:
            writer.append(hset1, i)
        for i in 2, 3, 4, 5:
            writer.append(hset2, i)
        self.assertEqual(Set(hset1), set([1, 2, 3]))
        self.assertEqual(Set(hset2), set([2, 3, 4, 5]))
        self.assertEqual(ds.smembers('myindex:1'), set(['1']))
        self.assertEqual(ds.smembers('myindex:2'), set(['1', '2']))
        self.assertEqual(ds.smembers('myindex:3'), set(['1', '2']))
        self.assertEqual(ds.smembers('myindex:4'), set(['2']))
        self.assertEqual(ds.smembers('myindex:5'), set(['2']))
        self.assertEqual(ds.smembers('myindex:6'), set())

    def test_unique_indexed_set(self):
        writer = SetWriter(int, index_key = 'myindex', unique_index = True)
        hset1 = SetHandle('myset:1', int)
        hset2 = SetHandle('myset:2', int)
        for i in 1, 2, 3:
            writer.append(hset1, i)
            writer.append(hset2, i + 3)
        self.assertRaises(UniqueError, writer.append, hset1, 4)
        self.assertRaises(UniqueError, writer.append, hset2, 2)
        self.assertEqual(Set(hset1), set([1, 2, 3]))
        self.assertEqual(Set(hset2), set([4, 5, 6]))
        self.assertEqual(ds.hgetall('myindex'),
                {'1': '1', '2': '1', '3': '1', '4': '2', '5': '2', '6': '2'})

class ModelWriteTestCase(ModelTestCase):

    def setUp(self):
        ds.flushdb()

    def tearDown(self):
        pass

    def test_write(self):
        # basic model
        city_writer = ModelWriter(City)
        c1 = City(name = 'Reixte', coast = True)
        c2 = City(name = 'Damtoo', coast = True)
        c3 = City(name = 'Toynbe', coast = False)
        map(city_writer.create, [c1, c2, c3])
        self.assertEqual((c1.oid, c2.oid, c3.oid), ('1', '2', '3'))
        self.assertEqual(City(City.by_id(1)).oid, '1')
        self.assertEqual(ds.hgetall('City:1'), {'name': 'Reixte', 'coast': '1'})
        self.assertEqual(ds.hgetall('City:2'), {'name': 'Damtoo', 'coast': '1'})
        self.assertEqual(ds.hgetall('City:3'), {'name': 'Toynbe', 'coast': '0'})

        # list field referencing model
        city_connections_writer = ListFieldWriter(City.connections)
        city_connections_writer.append(c1.connections, c2)
        city_connections_writer.append(c2.connections, c1)
        city_connections_writer.append(c1.connections, c3)
        city_connections_writer.append(c3.connections, c1)
        self.assertEqual(ds.lrange('City:1:connections', 0, -1), ['2', '3'])
        self.assertEqual(ds.lrange('City:2:connections', 0, -1), ['1'])
        self.assertEqual(ds.lrange('City:3:connections', 0, -1), ['1'])

        # unique indexed field
        fighter_writer = ModelWriter(Fighter)
        dtime1 = datetime.utcfromtimestamp(1400000002)
        dtime2 = datetime.utcfromtimestamp(1400000001)
        f1 = Fighter(name = 'Alice', age = 29, weight = 73.2, joined = dtime1, city = City.by_id(1))
        f2 = Fighter(name = 'Bob', age = 23, weight = 98, joined = dtime2, city = City.by_id(1))
        map(fighter_writer.create, [f1, f2])
        self.assertEqual(ds.hgetall('Fighter:1'), {'name': 'Alice', 'age': '29', 'weight': '73.2', 'joined': '1400000002', 'city': '1'})
        self.assertEqual(ds.hgetall('Fighter:2'), {'name': 'Bob', 'age': '23', 'weight': '98', 'joined': '1400000001', 'city': '1'})
        self.assertEqual(ds.hgetall('u:Fighter:name'), {'Alice': '1', 'Bob': '2'})

        # indexed reference field
        self.assertEqual(ds.smembers('i:Fighter:city:1'), set(['1', '2']))

        # zindexed fields
        self.assertEqual(ds.zrange('z:Fighter:age', 0, -1), ['2', '1'])
        self.assertEqual(ds.zrange('z:Fighter:weight', 0, -1), ['1', '2'])
        self.assertEqual(ds.zrange('z:Fighter:joined', 0, -1), ['2', '1'])

        # missing argument
        self.assertRaises(BadArgsError, Fighter, name = 'MissingWeight', age = 30, city = 1)

        # unique attribute
        f3 = Fighter(name = 'Bob', age = 30, weight = 80, joined = dtime1, city = 1)
        self.assertRaises(UniqueError, fighter_writer.create, f3)

        # basic model
        gang_writer = ModelWriter(Gang)
        g1 = Gang(name = 'Ghetto Warriors', leader = f1, hqcity = c3)
        g2 = Gang(name = 'Midnight Club', leader = f2, hqcity = c1)
        map(gang_writer.create, [g1, g2])

        # unique indexed reference field
        self.assertEqual(ds.hgetall('u:Gang:leader'), {'1': '1', '2': '2' })

        # unique indexed set field
        gang_members_writer = SetFieldWriter(Gang.members)
        gang_members_writer.append(g1.members, f1)
        gang_members_writer.append(g1.members, f2)
        self.assertEqual(ds.smembers('Gang:1:members'), set(['1', '2']))
        self.assertEqual(ds.hgetall('u:Gang:members'), {'1': '1', '2': '1'})

        self.assertRaises(UniqueError, gang_members_writer.append, g2.members, f1)
        self.assertRaises(UniqueError, gang_members_writer.append, g1.members, f1)

        # non-unique indexed set field
        gang_cities_writer = SetFieldWriter(Gang.cities)
        gang_cities_writer.append(g1.cities, c1)
        gang_cities_writer.append(g1.cities, c3)
        self.assertEqual(ds.smembers('Gang:1:cities'), set(['1', '3']))
        self.assertEqual(ds.smembers('i:Gang:cities:1'), set(['1']))
        self.assertEqual(ds.smembers('i:Gang:cities:3'), set(['1']))

        # listed reference field
        self.assertEqual(ds.lrange('l:Gang:hqcity:1', 0, -1), ['2'])
        self.assertEqual(ds.lrange('l:Gang:hqcity:3', 0, -1), ['1'])

        # basic model
        skill_writer = ModelWriter(Skill)
        sk1 = Skill(category = 1, name = 'Strength', description = 'Strength...')
        sk2 = Skill(category = 3, name = 'Karate', description = 'Karate...')
        map(skill_writer.create, [sk1, sk2])

        # owned model
        fighter_skill_list_writer = ModelWriter(FighterSkillList)
        f1skills = FighterSkillList()
        f2skills = FighterSkillList()
        fighter_skill_list_writer.create(f1skills, f1)
        fighter_skill_list_writer.create(f2skills, f2)
        self.assertEqual(f1skills.oid, '1')
        self.assertEqual(f2skills.oid, '2')
        if __debug__:
            f3skills = FighterSkillList()
            self.assertRaises(AssertionError, fighter_skill_list_writer.create, f3skills)
            f3 = Fighter(name = 'Unsaved', age = 0, weight = 0, joined = None, city = 1)
            self.assertRaises(AssertionError, fighter_skill_list_writer.create, f3skills, f3)

        # owned model list field
        skill_instance_writer = ModelWriter(SkillInstance)
        fighter_skills_writer = ListFieldWriter(FighterSkillList.skills, element_writer = skill_instance_writer)
        ski1 = SkillInstance(skill = sk1.handle(), value = 21)
        ski2 = SkillInstance(skill = sk2, value = 15)
        fighter_skills_writer.append(f1skills.skills, ski1)
        fighter_skills_writer.append(f1skills.skills, ski2)
        self.assertEqual(ds.lrange('FighterSkillList:1:skills', 0, -1), ['1', '2'])
        self.assertEqual(ds.hgetall('SkillInstance:1'), {'skill': '1', 'value': '21'})
        self.assertEqual(ds.hgetall('SkillInstance:2'), {'skill': '2', 'value': '15'})

        ski1 = SkillInstance(skill = sk1, value = 27)
        ski2 = SkillInstance(skill = sk2, value = 91)
        fighter_skills_writer.append(f2skills.skills, ski1)
        fighter_skills_writer.append(f2skills.skills, ski2)
        self.assertEqual(ds.lrange('FighterSkillList:2:skills', 0, -1), ['3', '4'])
        self.assertEqual(ds.hgetall('SkillInstance:3'), {'skill': '1', 'value': '27'})
        self.assertEqual(ds.hgetall('SkillInstance:4'), {'skill': '2', 'value': '91'})

        # owned model sorted set field
        weapon_writer = ModelWriter(Weapon)
        fighter_weapons_writer = SortedSetFieldWriter(Fighter.weapons, weapon_writer)
        w1 = Weapon(description = 'second', power = 50.5)
        w2 = Weapon(description = 'third', power = 34.2)
        w3 = Weapon(description = 'first', power = 50.7)
        fighter_weapons_writer.append(f1.weapons, w1)
        fighter_weapons_writer.append(f1.weapons, w2)
        fighter_weapons_writer.append(f1.weapons, w3)
        self.assertEqual(ds.zrange('Fighter:1:weapons', 0, -1), ['2', '1', '3'])
        self.assertEqual(ds.hgetall('Weapon:1'), {'description': 'second', 'power': '50.5'})
        self.assertEqual(ds.hgetall('Weapon:2'), {'description': 'third', 'power': '34.2'})
        self.assertEqual(ds.hgetall('Weapon:3'), {'description': 'first', 'power': '50.7'})

    def test_update(self):
        example_data.load()
        fighter_writer = ModelWriter(Fighter)

        # update unique attribute
        fighter = Fighter(Fighter.by_id(2))
        fighter.name = 'Bobby'
        fighter.age = 41
        fighter_writer.update_all(fighter)
        self.assertEqual(ds.hgetall('u:Fighter:name'), {'Alice': '1', 'Bobby': '2'})
        fighter2 = Fighter(Fighter.by_id(2))
        self.assertEqual(fighter2.name, 'Bobby')
        self.assertEqual(fighter2.age, 41)
        fighter_writer.update(fighter2, name = 'Robert', weight = 99.9)
        self.assertEqual(ds.hgetall('u:Fighter:name'), {'Alice': '1', 'Robert': '2'})
        self.assertEqual(fighter2.name, 'Robert')
        self.assertEqual(fighter2.weight, 99.9)
        fighter3 = Fighter(Fighter.by_id(2))
        self.assertEqual(fighter3.name, 'Robert')
        self.assertEqual(fighter3.weight, 99.9)

        # update indexed attribute
        self.assertEqual(ds.smembers('i:Fighter:city:1'), set(['1', '2']))
        self.assertEqual(ds.smembers('i:Fighter:city:2'), set())
        fighter1 = Fighter(Fighter.by_id(1))
        fighter2 = Fighter(Fighter.by_id(2))
        fighter2.city = City.by_id(2)
        fighter_writer.update_all(fighter2)
        self.assertEqual(ds.smembers('i:Fighter:city:1'), set(['1']))
        self.assertEqual(ds.smembers('i:Fighter:city:2'), set(['2']))
        fighter_writer.update(fighter1, city = City.by_id(2))
        self.assertEqual(ds.smembers('i:Fighter:city:1'), set())
        self.assertEqual(ds.smembers('i:Fighter:city:2'), set(['1', '2']))
        city1 = City(City.by_id(1))
        fighter_writer.update(fighter1, city = city1)
        self.assertEqual(ds.smembers('i:Fighter:city:1'), set(['1']))
        self.assertEqual(ds.smembers('i:Fighter:city:2'), set(['2']))

        # update zindexed attribute
        self.assertEqual(ds.zrange('z:Fighter:weight', 0, -1), ['2', '1'])
        fighter_writer.update(fighter1, weight = 99.91)
        self.assertEqual(ds.zrange('z:Fighter:weight', 0, -1), ['2', '1'])
        fighter_writer.update(fighter1, weight = 99.89)
        self.assertEqual(ds.zrange('z:Fighter:weight', 0, -1), ['1', '2'])

        # update listed attribute
        self.assertEqual(ds.lrange('l:Gang:hqcity:1', 0, -1), [])
        self.assertEqual(ds.lrange('l:Gang:hqcity:3', 0, -1), ['1', '2'])
        gang2 = Gang(Gang.by_id(2))
        gang_writer = ModelWriter(Gang)
        gang_writer.update(gang2, hqcity = city1)
        self.assertEqual(ds.lrange('l:Gang:hqcity:1', 0, -1), ['2'])
        self.assertEqual(ds.lrange('l:Gang:hqcity:3', 0, -1), ['1'])

        # update object and sorted set atomically
        self.assertEqual(ds.zrange('Fighter:1:weapons', 0, -1), ['2', '1', '3'])
        self.assertEqual(ds.hgetall('Weapon:2'), {'description': 'third', 'power': '34.2'})
        weapon_writer = ModelWriter(Weapon)
        fighter_weapons_writer = SortedSetFieldWriter(Fighter.weapons, weapon_writer)
        w2 = Weapon(Weapon.by_id(2))
        fighter_weapons_writer.update(fighter1.weapons, w2,
                                      power = 70, description = 'improved')
        self.assertEqual(ds.zrange('Fighter:1:weapons', 0, -1), ['1', '3', '2'])
        self.assertEqual(ds.hgetall('Weapon:2'), {'description': 'improved', 'power': '70'})
        self.assertEqual(w2.power, 70)
        self.assertEqual(w2.description, 'improved')
        w2.power -= 60
        w2.description = 'degraded'
        fighter_weapons_writer.update_all(fighter1.weapons, w2)
        self.assertEqual(ds.zrange('Fighter:1:weapons', 0, -1), ['2', '1', '3'])
        self.assertEqual(ds.hgetall('Weapon:2'), {'description': 'degraded', 'power': '10'})

    def test_delete(self):
        example_data.load()

        # delete object updates indexes
        fighter_writer = ModelWriter(Fighter)
        self.assertEqual(ds.hgetall('u:Fighter:name'), {'Alice': '1', 'Bob': '2'})
        self.assertEqual(ds.smembers('i:Fighter:city:1'), set(['1', '2']))
        self.assertEqual(ds.zrange('z:Fighter:weight', 0, -1), ['2', '1'])
        fighter1 = Fighter(Fighter.by_id(1))
        fighter_writer.delete(fighter1)
        self.assertRaises(NotFoundError, Fighter, Fighter.by_id(1))
        self.assertTrue(fighter1.oid is None)
        self.assertEqual(ds.hgetall('u:Fighter:name'), {'Bob': '2'})
        self.assertEqual(ds.smembers('i:Fighter:city:1'), set(['2']))
        self.assertEqual(ds.zrange('z:Fighter:weight', 0, -1), ['2'])

        # delete container item updates indexes
        gang_members_writer = SetFieldWriter(Gang.members)
        self.assertEqual(ds.smembers('Gang:1:members'), set(['1', '2']))
        self.assertEqual(ds.hgetall('u:Gang:members'), {'1': '1', '2': '1'})
        gang1 = Gang(Gang.by_id(1))
        gang_members_writer.remove(gang1.members, Fighter.by_id(1))
        self.assertEqual(ds.smembers('Gang:1:members'), set(['2']))
        self.assertEqual(ds.hgetall('u:Gang:members'), {'2': '1'})

        gang_cities_writer = SetFieldWriter(Gang.cities)
        self.assertEqual(ds.smembers('Gang:1:cities'), set(['1', '3']))
        self.assertEqual(ds.smembers('i:Gang:cities:1'), set(['1']))
        self.assertEqual(ds.smembers('i:Gang:cities:3'), set(['1']))
        gang1 = Gang(Gang.by_id(1))
        gang_cities_writer.remove(gang1.cities, City.by_id(1))
        self.assertEqual(ds.smembers('Gang:1:cities'), set(['3']))
        self.assertFalse(ds.exists('i:Gang:cities:1'))
        self.assertEqual(ds.smembers('i:Gang:cities:3'), set(['1']))

        # delete object updates lists of listed attributes
        self.assertEqual(ds.lrange('l:Gang:hqcity:3', 0, -1), ['1', '2'])
        gang_writer = ModelWriter(Gang)
        gang_writer.delete(gang1)
        self.assertEqual(ds.lrange('l:Gang:hqcity:3', 0, -1), ['2'])

        # autodelete owned item
        fighter_skill_list_writer = ModelWriter(FighterSkillList)
        skill_instance_writer = ModelWriter(SkillInstance)
        fighter_skills_writer = ListFieldWriter(FighterSkillList.skills, element_writer = skill_instance_writer)

        self.assertEqual(ds.lrange('FighterSkillList:1:skills', 0, -1), ['1', '2'])
        self.assertEqual(ds.lrange('FighterSkillList:2:skills', 0, -1), ['3', '4'])
        for i in range(1, 5):
            self.assertTrue(ds.exists('SkillInstance:{0}'.format(i)))

        handle = FighterSkillList.by_owner(Fighter.by_id(2))
        fsl = FighterSkillList(handle)
        ski = SkillInstance(SkillInstance.by_id(3))
        fighter_skills_writer.remove(fsl.skills, ski)

        self.assertTrue(ski.oid is None)
        self.assertEqual(ds.lrange('FighterSkillList:2:skills', 0, -1), ['4'])
        self.assertFalse(ds.exists('SkillInstance:3'))
        self.assertTrue(ds.exists('SkillInstance:4'))

        # don't allow removing not owned object
        ski = SkillInstance(SkillInstance.by_id(1))
        self.assertRaises(NotFoundError, fighter_skills_writer.remove, fsl.skills, ski)
        self.assertTrue(ds.exists('SkillInstance:1'))

class ModelReadTestCase(ModelTestCase):

    def setUp(self):
        example_data.load()

    def tearDown(self):
        pass

    def test_read(self):
        handle = Gang.by_id(1)
        gang = Gang(handle)
        self.assertEqual(gang.name, 'Ghetto Warriors')

        members = Set(gang.members)
        self.assertEqual(members, set([Fighter.by_id(1), Fighter.by_id(2)]))

        hfighter1 = Fighter.by_id(1)
        hfighter2 = Fighter.by_id(2)
        fighter1 = Fighter(hfighter1)
        fighter2 = Fighter(hfighter2)
        self.assertEqual(fighter1.name, 'Alice')
        self.assertEqual(fighter2.name, 'Bob')

        dtime = datetime.utcfromtimestamp(1400000001)
        self.assertEqual(fighter2.joined, dtime)

        handle1 = Fighter.by_id(1)
        handle2 = Fighter.by_id(2)
        handle3 = Fighter.by_id(1)
        self.assertEqual(handle1, handle3)
        self.assertFalse(handle1 != handle3)
        self.assertFalse(handle1 == handle2)
        self.assertTrue(handle1 != handle2)

        city = City(fighter1.city)
        self.assertEqual(city.name, 'Reixte')
        self.assertEqual(city.coast, True)
        conns = List(city.connections)
        self.assertEqual(len(conns), 2)
        city2 = City(conns[1])
        self.assertEqual(city2.name, 'Toynbe')
        self.assertEqual(city2.coast, False)

        handle = Gang.by_id(999)
        self.assertRaises(NotFoundError, Gang, handle)

        handle = Fighter.find(name = 'Bob')
        self.assertEqual(handle, fighter2.handle())

        handle = Fighter.find(name = 'NoPlayer')
        self.assertFalse(handle)
        self.assertRaises(NotFoundError, Fighter, handle)

        city_fighters = Fighter.multifind(city = City.by_id(1))
        self.assertEqual(city_fighters, set([hfighter1, hfighter2]))

        handle = Gang.find(leader = hfighter1)
        self.assertEqual(handle, Gang.by_id(1))

        self.assertTrue(not Gang.find(members__contains = Fighter.by_id(3)))
        handle = Gang.find(members__contains = Fighter(hfighter2))
        self.assertEqual(handle, Gang.by_id(1))

        city3 = City(City.by_id(3))
        city_gangs = Gang.multifind(cities__contains = city3)
        self.assertEqual(city_gangs, set([Gang.by_id(1)]))

        handle = FighterSkillList.by_owner(fighter1)
        fsl = FighterSkillList(handle)
        fsl_skills = List(fsl.skills)
        skills = map(SkillInstance, fsl_skills)
        self.assertEqual(skills[0].skill, Skill.by_id(1))
        self.assertEqual(skills[0].value, 21)
        self.assertEqual(skills[1].skill, Skill.by_id(2))
        self.assertEqual(skills[1].value, 15)

        handle = FighterSkillList.by_owner(hfighter2)
        fsl = FighterSkillList(handle)
        fsl_skills = List(fsl.skills)
        skills = map(SkillInstance, fsl_skills)
        self.assertEqual(skills[0].skill, Skill.by_id(1))
        self.assertEqual(skills[0].value, 27)
        self.assertEqual(skills[1].skill, Skill.by_id(2))
        self.assertEqual(skills[1].value, 91)

        sorted_by_weight_1 = Fighter.zrange('weight')
        self.assertEqual(sorted_by_weight_1, [hfighter2, hfighter1])

        sorted_by_weight_2 = Fighter.zrange('weight', 0, 0)
        self.assertEqual(sorted_by_weight_2, [hfighter2])

        sorted_by_weight_3 = Fighter.zrange('weight', 1, -1)
        self.assertEqual(sorted_by_weight_3, [hfighter1])

        sorted_by_weight_4 = Fighter.zrevrange('weight')
        self.assertEqual(sorted_by_weight_4, [hfighter1, hfighter2])

        sorted_by_weight_5 = Fighter.zrevrange('weight', 0, 0)
        self.assertEqual(sorted_by_weight_5, [hfighter1])

        le24a = Fighter.zfind(age__lte = 24)
        le24b = Fighter.zrangebyscore('age', '-inf', 24)
        self.assertEqual(le24a, [hfighter1, hfighter2])
        self.assertEqual(le24a, le24b)

        le23a = Fighter.zfind(age__lte = 23)
        le23b = Fighter.zrangebyscore('age', '-inf', 23)
        self.assertEqual(le23a, [hfighter1, hfighter2])
        self.assertEqual(le23a, le23b)

        lt23a = Fighter.zfind(age__lt = 23)
        lt23b = Fighter.zrangebyscore('age', '-inf', '(23')
        self.assertEqual(lt23a, [hfighter1])
        self.assertEqual(lt23a, lt23b)

        ge24a = Fighter.zfind(age__gte = 24)
        ge24b = Fighter.zrangebyscore('age', 24, '+inf')
        self.assertEqual(ge24a, [])
        self.assertEqual(ge24a, ge24b)

        ge23a = Fighter.zfind(age__gte = 23)
        ge23b = Fighter.zrangebyscore('age', 23, '+inf')
        self.assertEqual(ge23a, [hfighter2])
        self.assertEqual(ge23a, ge23b)

        gt23a = Fighter.zfind(age__gt = 20)
        gt23b = Fighter.zrangebyscore('age', '(20', '+inf')
        self.assertEqual(gt23a, [hfighter2])
        self.assertEqual(gt23a, gt23b)

        age_in_a = Fighter.zfind(age__in = (20, 23))
        age_in_b = Fighter.zrangebyscore('age', 20, 23)
        age_in_c = Fighter.zrangebyscore('age', 20, 23, 0, 2)
        self.assertEqual(age_in_a, [hfighter1, hfighter2])
        self.assertEqual(age_in_a, age_in_b)
        self.assertEqual(age_in_a, age_in_c)

        age_eq_a = Fighter.zfind(age = 20)
        age_eq_b = Fighter.zrangebyscore('age', 20, 20)
        self.assertEqual(age_eq_a, [hfighter1])
        self.assertEqual(age_eq_a, age_eq_b)

        joined_before_2014 = Fighter.zfind(joined__lt = datetime(2014, 1, 1))
        self.assertEqual(joined_before_2014, [])
        joined_before_2020 = Fighter.zfind(joined__lt = datetime(2020, 1, 1))
        self.assertEqual(joined_before_2020, [hfighter2, hfighter1])
        joined_in_201x = Fighter.zfind(joined__in = (datetime(2010, 1, 1), datetime(2020, 1, 1)))
        self.assertEqual(joined_in_201x, [hfighter2, hfighter1])

        rev_age_in_a = Fighter.zrevrangebyscore('age', 23, 20)
        rev_age_in_b = Fighter.zrevrangebyscore('age', 23, 20, 0, 2)
        self.assertEqual(rev_age_in_a, [hfighter2, hfighter1])
        self.assertEqual(rev_age_in_a, rev_age_in_b)

        self.assertEqual(Fighter.zcount('age', 20, 23), 2)
        self.assertEqual(Fighter.zrank('weight', fighter1), 1)
        self.assertEqual(Fighter.zrank('weight', hfighter2), 0)
        self.assertEqual(Fighter.zrevrank('weight', hfighter1), 0)
        self.assertEqual(Fighter.zrevrank('weight', hfighter2), 1)

        hweapon1 = Weapon.by_id(1)
        hweapon2 = Weapon.by_id(2)
        hweapon3 = Weapon.by_id(3)

        sorted_weapons = SortedSet.zrange(fighter1.weapons)
        self.assertEqual(sorted_weapons, (hweapon2, hweapon1, hweapon3))

        top_weapons = SortedSet.zrevrange(fighter1.weapons, 0, 1)
        self.assertEqual(top_weapons, (hweapon3, hweapon1))

        powerful_weapons1 = SortedSet.zfind(fighter1.weapons, gt = 50)
        powerful_weapons2 = SortedSet(fighter1.weapons, gt = 50)
        self.assertEqual(powerful_weapons1, (hweapon1, hweapon3))
        self.assertEqual(powerful_weapons1, powerful_weapons2)


def all_tests():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ContainersTestCase))
    suite.addTest(unittest.makeSuite(ModelWriteTestCase))
    suite.addTest(unittest.makeSuite(ModelReadTestCase))
    return suite


if __name__ == "__main__":
    if len(sys.argv) > 1:
        unittest.main()
    else:
        suite = all_tests()
        unittest.TextTestRunner(verbosity=2).run(suite)
