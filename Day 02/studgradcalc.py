def calculate_grade(marks):
    total = sum(marks)
    average = total / len(marks)
    
    if average >= 90:
        grade = 'A'
    elif average >= 80:
        grade = 'B'
    elif average >= 70:
        grade = 'C'
    elif average >= 60:
        grade = 'D'
    else:
        grade = 'F'
        
    return total, average, grade

student_marks = [int(x) for x in input("Enter marks out of 100: ").split()]
total, avg, grade = calculate_grade(student_marks)
print(f"Your total marks are: {total}")
print(f"Your average marks are: {avg:.2f}")
print(f"Your Grade is: {grade}")