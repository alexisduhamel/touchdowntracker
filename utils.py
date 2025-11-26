
import csv
import logging as log
import yaml

from pathlib import Path
from globals import *

def loadPlayers(filepath='config/players.csv'):
    """
    Load player data from a CSV file into a dictionary.
    Each player is keyed by name, with their attributes as values.
    """
    players = {}
    teams = {}
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f'{filepath} not found.')

    with open(path, mode='r', encoding='utf-8') as file:
        reader = csv.reader(file)
        header = next(reader)
        has_team = 'Team' in header

        for row in reader:
            if len(row) < len(header):
                continue  # skip malformed lines
            player_data = dict(zip(header, row))
            name = player_data.get('Player', row[0])
            players[name] = player_data

            if has_team:
                team_name = player_data.get('Team')
                if not team_name:  # enforce every player has a team
                    raise ValueError(f"Player '{name}' has no team assigned.")
                teams.setdefault(team_name, []).append(name)

    # If we have teams, validate team sizes
    if has_team and teams:
        team_sizes = {team: len(roster) for team, roster in teams.items()}
        unique_sizes = set(team_sizes.values())
        if len(unique_sizes) > 1:
            mismatch = ", ".join(f"{t}: {s}" for t, s in team_sizes.items())
            raise ValueError(f"Inconsistent team sizes detected -> {mismatch}")
        config['team_size'] = unique_sizes.pop()
        config['teams'] = teams
    
    # If we track tier, assign values based on tiers.yaml

    if 'tier' in config['statistics']:
        with open('config/tiers.yaml', 'r', encoding='utf-8') as f:
            tiers = yaml.safe_load(f)

        for player in players:
            if players[player]['Race'] not in tiers:
                raise ValueError(f"Race '{players[player]['Race']}' for player '{player}' has no tier defined in tiers.yaml.")
            players[player]['tier'] = tiers[players[player]['Race']]

    return players
    
def loadStats(filepath='stats/statistics.csv'):
    """
    Load player statistics from a CSV file into a dictionary.
    If the file does not exist, create it with the appropriate header
    based on config['statistics'] and config['additional_statistics'].
    """
    stats = {}
    path = Path(filepath)
    stats_header = ['Player'] + config.get('statistics', []) + config.get('additional_statistics', [])

    if not path.exists():
        # Create file with header from config
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, mode='w', encoding='utf-8', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(stats_header)
        return stats

    with open(path, mode='r', encoding='utf-8') as file:
        reader = csv.reader(file)
        try:
            header = next(reader)
        except StopIteration:
            return stats  # empty file

        stat_names = header[1:]  # everything after 'Player'
        for row in reader:
            if not row or len(row) == 0:
                continue
            name = row[0]
            # build dict for this player from header columns, filling missing with 0
            player_stats = {}
            for idx, stat in enumerate(stat_names):
                col_idx = idx + 1
                val = row[col_idx] if col_idx < len(row) else ''
                # normalize empty -> 0, try int then float, else keep string
                if val == '':
                    conv = 0
                else:
                    try:
                        conv = int(val)
                    except ValueError:
                        try:
                            conv = float(val)
                        except ValueError:
                            conv = val
                player_stats[stat] = conv
            stats[name] = player_stats

    return stats

def loadRound(filepath='rounds/round1.csv'):
    """
    Load a round's results from a CSV file.
    Returns a list of match results for the round.
    """
    round = []
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f'{filepath} not found')
    with open(path, mode='r', encoding='utf-8') as file:
        reader = csv.reader(file)
        next(reader) # skip first line
        for row in reader:
            round.append(row)
    return round

def savePairing(round_number, pairing):
    """
    Save the pairings for a round to a CSV file.
    Handles both team and individual formats.
    """
    filepath = f'rounds/round{round_number}.csv'
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Need access to players_dict for team info
    from inspect import currentframe
    frame = currentframe()
    players_dict = frame.f_back.f_locals.get('players_dict', {})
    team_size = int(config.get('team_size', 1))

    with open(path, mode='w', encoding='utf-8', newline="") as file:
        writer = csv.writer(file)
        if team_size > 1:
            # Write header with stats columns based on tie breaks and additional stats
            header = ['TeamA', 'PlayerA', 'TouchdownA']
            for stat in config['statistics'] + config['additional_statistics']:
                if stat not in config['base_statistics']:
                    header.append(f'{stat}A')
            header_part_size = len(header)
            header += ['TeamB', 'PlayerB', 'TouchdownB']
            for stat in config['statistics'] + config['additional_statistics']:
                if stat not in config['base_statistics']:
                    header.append(f'{stat}B')
            writer.writerow(header)
            for game in pairing:
                pA, pB = game[0], game[1]

                row = [''] * (2*header_part_size)

                row[header.index('TeamA')] = players_dict.get(pA, {}).get('Team', '') if pA != 'BYE' else 'BYE'
                row[header.index('PlayerA')] = pA
                row[header.index('TeamB')] = players_dict.get(pB, {}).get('Team', '') if pB != 'BYE' else 'BYE'
                row[header.index('PlayerB')] = pB

                if 'tier' in config['statistics'] + config['additional_statistics']:
                    row[header.index('tierA')] = players_dict.get(pA, {}).get('tier', '') if pA != 'BYE' else ''
                    row[header.index('tierB')] = players_dict.get(pB, {}).get('tier', '') if pB != 'BYE' else ''
                writer.writerow(row)
        else:
            writer.writerow(['PlayerA', 'PlayerB', 'TouchdownA', 'TouchdownB'])
            for game in pairing:
                writer.writerow([game[0], game[1], '', ''])
    log.info(f'{path} saved.')

