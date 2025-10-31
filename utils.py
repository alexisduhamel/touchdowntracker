
import csv
import logging as log

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

    return players
    
def loadStats(filepath='stats/statistics.csv'):
    """
    Load player statistics from a CSV file into a dictionary.
    If the file does not exist, create it with the appropriate header.
    """
    stats = {}
    path = Path(filepath)
    if not path.exists():
        # Create file with header
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, mode='w', encoding='utf-8', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['Player', 'Rank', 'Points', 'Touchdowns', 'Wins', 'Draws', 'Losses'])
        return stats
    with open(path, mode='r', encoding='utf-8') as file:
        reader = csv.reader(file)
        next(reader) # skip first line
        for row in reader:
            if len(row) < 7:
                continue # skip malformed lines
            name = row[0]
            rank = int(row[1])
            points = int(row[2])
            touchdowns = int(row[3])
            wins = int(row[4])
            draws = int(row[5])
            losses = int(row[6])
            stats[name] = {
                "rank": rank,
                "points": points,
                "touchdowns": touchdowns,
                "wins": wins,
                "draws": draws,
                "losses": losses
            }
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
    team_size = int(config.get('team_size', 1))
    with open(path, mode='r', encoding='utf-8') as file:
        reader = csv.reader(file)
        next(reader) # skip first line
        for row in reader:
            if team_size > 1:
                if len(row) < 6:
                    continue # skip malformed lines
                round.append([row[2], row[3], row[4], row[5]]) # PlayerA, PlayerB, TouchdownA, TouchdownB
            else:
                if len(row) < 4:
                    continue # skip malformed lines
                round.append([row[0], row[1], row[2], row[3]])
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
            writer.writerow(['TeamA', 'TeamB', 'PlayerA', 'PlayerB', 'TouchdownA', 'TouchdownB'])
            for game in pairing:
                pA, pB = game[0], game[1]
                teamA = players_dict.get(pA, {}).get('Team', '') if pA != 'BYE' else 'BYE'
                teamB = players_dict.get(pB, {}).get('Team', '') if pB != 'BYE' else 'BYE'
                writer.writerow([teamA, teamB, pA, pB, '', ''])
        else:
            writer.writerow(['PlayerA', 'PlayerB', 'TouchdownA', 'TouchdownB'])
            for game in pairing:
                writer.writerow([game[0], game[1], '', ''])
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