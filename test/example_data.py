from test.example_models import City, Fighter, Gang, Skill, SkillInstance, FighterSkillList
from redmodel.models import ModelWriter, ListFieldWriter, SetFieldWriter
from redmodel import connection as ds

# --- City ---

city_writer = ModelWriter(City)
city_connections_writer = ListFieldWriter(City.connections)

def create_city(name_):
    city = City(name = name_)
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

def create_fighter(name_):
    f = Fighter(name = name_, age = 20, weight = 100, city = 1)
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
    gang = Gang(name = name_, leader = leader_)
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

    c1 = create_city('Reixte')
    c2 = create_city('Damtoo')
    c3 = create_city('Toynbe')
    create_connection(c1, c2)
    create_connection(c1, c3)

    f1 = create_fighter('Alice')
    f2 = create_fighter('Bob')

    g = create_gang('Ghetto Warriors', f1)
    add_member(g, f1)
    add_member(g, f2)
    add_gang_city(g, c1)
    add_gang_city(g, c3)

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