def savePairingHtml(round_number, pairing):
    """
    Save the pairings for a round to an HTML file.
    Handles both team and individual formats and mirrors savePairing's
    behavior for config['statistics'] and config['additional_statistics'].
    """
    filepath = f'rounds/round{round_number}.html'
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Need access to players_dict for team info
    from inspect import currentframe
    from html import escape
    frame = currentframe()
    players_dict = frame.f_back.f_locals.get('players_dict', {})
    team_size = int(config.get('team_size', 1))

    with open(path, mode='w', encoding='utf-8') as file:

        file.write('<html><head>\n')
        file.write('    <title>Round {}</title>\n'.format(round_number))
        file.write('    <style>\n')
        file.write('        table, th, td { text-align: center; }\n')
        file.write('    </style>\n')
        file.write('</head>\n')
        file.write('<body>\n')
        file.write('<h1>Round {}</h1>\n'.format(round_number))


        if team_size > 1:
            # Build header grouped by A then B
            base_a = ['TeamA', 'PlayerA', 'TouchdownA']
            base_b = ['TeamB', 'PlayerB', 'TouchdownB']

            extra_stats = []
            for stat in config['statistics'] + config['additional_statistics']:
                if stat not in config['base_statistics']:
                    extra_stats.append(stat)

            header = base_a + [f'{s}A' for s in extra_stats] + base_b + [f'{s}B' for s in extra_stats]

            # get the game and index
            for game, idx in zip(pairing, range(0, len(pairing))):

                if idx%team_size == 0:
                    file.write('<table border="1">\n')
                    # write header row with readable labels
                    file.write('<tr>')
                    for h in header:
                        if h.endswith('A') or h.endswith('B'):
                            label = h[:-1] + ' ' + h[-1]
                        else:
                            label = h
                        file.write(f'<th>{escape(label)}</th>')
                    file.write('</tr>\n')

                pA, pB = game[0], game[1]

                row = [''] * len(header)

                # build A block then B block
                row[header.index('TeamA')] = players_dict.get(pA, {}).get('Team', '') if pA != 'BYE' else 'BYE'
                row[header.index('PlayerA')] = pA
                row[header.index('TeamB')] = players_dict.get(pB, {}).get('Team', '') if pB != 'BYE' else 'BYE'
                row[header.index('PlayerB')] = pB

                # If tier is tracked, fill tier columns (matching savePairing)
                if 'tier' in config['statistics'] + config['additional_statistics']:
                    # set tierA and tierB in row
                    row[header.index('tierA')] = players_dict.get(pA, {}).get('tier', '') if pA != 'BYE' else ''
                    row[header.index('tierB')] = players_dict.get(pB, {}).get('tier', '') if pB != 'BYE' else ''

                # write the row
                file.write('<tr>')
                for cell in row:
                    file.write(f'<td>{escape(str(cell))}</td>')
                file.write('</tr>\n')
                if idx%team_size == team_size - 1:
                    file.write('</table><br>\n')
        else:
            # individual format
            file.write('<tr><th>Player A</th><th>Player B</th><th>Touchdown A</th><th>Touchdown B</th></tr>\n')
            for game in pairing:
                file.write('<tr><td>{}</td><td>{}</td><td></td><td></td></tr>\n'.format(escape(game[0]), escape(game[1])))

        file.write('</table>\n')
        file.write('</body></html>\n')
    log.info(f'{path} saved.')

def saveStats(stats, filepath='stats/statistics.csv'):
    """
    Save player statistics to a CSV file.
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, mode='w', encoding='utf-8', newline="") as file:
        writer = csv.writer(file)
        writer.writerow(['Player'] + config['statistics'] + config['additional_statistics'])
        for player in stats:
            log.debug(f'Saving stats for player: {player} : {stats[player]}')
            s = stats[player]
            writer.writerow([player] + [s.get(stat, 0) for stat in (config['statistics']+ config['additional_statistics'])])
    log.info(f'{filepath} saved.')

def saveTeamStats(team_stats, filepath='stats/team_statistics.csv'):
    """
    Save team statistics to a CSV file.
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, mode='w', encoding='utf-8', newline="") as file:
        writer = csv.writer(file)
        writer.writerow(['Team'] + config['statistics'] + config['additional_statistics'])
        for team, stats in team_stats.items():
            writer.writerow([team] + [stats.get(stat, 0) for stat in (config['statistics'] + config['additional_statistics'])])
    log.info(f'{filepath} saved.')