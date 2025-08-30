import csv
import pathlib
import logging as log
import yaml

with open('config/config.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

def process_csv_files(folder_path, team_size):
    """
    Processes all CSV files in a given folder, extracting unique pairs
    from the first two columns. If team_size > 1, treat columns as teams;
    else, treat as players.

    Args:
        folder_path (str or pathlib.Path): The path to the folder containing the CSV files.
        team_size (int): The configured team size.

    Returns:
        set: A set of unique, normalized pairs (tuples).
    """
    rounds_folder = pathlib.Path(folder_path)
    pair_counts = {}

    if not rounds_folder.is_dir():
        print(f"Error: The folder '{rounds_folder}' does not exist.")
        return set(pair_counts.keys())

    csv_files = rounds_folder.glob('*.csv')

    for file_path in csv_files:
        print(f"Processing file: {file_path}")
        try:
            with file_path.open(mode='r', newline='', encoding='utf-8') as file:
                reader = csv.reader(file)
                next(reader, None)
                for row in reader:
                    if len(row) >= 2:
                        # If team_size > 1, treat as teams; else, as players
                        if team_size > 1:
                            value1 = row[0].strip()  # Team 1
                            value2 = row[1].strip()  # Team 2
                        else:
                            value1 = row[0].strip()  # Player 1
                            value2 = row[1].strip()  # Player 2
                        normalized_pair = tuple(sorted((value1, value2)))
                        pair_counts[normalized_pair] = pair_counts.get(normalized_pair, 0) + 1
        except Exception as e:
            print(f"Error processing {file_path}: {e}")
    duplicates = [pair for pair, count in pair_counts.items() if count > team_size]
    if duplicates:
        log.info(f"Duplicate pairings found: {duplicates}")
    return set(pair_counts.keys())

if __name__ == "__main__":
    log.basicConfig(format='%(levelname)s - %(message)s', level=log.INFO)
    rounds_folder_name = 'rounds'
    all_unique_pairs = process_csv_files(rounds_folder_name, config["team_size"])
    print("\n--- Summary ---")
    print(f"Total unique pairs found: {len(all_unique_pairs)}")
