# TouchdownTracker

Python-based script suite for Blood Bowl tournament management.

## Features

- Configurable tie breakers for swiss rounds
- Handles individual and team competitions (team competitions will be double swiss pairings, i.e. best player of team A against best player of team B)
- Extra statistics tracking that does not impact rankings (e.g: casualties, fouls, passes...)  

## Usage

### Requirements
- Python 3.x
- Install required packages:
```powershell
pip install -r requirements.txt
```

### Running the Script
```powershell
python touchdowntracker.py --loglevel INFO
```

### Basic Workflow
1. Configure tournament settings in `config/config.yaml`.
2. Add player data in `config/players_indiv.csv` (if your config.yaml is configured for individual play) or `config/players_team.csv` (if your config.yaml is for team play).
3. Run the script to generate pairings and update statistics.
4. Results and statistics are saved in the `rounds/` and `stats/` folders.

### Command Line Options
- `--loglevel`: Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

### Example

To generate statistics and the next round:
```powershell
python touchdowntracker.py
```
