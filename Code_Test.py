name = input("What is your name? ")
age = int(input("How old are you? "))

current_year = 2026
years_until_100 = 100 - age
year_turn_100 = current_year + years_until_100

print(f"\nHello, {name}!")
print(f"You are {age} years old.")
print(f"You will turn 100 in the year {year_turn_100}.")