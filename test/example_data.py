from test.example_models import City, Weapon, Fighter, Gang, Skill, SkillInstance, FighterSkillList
from redmodel.models import ModelWriter, ListFieldWriter, SetFieldWriter, SortedSetFieldWriter
from redmodel import connection as ds
from datetime import datetime

# --- City ---

city_writer = ModelWriter(City)
city_connections_writer = ListFieldWriter(City.connections)

def create_city(name_, coast_):
    city = City(name = name_, coast = coast_)
    city_writer.create(city)
    return city

def create_connection(city1, city2):
    assert isinstance(city1, City)
    assert isinstance(city2, City)
    # TODO multi-exec
    city_connections_writer.append(city1.connections, city2)
    city_connections_writer.append(city2.connections, city1)


# --- Fighter ---

fighter_writer = ModelWriter(Fighter)

def create_fighter(name_, age_, weight_, join_tstamp):
    joined_ = datetime.utcfromtimestamp(join_tstamp)
    f = Fighter(name = name_, age = age_, weight = weight_, joined = joined_, city = 1)
    fighter_writer.create(f)
    return f

def increase_age(name_):
    h = Fighter.find(name = name_)
    ds.hincrby(h.key, 'age')


# --- Gang ---

gang_writer = ModelWriter(Gang)
gang_members_writer = SetFieldWriter(Gang.members)
gang_cities_writer = SetFieldWriter(Gang.cities)

def create_gang(name_, leader_):
    gang = Gang(name = name_, leader = leader_, hqcity = City.by_id(3))
    gang_writer.create(gang)
    return gang

def add_member(gang, fighter):
    assert isinstance(gang, Gang)
    gang_members_writer.append(gang.members, fighter)

def add_gang_city(gang, city):
    assert isinstance(gang, Gang)
    gang_cities_writer.append(gang.cities, city)


# --- Example data ---

def load():
    ds.flushdb()

    c1 = create_city('Reixte', True)
    c2 = create_city('Damtoo', True)
    c3 = create_city('Toynbe', False)
    create_connection(c1, c2)
    create_connection(c1, c3)

    f1 = create_fighter('Alice', 20, 107.44, 1400000002)
    f2 = create_fighter('Bob', 23, 102.923, 1400000001)

    g1 = create_gang('Ghetto Warriors', f1)
    add_member(g1, f1)
    add_member(g1, f2)
    add_gang_city(g1, c1)
    add_gang_city(g1, c3)
    g2 = create_gang('Midnight Club', Fighter.by_id(0))

    # add weapons to fighter; weapons are owned (owned = True on the
    # SortedSetField), so we attach weapon writer to fighter weapons writer
    weapon_writer = ModelWriter(Weapon)
    fighter_weapons_writer = SortedSetFieldWriter(Fighter.weapons, weapon_writer)
    w1 = Weapon(description = 'second', power = 50.5)
    w2 = Weapon(description = 'third', power = 34.2)
    w3 = Weapon(description = 'first', power = 50.7)
    for w in w1, w2, w3:
        fighter_weapons_writer.append(f1.weapons, w)

    # skills
    skill_writer = ModelWriter(Skill)
    sk1 = Skill(category = 1, name = 'Strength', description = 'Strength...')
    sk2 = Skill(category = 3, name = 'Karate', description = 'Karate...')
    map(skill_writer.create, [sk1, sk2])

    fighter_skill_list_writer = ModelWriter(FighterSkillList)
    f1skills = FighterSkillList()
    f2skills = FighterSkillList()
    fighter_skill_list_writer.create(f1skills, f1)
    fighter_skill_list_writer.create(f2skills, f2)

    # can do this if and only if owned = True in the ListField
    skill_instance_writer = ModelWriter(SkillInstance)
    fighter_skills_writer = ListFieldWriter(FighterSkillList.skills, element_writer = skill_instance_writer)
    ski1 = SkillInstance(skill = sk1.handle(), value = 21)
    ski2 = SkillInstance(skill = sk2, value = 15)
    fighter_skills_writer.append(f1skills.skills, ski1)
    fighter_skills_writer.append(f1skills.skills, ski2)

    ski1 = SkillInstance(skill = sk1, value = 27)
    ski2 = SkillInstance(skill = sk2, value = 91)
    fighter_skills_writer.append(f2skills.skills, ski1)
    fighter_skills_writer.append(f2skills.skills, ski2)
