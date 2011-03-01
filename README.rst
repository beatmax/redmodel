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

    from redmodel.models import Model, Attribute, IntegerField, ReferenceField, ListField, SetField, Recursive

    # City with a name and a list of connections to other cities
    # (recursive references).
    class City(Model):
        name = Attribute()
        connections = ListField(Recursive)

    # Fighter with name, age, weight, and current city.
    # - The name is defined as unique, so fighters are indexed by name (we can
    #   find a fighter by name), and it cannot be repeated. The index is a
    #   redis hash.
    # - The current city is indexed, so we can find which fighters are in a
    #   city. This index is a collection of redis sets.
    class Fighter(Model):
        name = Attribute(unique = True)
        age = IntegerField()
        weight = IntegerField()
        city = ReferenceField(City, indexed = True)

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
    c1 = City(name = 'Reixte')
    c2 = City(name = 'Damtoo')
    c3 = City(name = 'Toynbe')
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

    fighter_writer = ModelWriter(Fighter)
    f1 = Fighter(name = 'Alice', age = 29, weight = 73, city = City.by_id(1))
    f2 = Fighter(name = 'Bob', age = 32, weight = 98, city = City.by_id(1))
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
skill_instance_writer to fighter_skills_writer as the "element_writer", so
objects are created and deleted automatically (we can do this because the
"skills" container of FighterSkillList has "owned = True").

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

Container fields (lists and sets) are not read automatically from redis.
Instead, a handle for the container is generated in the owner object.
They are loaded using the List and Set classes from redmodel.containers.
A List or Set class contains a collection of object handles (but notice that
containers of elementary types can also exist).

This is how we list the gang member fighters:

::

    from redmodel.containers import Set
    members = Set(gang.members)
    for handle in members:
        print(str(Fighter(handle)))

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


Updating Data
-------------

Object attributes can be updated in two ways:
(notice that indexes are updated automatically)

::

    # Method 1:
    fighter = Fighter(Fighter.by_id(2))
    fighter_writer.update(fighter, name = 'Robert', weight = 99)

    # Method 2:
    fighter = Fighter(Fighter.by_id(2))
    fighter.name = 'Bobby'
    fighter.age = 41
    fighter_writer.update_all(fighter)

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

    from redmodel.containers import List, Set, ListHandle, SetHandle, ListWriter, SetWriter

    # a list of strings
    writer = ListWriter(str)
    hlist = ListHandle('mylist', str)
    writer.append(hlist, 'spam')
    writer.append(hlist, 'eggs')

    # a set of integers
    writer = SetWriter(int)
    hset = SetHandle('myset', int)
    writer.append(hset, 11)
    writer.append(hset, 13)
    writer.append(hset, 17)

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
