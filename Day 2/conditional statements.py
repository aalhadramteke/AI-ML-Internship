# CONDITIONAL STATEMENTS IN PYTHON

#if statement

a = int(input("Enter a number: "))
if a > 5:
    print("a is greater than 5")
    print("a =", a)

#if-else statement 

b = int(input("Enter another number: "))

if b < 5:
    print("b is less than 5")
    print("b =", b)
else:
    print("b is not less than 5")
    print("b =", b)

#elif statement

c = int(input("Enter a third number: "))
if c > 20:
    print("c is greater than 20")
    print("c =", c)
elif c > 10:
    print("c is greater than 10 but not greater than 20")
    print("c =", c)
else:
    print("c is not greater than 10")
    print("c =", c)


