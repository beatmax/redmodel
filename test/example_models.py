from redmodel.models import Model, Attribute, BooleanField, IntegerField, FloatField, UTCDateTimeField, ReferenceField, ListField, SetField, Recursive
from redmodel.containers import List, Set

# City with a name, a boolean, and a list of connections to other cities
# (recursive references).
class City(Model):
    name = Attribute()
    coast = BooleanField()
    connections = ListField(Recursive)

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
class Fighter(Model):
    name = Attribute(unique = True)
    age = IntegerField(zindexed = True)
    weight = FloatField(zindexed = True)
    joined = UTCDateTimeField(zindexed = True)
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

if __name__ == '__main__':
    gang = Gang(Gang.by_id(1))
    print(gang)
    members = Set(gang.members)
    print(members)
    fighters = list(members)
    fighter1 = Fighter(fighters[0])
    fighter2 = Fighter(fighters[1])
    print(fighter1)
    print(fighter2)
    city = City(fighter1.city)
    print(city)
    conns = List(city.connections)
    print(conns)
    city2 = City(conns[1])
    print(city2)
