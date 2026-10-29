from typing import Union

a = {1, 2, 3, 4, 5}
b = {4, 5, 6, 7, 8}
print("Set A:", a)
print("Set B:", b)

#Adding Elements

a.add(9)
print("After add(9):", a)

a.update([10, 11])
print("After update([10,11]):", a)

#Removing Elements

a.remove(11)          
a.discard(10)        
a.pop()               
print("After removals:", a)

#Union of Sets

print("Union (a | b):", a | b)
print("Union (a.union(b)):", a.union(b))

#Intersection of Sets

print("Intersection (a & b):", a & b)
print("Intersection (a.intersection(b)):", a.intersection(b))

#Difference of Sets

print("Difference (a - b):", a - b)
print("Difference (b - a):", b - a)

#Subset & Superset

c = {1, 2}
print("c is subset of a:", c.issubset(a))
print("a is superset of c:", a.issuperset(c))
