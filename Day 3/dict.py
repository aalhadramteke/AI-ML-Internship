data = { "name": "Aalhad", "age": 20, "city": "Nagpur"}
print(data)
print(type(data))                                   #prints the type of the variable 'data'

# Accessing items in Dictionaries

print(data["name"])                                 #prints the value of the key "name"
print(data["age"])                                  #prints the value of the key "age"
print(data["city"])                                 #prints the value of the key "city"

#Updating items in Dictionaries

data["phone"] = "9421722770"                        #add new key
data["age"] = 20                                    #update existing key
data.update({"salary": 25000, "city": "Pune"})
print(dict(data))                                   #prints the updated dictionary

#Viewing items in Dictionaries

print(data.keys())                                  #prints the keys of the dictionary
print(data.values())                                #prints the values of the dictionary
print(data.items())                                 #prints the key-value pairs of the dictionary