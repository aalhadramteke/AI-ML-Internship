cars = ("benz", "merc", "safari", "bmw", "audi")  #tuple of car brands
print(cars)
print(type(cars))               #prints the type of the variable 'cars' 

# Indexing & Slicing in Tuples

print(cars[0])                  #prints the first element in the tuple
print(cars[1:4])                #prints the elements from index 1 to index 3 (4 is excluded)
print(cars[:3])                 #prints the elements from the beginning of the tuple to index 2 (3 is excluded)
print(cars[-3:-1])              #prints the elements from index -3 to index -2 (-1 is excluded)

# Accessing in Tuples

tup = tuple('AALHADRAMTEKE')    #creates a tuple from the string 'AALHADRAMTEKE'

print(tup[1:])
print(tup[::-1])
print(tup[4:9])

# Concatenation of Tuples

concatenated_tuple = cars + tup  #concatenates the tuples 'cars' and 'tup'
print(concatenated_tuple)

# Deleting Tuples

num = (0, 1, 2, 3, 4)
del num
print(num)                       #this will raise an error since the tuple 'num' has been deleted