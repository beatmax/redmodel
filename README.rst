========
Redmodel
========

Python Data Models for Redis.
Maximiliano Pin <mxcpin-AT-gmail-DOT-com>


Description
-----------

Redmodel is born as an alternative to Redisco. It's focused on model
relationships and indexes, and tries to be a thin but powerful layer on top of
redis.

The concepts of Handle and Writer are introduced, which make redmodel less
magic than redisco, but allow a finer control on what you are doing:

- A handle is a reference to an object stored in redis. A query, for instance,
  returns a handle or a set of handles, and does not load automatically the
  objects from redis. You must load them explicitly.

- A writer is an object used to write model objects or containers. The main
  reason for this is to allow writing code which only reads some models data,
  but is not able to write them. That's good to divide responsibilities in
  different modules, threads, or programs.

Test-driven development was used to create Redmodel, so it is and will be
extensively tested by automated tests located in the test directory.
I recomend you read the testing code if you want to understand the internals
of Redmodel.


Installation
------------

Redmodel requires redis-py. Install it first. Then run:

    sudo python ./setup.py install


Quick Example
-------------

This example code shows some Redmodel features. It's located in
test/quick_example.py (warning: test programs flush your redis database!).

::

    from redmodel.models import Model, Attribute, IntegerField, ListField
    from redmodel.models import ModelWriter, ListFieldWriter
    from redmodel.containers import List

    # clean all data
    from redmodel import connection
    connection.flushdb()

    # define Color class
    class Color(Model):
        name = Attribute(unique = True)
        rgb = IntegerField()

    # define Person class
    class Person(Model):
        name = Attribute(unique = True)
        fave_colors = ListField(Color, indexed = True)

    # create writer objects
    color_writer = ModelWriter(Color)
    person_writer = ModelWriter(Person)
    fave_colors_writer = ListFieldWriter(Person.fave_colors)

    # create some colors
    c1 = Color(name = 'red', rgb = 0xff0000)
    c2 = Color(name = 'green', rgb = 0x00ff00)
    c3 = Color(name = 'blue', rgb = 0x0000ff)

    # save the colors in Redis
    map(color_writer.create, [c1, c2, c3])

    # create a person in Redis
    person = Person(name = 'Cristina')
    person_writer.create(person)

    # set fave colors of this person
    fave_colors_writer.append(person.fave_colors, Color.find(name = 'blue'))
    fave_colors_writer.append(person.fave_colors, Color.find(name = 'green'))

    # list people who like color green
    green = Color.find(name = 'green')
    for handle in Person.multifind(fave_colors__contains = green):
        person = Person(handle)
        print(person.name)
        # print all colors she likes
        for color_handle in List(person.fave_colors):
            print(str(Color(color_handle)))


Model Definition
----------------

These example models have been created to test all redmodel features. They
model the data of an hypothetic game of gangs, whose members are fighters
which move along different cities. A game extension adds a skill system to
the fighters.

::

    from redmodel.models import Model, Attribute, BooleanField, IntegerField, FloatField, UTCDateTimeField
    from redmodel.models import ReferenceField, ListField, SetField, SortedSetField, Recursive

    # City with a name, a boolean, and a list of connections to other cities
    # (recursive references).
    class City(Model):
        name = Attribute()
        coast = BooleanField()
        connections = ListField(Recursive)

    # Weapon with a description and its power value.
    class Weapon(Model):
        description = Attribute()
        power = FloatField()

    # Fighter with name, age, weight, join time, and current city.
    # - The name is defined as unique, so fighters are indexed by name (we can
    #   find a fighter by name), and it cannot be repeated. The index is a
    #   redis hash.
    # - The datetime field is stored as an integer (no microseconds). It may be
    #   better to use an IntegerField directly, in order to avoid conversions.
    # - The current city is indexed, so we can find which fighters are in a
    #   city. This index is a collection of redis sets.
    # - Attributes which are zindexed have a redis sorted set associated, so we
    #   can execute queries like Fighter.zfind(age__lt = 30).
    # - Weapons are sorted by power. In this case, we have a redis sorted set
    #   for every Fighter object (with zindexed, we have one global sorted set).
    # - The weapons field could have been created as:
    #     weapons = SortedSetField(Weapon)
    #   So entries are not sorted by a specific field, but a 'score' must be
    #   specified as an additional parameter.
    #   If a field is specified, then owned must be True (see below for an
    #   explanation about 'owned'), and a weapon's power should not be updated
    #   directly, but using SortedSetFieldWriter's update or update_all methods,
    #   so the sorted set is automatically and atomically updated.
    class Fighter(Model):
        name = Attribute(unique = True)
        age = IntegerField(zindexed = True)
        weight = FloatField(zindexed = True)
        joined = UTCDateTimeField(zindexed = True)
        city = ReferenceField(City, indexed = True)
        weapons = SortedSetField(Weapon, Weapon.power, owned = True)

    # Gang with a name and a set of member fighters.
    # A fighter can only be the leader of one gang. This index is a redis hash.
    # Members are indexed uniquely. That means a fighter can be in one gang
    # only. This index is a single redis hash.
    # Cities where the gang operates are indexed, so we can find which gangs
    # operate in a city. This index is a collection of redis sets.
    class Gang(Model):
        name = Attribute()
        leader = ReferenceField(Fighter, unique = True)
        members = SetField(Fighter, unique = True)
        cities = SetField(City, indexed = True)

    # Skill that fighters can have.
    class Skill(Model):
        category = Attribute()
        name = Attribute()
        description = Attribute()

    # Skill instance: a skill with a value.
    class SkillInstance(Model):
        skill = ReferenceField(Skill)
        value = IntegerField()

    # Skills a fighter has.
    # - This model is owned by the Fighter model ("owner = Fighter"). So, this
    #   model is an extension to the Fighter model. This is useful to implement
    #   plugins or independent modules with independent data, instead of
    #   modifying the base model (Fighter in this example).
    # - SkillInstance objects in the skills list are owned by this model
    #   ("owned = True"). This means that:
    #   1. New SkillInstance objects can be created and added to the list
    #      atomically.
    #   2. An object removed from the list is deleted automatically.
    class FighterSkillList(Model):
        owner = Fighter
        skills = ListField(SkillInstance, owned = True)


