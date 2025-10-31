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
_stats = [
    'rank', 'points',
    'wins', 'draws', 'losses',
    'touchdown_scored', 'touchdown_received', 'touchdown_diff'
]

# Mapping of known tie-breaker to the stats they require
_tie_break_to_stat = {
    'most_wins'         : 'wins',
    'most_draws'        : 'draws',
    'most_touchdowns'   : 'touchdown_scored',
    'diff_touchdowns'   : 'touchdown_diff',
    'least_touchdowns'  : 'touchdown_received',
    'most_casualties'   : 'casualities',
    'most_fouls'        : 'fouls',
    'most_passes'       : 'passes',
    'highest_tier'      : 'tier',
}

# Process tie_breakers from config
for tie_break in config.get('indiv_tie_breakers', []):
    if tie_break in _tie_break_to_stat:
        _stats.append(_tie_break_to_stat[tie_break])

# Accept both 'team_tie_breakers' and the misspelled 'team_time_breakers'
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