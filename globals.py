import argparse
import yaml

version = 0.1
with open('config/config.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

# Global argparse setup
parser = argparse.ArgumentParser(description='Touchdown Tracker')
parser.add_argument('--loglevel', type=str, default='INFO', help='Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)')
args = parser.parse_args()

# Base stats to track
config['base_statistics'] = [
    'rank', 'points',
    'wins', 'draws', 'losses',
    'touchdown_scored', 'touchdown_conceded', 'touchdown_diff'
]

_stats = config['base_statistics'].copy()

# Mapping of known tie-breaker to the stats they require
_tie_break_to_stat = {
    'wins'              : 'wins',
    'draws'             : 'draws',
    'offense'           : 'touchdown_scored',
    'diff'              : 'touchdown_diff',
    'defense'           : 'touchdown_conceded',
    'casualties'        : 'casualities',
    'fouls'             : 'fouls',
    'passes'            : 'passes',
    'tier'              : 'tier',
    'touchdowns'        : 'touchdown_diff',
}

# Process individual tie_breakers from config
for tie_break in config.get('indiv_tie_breakers', []):
    if tie_break in _tie_break_to_stat:
        _stats.append(_tie_break_to_stat[tie_break])

# Process team tie_breakers from config
for tie_break in config.get('team_tie_breakers', []):
    if tie_break in _tie_break_to_stat:
        _stats.append(_tie_break_to_stat[tie_break])

# Remove duplicates while preserving order
seen = set()
unique_stats = []
for s in _stats:
    if s not in seen:
        seen.add(s)
        unique_stats.append(s)

# Attach deduplicated statistics to the loaded config
config['statistics'] = unique_stats

# Include any additional statistics that aren't already in _stats
config['additional_statistics'] = [stat for stat in config['additional_statistics'] if stat not in _stats]