Creating Objects
----------------

Let's create some data for our example model.

Create some cities:

::

    from redmodel.models import ModelWriter
    city_writer = ModelWriter(City)
    c1 = City(name = 'Reixte', coast = True)
    c2 = City(name = 'Damtoo', coast = True)
    c3 = City(name = 'Toynbe', coast = False)
    map(city_writer.create, [c1, c2, c3])

Create connections between cities:

::

    from redmodel.models import ListFieldWriter
    city_connections_writer = ListFieldWriter(City.connections)
    city_connections_writer.append(c1.connections, c2)
    city_connections_writer.append(c2.connections, c1)
    city_connections_writer.append(c1.connections, c3)
    city_connections_writer.append(c3.connections, c1)

Create some fighters:

::

    from datetime import datetime
    fighter_writer = ModelWriter(Fighter)
    dtime = datetime.utcfromtimestamp(1400000000)
    f1 = Fighter(name = 'Alice', age = 29, weight = 73.2, joined = dtime, city = City.by_id(1))
    f2 = Fighter(name = 'Bob', age = 32, weight = 98, joined = dtime, city = City.by_id(1))
    map(fighter_writer.create, [f1, f2])

Create a gang and add both fighters to it:

::

    gang_writer = ModelWriter(Gang)
    g = Gang(name = 'Ghetto Warriors', leader = f1)
    gang_writer.create(g)

    from redmodel.models import SetFieldWriter
    gang_members_writer = SetFieldWriter(Gang.members)
    gang_members_writer.append(g.members, f1)
    gang_members_writer.append(g.members, f2)

Add some weapons to fighter f1. Notice that we attach weapon_writer to
fighter_weapons_writer as the "element_writer", so objects are created and
deleted automatically (we can do this because the "weapons" container of
Fighter has "owned = True"). Furthermore, this will be useful when updating
the objects to keep the set sorted (see later):

::

    weapon_writer = ModelWriter(Weapon)
    fighter_weapons_writer = SortedSetFieldWriter(Fighter.weapons, weapon_writer)
    w1 = Weapon(description = 'second', power = 50.5)
    w2 = Weapon(description = 'third', power = 34.2)
    w3 = Weapon(description = 'first', power = 50.7)
    for w in w1, w2, w3:
        fighter_weapons_writer.append(f1.weapons, w)

Create some skill definitions:

::

    skill_writer = ModelWriter(Skill)
    sk1 = Skill(category = 1, name = 'Strength', description = 'Strength...')
    sk2 = Skill(category = 3, name = 'Karate', description = 'Karate...')
    map(skill_writer.create, [sk1, sk2])

Attach FighterSkillList objects to existing Fighter objects:

::

    fighter_skill_list_writer = ModelWriter(FighterSkillList)
    f1skills = FighterSkillList()
    f2skills = FighterSkillList()
    fighter_skill_list_writer.create(f1skills, f1)
    fighter_skill_list_writer.create(f2skills, f2)

