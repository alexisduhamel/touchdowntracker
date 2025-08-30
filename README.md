# TouchdownTracker

Python-based script suite for Blood Bowl tournament management.

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
2. Add player data in `config/players_indiv.csv` or `config/players_team.csv`.
3. Run the script to generate pairings and update statistics.
4. Results and statistics are saved in the `rounds/` and `stats/` folders.

### Command Line Options
- `--loglevel`: Set logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

### Example
```powershell
python touchdowntracker.py --loglevel DEBUG
```
