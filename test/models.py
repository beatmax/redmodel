'''
Created on 12/12/2010

@author: mad
'''
import unittest
from test import example_data
from test.example_models import City, Fighter, Gang, Skill, SkillInstance, FighterSkillList
from redmodel.models import SetField, ModelWriter, ListFieldWriter, SetFieldWriter, NotFoundError, UniqueError, BadArgsError
from redmodel.containers import List, Set, ListHandle, SetHandle, ListWriter, SetWriter
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
        c1 = City(name = 'Reixte')
        c2 = City(name = 'Damtoo')
        c3 = City(name = 'Toynbe')
        map(city_writer.create, [c1, c2, c3])
        self.assertEqual((c1.oid, c2.oid, c3.oid), ('1', '2', '3'))
        self.assertEqual(City(City.by_id(1)).oid, '1')
        self.assertEqual(ds.hgetall('City:1'), {'name': 'Reixte'})
        self.assertEqual(ds.hgetall('City:2'), {'name': 'Damtoo'})
        self.assertEqual(ds.hgetall('City:3'), {'name': 'Toynbe'})

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
        f1 = Fighter(name = 'Alice', age = 29, weight = 73, city = City.by_id(1))
        f2 = Fighter(name = 'Bob', age = 32, weight = 98, city = City.by_id(1))
        map(fighter_writer.create, [f1, f2])
        self.assertEqual(ds.hgetall('u:Fighter:name'), {'Alice': '1', 'Bob': '2'})

        # indexed reference field
        self.assertEqual(ds.smembers('i:Fighter:city:1'), set(['1', '2']))

        # missing argument
        self.assertRaises(BadArgsError, Fighter, name = 'MissingWeight', age = 30, city = 1)

        # unique attribute
        f3 = Fighter(name = 'Bob', age = 30, weight = 80, city = 1)
        self.assertRaises(UniqueError, fighter_writer.create, f3)

        # basic model
        gang_writer = ModelWriter(Gang)
        g1 = Gang(name = 'Ghetto Warriors', leader = f1)
        g2 = Gang(name = 'Midnight Club', leader = f2)
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
            f3 = Fighter(name = 'Unsaved', age = 0, weight = 0, city = 1)
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
        fighter_writer.update(fighter2, name = 'Robert', weight = 99)
        self.assertEqual(ds.hgetall('u:Fighter:name'), {'Alice': '1', 'Robert': '2'})
        self.assertEqual(fighter2.name, 'Robert')
        self.assertEqual(fighter2.weight, 99)
        fighter3 = Fighter(Fighter.by_id(2))
        self.assertEqual(fighter3.name, 'Robert')
        self.assertEqual(fighter3.weight, 99)

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

    def test_delete(self):
        example_data.load()

        # delete object updates indexes
        fighter_writer = ModelWriter(Fighter)
        self.assertEqual(ds.hgetall('u:Fighter:name'), {'Alice': '1', 'Bob': '2'})
        self.assertEqual(ds.smembers('i:Fighter:city:1'), set(['1', '2']))
        fighter1 = Fighter(Fighter.by_id(1))
        fighter_writer.delete(fighter1)
        self.assertRaises(NotFoundError, Fighter, Fighter.by_id(1))
        self.assertTrue(fighter1.oid is None)
        self.assertEqual(ds.hgetall('u:Fighter:name'), {'Bob': '2'})
        self.assertEqual(ds.smembers('i:Fighter:city:1'), set(['2']))

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

        handle1 = Fighter.by_id(1)
        handle2 = Fighter.by_id(2)
        handle3 = Fighter.by_id(1)
        self.assertEqual(handle1, handle3)
        self.assertFalse(handle1 != handle3)
        self.assertFalse(handle1 == handle2)
        self.assertTrue(handle1 != handle2)

        city = City(fighter1.city)
        self.assertEqual(city.name, 'Reixte')
        conns = List(city.connections)
        self.assertEqual(len(conns), 2)
        city2 = City(conns[1])
        self.assertEqual(city2.name, 'Toynbe')

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
        handle = Gang.find(members__contains = hfighter2)
        self.assertEqual(handle, Gang.by_id(1))

        city_gangs = Gang.multifind(cities__contains = City.by_id(3))
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


def all_tests():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(ContainersTestCase))
    suite.addTest(unittest.makeSuite(ModelWriteTestCase))
    suite.addTest(unittest.makeSuite(ModelReadTestCase))
    return suite


if __name__ == "__main__":
    #suite = unittest.TestLoader().loadTestsFromTestCase(Test)
    suite = all_tests()
    unittest.TextTestRunner(verbosity=2).run(suite)
