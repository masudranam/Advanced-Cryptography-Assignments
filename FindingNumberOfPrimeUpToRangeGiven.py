import csv
import math

def is_prime(n):
    if n <= 1:
        return False
    if n <= 3:
        return True
    if n % 2 == 0 or n % 3 == 0:
        return False
    i = 5
    while i * i <= n:
        if n % i == 0 or n % (i + 2) == 0:
            return False
        i += 6
    return True

def count_primes(limit):
    count = 0
    for num in range(2, limit + 1):
        if is_prime(num):
            count += 1
    return count

with open('input.csv', 'r') as infile:
    reader = csv.DictReader(infile)
    ranges = [int(row['range']) for row in reader]

results = []
for r in ranges:
    results.append({'range': r, 'prime_count': count_primes(r)})

with open('output.csv', 'w', newline='') as outfile:
    writer = csv.DictWriter(outfile, fieldnames=['range', 'prime_count'])
    writer.writeheader()
    writer.writerows(results)

print("Prime counts have been written to output.csv")
