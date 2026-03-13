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
        with open(file_path, 'r', encoding='utf-8') as file: 
            reader = csv.reader(file)
            header = next(reader)
            teamA_idx = header.index('TeamA') if 'TeamA' in header else None
            teamB_idx = header.index('TeamB') if 'TeamB' in header else None
            playerA_idx = header.index('PlayerA') if 'PlayerA' in header else None
            playerB_idx = header.index('PlayerB') if 'PlayerB' in header else None
            for row in reader:
                if config['team_size'] > 1 and teamA_idx is not None and teamB_idx is not None:
                # If team_size > 1, treat as teams; else, as players
                    value1 = row[teamA_idx]  # Team A
                    value2 = row[teamB_idx]  # Team B
                else:
                    value1 = row[playerA_idx]  # Player A
                    value2 = row[playerB_idx]  # Player B
                normalized_pair = tuple(sorted((value1, value2)))
                pair_counts[normalized_pair] = pair_counts.get(normalized_pair, 0) + 1
    # Check if each pair_counts appear exactly config['team_size'] times
    all_unique_pairs = set()
    for pair, count in pair_counts.items():
        if count != config['team_size']:
            log.warning(f"Pair {pair} appears {count} times, expected {config['team_size']} times.")
        all_unique_pairs.add(pair)
    return all_unique_pairs

if __name__ == "__main__":
    log.basicConfig(format='%(levelname)s - %(message)s', level=log.INFO)
    rounds_folder_name = 'rounds'
    all_unique_pairs = process_csv_files(rounds_folder_name, config["team_size"])
    print("\n--- Summary ---")
    print(f"Total unique pairs found: {len(all_unique_pairs)}")