Add skill instances to fighter skill lists. Notice that we attach
skill_instance_writer to fighter_skills_writer as the "element_writer":

::

    skill_instance_writer = ModelWriter(SkillInstance)
    fighter_skills_writer = ListFieldWriter(FighterSkillList.skills, element_writer = skill_instance_writer)

    ski1 = SkillInstance(skill = sk1, value = 21)
    ski2 = SkillInstance(skill = sk2, value = 15)
    fighter_skills_writer.append(f1skills.skills, ski1)
    fighter_skills_writer.append(f1skills.skills, ski2)

    ski1 = SkillInstance(skill = sk1, value = 27)
    ski2 = SkillInstance(skill = sk2, value = 91)
    fighter_skills_writer.append(f2skills.skills, ski1)
    fighter_skills_writer.append(f2skills.skills, ski2)


Reading Data
------------

We can build a handle for an object by id. This implies no access to redis.
If the object does not exist, the handle is valid anyway:

::

    handle = Gang.by_id(1)

To read the data from redis, we create a model object, passing a handle to the
constructor:

::

    gang = Gang(handle)

Container fields (lists, sets and sorted sets) are not read automatically from
redis. Instead, a handle for the container is generated in the owner object.
They are loaded using the List, Set and SortedSet classes from
redmodel.containers.  A List, Set or SortedSet object contains a collection
of object handles (but notice that containers of elementary types can also
exist).

This is how we list the gang member fighters:

::

    from redmodel.containers import Set
    members = Set(gang.members)
    for handle in members:
        print(str(Fighter(handle)))

SortedSet has some query methods in addition to the read constructor.
These methods wrap z* redis functions (plus the convenience zfind method).
These are further explained in the Containers section. So, we can make some
queries on a fighter weapon set:

::

    fighter1 = Fighter(Fighter.by_id(1))
    # normal read constructor: returns sorted weapon handle list
    sorted_weapons = SortedSet(fighter1.weapons)
    # read constructor with filter (returns weapons with power greater than 50)
    powerful_weapons = SortedSet(fighter1.weapons, gt = 50)
    # alternative method to get the same
    powerful_weapons = SortedSet.zfind(fighter1.weapons, gt = 50)
    # top 10 fighter1's most powerful weapons
    top_weapons = SortedSet.zrevrange(fighter1.weapons, 0, 9)

For owned models, use by_owner() to create handles and read data:

::

    # an owner handle or object can be used
    fighter1 = Fighter(Fighter.by_id(1))
    handle = FighterSkillList.by_owner(fighter1)
    fsl = FighterSkillList(handle)


Queries
-------

Find in unique index:

::

    hbob = Fighter.find(name = 'Bob')
    if not hbob:
        print('Fighter not found.')

    # trying to read from an invalid handle would raise NotFoundError,
    # so we can do this instead:
    from redmodel.models import NotFoundError
    try:
        fighter = Fighter(Fighter.find(name = 'Bob'))
    except NotFoundError:
        print('Fighter not found.')


Find in non unique index:

::

    # find all fighters which are currently in city number 1;
    # the result is a set of Fighter handles
    city_fighters = Fighter.multifind(city = City.by_id(1))

Find in unique container index:

::

    bobs_gang = Gang(Gang.find(members__contains = hbob))

Find in non unique container index:

::

    # find all gangs which operate in city number 3;
    # the result is a set of Gang handles
    city_gangs = Gang.multifind(cities__contains = City.by_id(3))


Queries on Sorted Indexes
-------------------------

For fields which are zindexed, methods that wrap z* redis functions are
available (similar to those on sorted set fields explained before).
These methods return a sorted list of handles:

::

    # get a list of Fighter handles sorted by fighters weight
    # (notice there's no sorting operation here; we are keeping a sorted index)
    sorted_by_weight = Fighter.zrange('weight')

    # get the top ten heaviest fighters
    heaviest_fighters = Fighter.zrevrange('weight', 0, 9)

    # get list of fighters less or equal than 24 years old
    # (notice you can use zfind for this; see below)
    young_fighters = Fighter.zrangebyscore('age', '-inf', 24)

    # get first 3 fighters greater than 39 years old (39 not included)
    mature_fighters = Fighter.zrangebyscore('age', '(39', '+inf', 0, 3)

The convenience zfind method may be used instead of zrangebyscore:

::

    young_fighters = Fighter.zfind(age__lt = 25)
    mature_fighters = Fighter.zfind(age__gte = 40)
    in_their_twenties = Fighter.zfind(age__in = (20, 29))
    age_match = Fighter.zfind(age = 23)
    joined_before_2020 = Fighter.zfind(joined__lt = datetime(2020, 1, 1))

Other available methods:

