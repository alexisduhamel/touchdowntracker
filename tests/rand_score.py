import os
import csv
import random

rounds_dir = 'rounds'
files = [f for f in os.listdir(rounds_dir) if f.startswith('round') and f.endswith('.csv')]

for i, filename in enumerate(files, start=1):
    filepath = os.path.join(rounds_dir, filename)
    rows = []
    with open(filepath, newline='', encoding='utf-8') as csvfile:
        reader = list(csv.reader(csvfile))
        if reader:
            header = reader[0]
            rows.append(header)
            # Find indices for TouchdownA and TouchdownB
            try:
                idx_a = header.index('TouchdownA')
                idx_b = header.index('TouchdownB')
            except ValueError:
                idx_a = idx_b = None
            for row in reader[1:]:
                # Ensure row is long enough
                while len(row) < len(header):
                    row.append('')
                # For every empty field, assign a random int between 0 and 4
                for i in range(len(header)):
                    try:
                        cell = row[i]
                    except IndexError:
                        # Shouldn't happen due to padding, but guard anyway
                        row.append(str(random.randint(0, 4)))
                        continue
                    if isinstance(cell, str) and cell.strip() == '':
                        row[i] = str(random.randint(0, 4))
                rows.append(row)
    with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerows(rows)