fruits = ['orange', 'apple', 'pear', 'banana', 'kiwi', 'apple', 'banana']
print(type(fruits))  #prints the type of the variable 'fruits'

# List methods

print(fruits.count('apple'))        #counts the number of times 'apple' appears in the list
print(fruits.count('tangerine'))    #counts the number of times 'tangerine' appears in the list
print(fruits.index('banana'))       #finds the index of the first occurrence of 'banana' in the list
print(fruits.index('banana', 4))    #finds the index of the first occurrence of 'banana' in the list, 
                                    #starting the search from index 4

fruits.reverse()                    #reverses the order of the elements in the list                     
print(fruits)

fruits.append('grape')              #adds 'grape' to the end of the list
print(fruits)

fruits.sort()                       #sorts the elements in the list in ascending order
print(fruits)

fruits.pop()                        #removes the last element from the list and returns it
print(fruits)

# Indexing and slicing in lists 

print(fruits[2:5])                  #prints the elements from index 2 to index 4 (5 is excluded)
print(fruits[:4])                   #prints the elements from the beginning of the list to index 3 (4 is excluded)
print(fruits[2:])                   #prints the elements from index 2 to the end
print(fruits[-4:-1])                #prints the elements from index -4 to index -2 (-1 is excluded)
print(fruits[-1])                   #prints the last element in the list
print(fruits[-3:])                  #prints the last three elements in the list