::

    # count fighters in an age range
    Fighter.zcount('age', 20, 23)

    # get position of fighter in zero-based weight ranking (increasing order)
    Fighter.zrank('weight', fighter1)

    # get position of fighter by handle in weight ranking (decreasing order)
    Fighter.zrevrank('weight', hfighter2)


Updating Data
-------------

Object attributes can be updated in two ways:
(notice that indexes are updated automatically)

::

    # Method 1:
    fighter = Fighter(Fighter.by_id(2))
    fighter_writer.update(fighter, name = 'Robert', weight = 99.9)

    # Method 2:
    fighter = Fighter(Fighter.by_id(2))
    fighter.name = 'Bobby'
    fighter.age = 41
    fighter_writer.update_all(fighter)

Update a sorted set field owned element while resorting the set atomically:

::

    w2 = Weapon(Weapon.by_id(2))
    fighter_weapons_writer.update(fighter1.weapons, w2,
                                  power = 70, description = 'improved')
    w2.power -= 60
    w2.description = 'degraded'
    fighter_weapons_writer.update_all(fighter1.weapons, w2)

Delete an object. Notice that containers referencing this object will contain
now an invalid handle! Use container fields with "owned = True" whenever
possible, so objects are deleted automatically when removing its handle from
the container.

::

    fighter_writer.delete(fighter1)

Remove items from containers (see note above about containers with owned
elements):

::

    gang1 = Gang(Gang.by_id(1))
    gang_members_writer.remove(gang1.members, Fighter.by_id(2))


Containers
----------

We've seen how to use container fields in models, but standalone containers may
also be used, which can hold model objects and even be indexed. Some examples:

::

    from redmodel.containers import List, Set, SortedSet
    from redmodel.containers import ListHandle, SetHandle, SortedSetHandle
    from redmodel.containers import ListWriter, SetWriter, SortedSetWriter

    # a list of strings
    writer = ListWriter(str)
    hlist = ListHandle('mylist', str)
    writer.append(hlist, 'spam')
    writer.append(hlist, 'eggs')
    read_list = List(hlist)

    # a set of integers
    writer = SetWriter(int)
    hset = SetHandle('myset', int)
    writer.append(hset, 11)
    writer.append(hset, 13)
    writer.append(hset, 17)
    read_set = Set(hset)

    # a sorted set of strings (sorted by a float score)
    writer = SortedSetWriter(str)
    hzset = SortedSetHandle('myzset', str)
    writer.append(hzset, 'spam', 3.25)
    writer.append(hzset, 'eggs', 3.24)
    read_zset = SortedSet(hzset)
    read_zset = SortedSet(hzset, gt = 3.24)  # returns ('spam',)

    # SortedSet has z* query methods which map redis z* functions,
    # plus convenience zfind method (as an alternative to zrangebyscore)
    sorted_elements = SortedSet.zrange(hzset)
    top_ten = SortedSet.zrevrange(hzset, 0, 9)
    first_greater = SortedSet.zrangebyscore(hzset, '(3.24', '+inf', 0, 1)
    all_greater = SortedSet.zfind(hzset, gt = 3.24)
    score_match = SortedSet.zfind(hzset, eq = 3.24)
    range_count = SortedSet.zcount(hzset, 3.24, 3.25)
    element_position = SortedSet.zrank(hzset, 'spam')
    rev_element_position = SortedSet.zrevrank(hzset, 'eggs')

    # a list of objects
    writer = ListWriter(Fighter)
    hlist = ListHandle('mylist', Fighter)
    writer.append(hlist, Fighter.by_id(2))

    # an indexed set
    writer = SetWriter(int, index_key = 'myindex')
    hset1 = SetHandle('myset:1', int)
    hset2 = SetHandle('myset:2', int)
    for i in 1, 2, 3:
        writer.append(hset1, i)
    for i in 2, 3, 4, 5:
        writer.append(hset2, i)
    # redis sets 'myindex:1' to 'myindex:5' have been created

    # an unique indexed set
    writer = SetWriter(int, index_key = 'myindex', unique_index = True)
    hset1 = SetHandle('myset:1', int)
    hset2 = SetHandle('myset:2', int)
    for i in 1, 2, 3:
        writer.append(hset1, i)
        writer.append(hset2, i + 3)
    # redis hash 'myindex' has been created with these values:
    # {'1': '1', '2': '1', '3': '1', '4': '2', '5': '2', '6': '2'}


Credits
-------

Thanks to Tim Medina, author of Redisco. Most concepts in Redmodel are taken
from Redisco. Also, I learned a lot from his code.

Thanks to Salvatore Sanfilippo for creating Redis.
