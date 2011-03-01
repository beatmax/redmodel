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
