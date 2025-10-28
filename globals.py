import argparse
import yaml

version = 0.1
with open('config/config.yaml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

# Global argparse setup
parser = argparse.ArgumentParser(description='Touchdown Tracker')
parser.add_argument('--loglevel', type=str, default='INFO', help='Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)')
args = parser.parse_args()