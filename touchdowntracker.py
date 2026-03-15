# touchdowntracker.py

import os
import random
import csv
import logging as log
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from globals import *
from utils import *

def get_previous_pairings(rounds_dir: str = 'rounds', a_col: str = 'PlayerA', b_col: str = 'PlayerB') -> List[List[str]]:
    """
    Return a list of previous pairings by scanning round CSVs.
    Each element is a pair [A, B].
    """
    prev = []
    # Use pathlib for better path handling and efficiency
    rounds_path = Path(rounds_dir)
    if not rounds_path.exists():
        return prev
    # Find all round files and sort by round number
    round_files = sorted(
        rounds_path.glob('round*.csv'),
        key=lambda p: int(p.stem.replace('round', ''))
    )
    for round_file in round_files:
        try:
            r = loadRound(str(round_file))
        except FileNotFoundError:
            continue
        if not r:
            continue
        header = r[0]
        if a_col not in header or b_col not in header:
            continue
        a_idx = header.index(a_col)
        b_idx = header.index(b_col)
        for row in r[1:]:
            prev.append([row[a_idx], row[b_idx]])
    return prev

def generatePairing(round_number: int, players_dict: Dict[str, Dict[str, Any]], stats_dict: Dict[str, Dict[str, Any]], team_stats: Optional[Dict[str, Dict[str, Any]]] = None) -> List[List[str]]:
    """
    Generate Swiss pairings for the given round.
    Supports both team-based and individual pairings, avoiding repeat matchups.
    """
    team_size = int(config.get('team_size', 1))

    if team_size > 1:
        log.debug('Team Swiss pairing mode')

        # Get list of unique teams
        if team_stats:
            teams = list(team_stats.keys())
        else:
            teams = list({p.get('Team') for p in players_dict.values() if p.get('Team') is not None})
        
        # Find previous team matchups
        prev_team_games = get_previous_pairings('rounds', 'TeamA', 'TeamB')

        log.debug(f'Found {len(prev_team_games)} previous team games')
        log.debug('')

        team_pairings = dfs_team_recursive(teams, prev_team_games)

        # For each team pairing, match individual players by rank
        player_pairings = []
        for t1, t2 in team_pairings:
            log.debug(f'Pairing teams: {t1} vs {t2}')
            if t1 == 'BYE':
                team1_sorted = ['BYE' for _ in range(team_size)]
                team2_players = [p for p in players_dict if players_dict[p].get('Team') == t2]
                team2_sorted = sorted(team2_players, key=lambda p: stats_dict.get(p, {}).get('rank', 9999))
            elif t2 == 'BYE':
                team2_sorted = ['BYE' for _ in range(team_size)]
                team1_players = [p for p in players_dict if players_dict[p].get('Team') == t1]
                team1_sorted = sorted(team1_players, key=lambda p: stats_dict.get(p, {}).get('rank', 9999)) 
            else:
                team1_players = [p for p in players_dict if players_dict[p].get('Team') == t1]
                team1_sorted = sorted(team1_players, key=lambda p: stats_dict.get(p, {}).get('rank', 9999))
                team2_players = [p for p in players_dict if players_dict[p].get('Team') == t2]
                team2_sorted = sorted(team2_players, key=lambda p: stats_dict.get(p, {}).get('rank', 9999))
            for p1, p2 in zip(team1_sorted, team2_sorted):
                log.debug(f'\tPairing players: {p1} vs {p2}')
                player_pairings.append([p1, p2])
            # If teams have unequal number of players, ignore extra players (no BYE)
        return player_pairings
    else:
        log.debug('Individual Swiss pairing mode')
        if (round_number==1): # first round
            log.debug('First round pairing')
            if stats_dict:
                log.debug('Sorting players by rank')
                sorted_players = sorted(players_dict.keys(), key=lambda p: stats_dict.get(p, {}).get('rank', 9999))
            else:
                log.debug('No stats, shuffling players randomly')
                sorted_players = list(players_dict.keys())
                random.shuffle(sorted_players)
            pairings = []
            log.debug('Remaining players: ' + ', '.join(sorted_players))
            for i in range(0, len(sorted_players)-1, 2):
                log.debug(f'Pairing: {sorted_players[i]} vs {sorted_players[i+1]}')
                pairings.append([sorted_players[i], sorted_players[i+1]])
            if len(sorted_players) % 2 == 1:
                log.debug(f'Assigning BYE to: {sorted_players[-1]}')
                pairings.append([sorted_players[-1], 'BYE'])
            return pairings
        else:
            log.debug('Subsequent round pairing')
            prev_games = get_previous_pairings('rounds', 'PlayerA', 'PlayerB')
            pairings = dfs_recursive(players_dict, stats_dict, prev_games)
            return pairings

def dfs_recursive(players_dict: Dict[str, Dict[str, Any]], stats_dict: Dict[str, Dict[str, Any]], prev_games: List[List[str]], pairings: Optional[List[List[str]]] = None) -> Optional[List[List[str]]]:
    """
    Recursively generate valid player pairings using DFS, avoiding repeat matchups.
    Returns a list of pairings.
    """
    log.debug(f'dfs_recursive called')
    if pairings is None:
        pairings = []
    if len(pairings) * 2 >= len(players_dict):
        log.debug('All players paired, returning pairings')
        return pairings
    used = set()
    for p1, p2 in pairings:
        used.add(p1)
        used.add(p2)
    remaining = [p for p in players_dict if p not in used]
    log.debug(f'Remaining players: {remaining}')
    if len(remaining) == 1:
        log.debug(f'Only one player left: {remaining[0]}, assigning BYE')
        pairings.append([remaining[0], 'BYE'])
        return pairings
    elif not remaining:
        log.debug('No remaining players, returning pairings')
        return pairings
    # Sort remaining by rank (lowest first)
    sorted_remaining = sorted(remaining, key=lambda p: stats_dict.get(p, {}).get('rank', 9999))
    log.debug(f'Sorted remaining players by rank: {sorted_remaining}')
    p1 = sorted_remaining[0]
    for i in range(1, len(sorted_remaining)):
        p2 = sorted_remaining[i]
        log.debug(f'Trying to pair {p1} with {p2}')
        if [p1, p2] not in prev_games and [p2, p1] not in prev_games:
            log.debug(f'Pair {p1}-{p2} not in previous games, recursing')
            result = dfs_recursive(players_dict, stats_dict, prev_games, pairings + [[p1, p2]])
            if result:
                log.debug(f'Recursion successful for pair {p1}-{p2}')
                return result
            else:
                log.debug(f'Recursion failed for pair {p1}-{p2}')
    log.debug('No valid pairings found, returning empty list')
    return []

def dfs_team_recursive(sorted_teams: List[str], prev_games: List[List[str]], pairings: Optional[List[List[str]]] = None) -> Optional[List[List[str]]]:
    """
    Recursively generate valid team pairings using DFS, avoiding repeat matchups.
    """
    if pairings is None:
        pairings = []
    log.debug(f'dfs_team_recursive called with pairings: {pairings}')
    if len(pairings) * 2 >= len(sorted_teams):
        log.debug('All teams paired, returning pairings')
        return pairings
    used = set()
    for t1, t2 in pairings:
        used.add(t1)
        used.add(t2)
    remaining = [t for t in sorted_teams if t not in used]
    log.debug(f'\tRemaining teams: {remaining}')
    if len(remaining) == 1:
        log.debug(f'Only one team left: {remaining[0]}, assigning BYE')
        pairings.append([remaining[0], 'BYE'])
        return pairings
    elif not remaining:
        log.debug('No remaining teams, returning pairings')
        return pairings
    t1 = remaining[0]
    for i in range(1, len(remaining)):
        t2 = remaining[i]
        log.debug(f'\t\tTrying to pair {t1} with {t2}')
        if [t1, t2] not in prev_games and [t2, t1] not in prev_games:
            log.debug(f'\tPair {t1}-{t2} not in previous games, recursing')
            log.debug('')
            result = dfs_team_recursive(sorted_teams, prev_games, pairings + [[t1, t2]])
            if result:
                log.debug(f'\tRecursion successful for pair {t1}-{t2}')
                return result
            else:
                log.debug(f'\tRecursion failed for pair {t1}-{t2}')
    log.debug(f'No valid pairings found for {t1}, assigning BYE')
    pairings.append([t1, 'BYE'])
    return pairings

def updateStats(players: List[str], stats: Dict[str, Dict[str, Any]], last_round: List[List[str]]) -> Dict[str, Dict[str, Any]]:
    """
    Update player statistics based on the results of the last round.
    Returns a dictionary of updated stats, sorted and ranked.
    """
    for player in players:
        log.debug(f'Updating stats for player: {player}')
        stats.setdefault(player, {key: 0 for key in config['base_statistics'] + config['statistics'] + config['additional_statistics']})
        log.debug(f'....Current stats: {stats.get(player, {})}')  
        for idx, game in enumerate(last_round):
            if idx == 0:  # header row
                headers = game
                if 'PlayerA' not in headers or 'PlayerB' not in headers or 'TouchdownA' not in headers or 'TouchdownB' not in headers:
                    raise ValueError('Invalid round header for player stats')
                pA_index = headers.index('PlayerA')
                pB_index = headers.index('PlayerB')
                tdA_index = headers.index('TouchdownA')
                tdB_index = headers.index('TouchdownB')
            else:
                if (game[pA_index] == player) or (game[pB_index] == player):
                    # Update points, wins, draws and losses
                    pA, pB = game[pA_index], game[pB_index]
                    if (game[tdA_index] == '') or (game[tdB_index] == ''):
                        raise ValueError('Round still in progress - missing scores')
                    tdA, tdB = int(game[tdA_index]), int(game[tdB_index])
                    log.debug(f'....Game found for player {player}: {pA} vs {pB}, scores {tdA}-{tdB}')
                    if (pA == player and tdA > tdB) or (pB == player and tdB > tdA):
                        stats[player]["points"] += 4
                        stats[player]["wins"]   += 1
                    elif tdA == tdB:
                        stats[player]["points"] += 2
                        stats[player]["draws"]  += 1
                    else:
                        stats[player]["points"] += 0
                        stats[player]["losses"] += 1

                    # Update touchdowns scored/conceded (always first two columns after player names)
                    stats[player]["touchdown_scored"]   += tdA if pA == player else tdB
                    stats[player]["touchdown_conceded"] += tdB if pA == player else tdA
                    if "touchdown_diff" in config['statistics'] or "touchdown_diff" in config['additional_statistics']:
                        stats[player]["touchdown_diff"]     = stats[player]["touchdown_scored"] - stats[player]["touchdown_conceded"]

                    # Headers are taken from the first row of last_round
                    # variable 'headers' was set above when idx==0
                    
                    # Update stats based on header positions
                    for stat in config['statistics'] + config['additional_statistics']:
                        if stat not in config['base_statistics']: # Exclude mandatory stats
                            # Look for both statA and statB variations in headers
                            stat_a = f"{stat}A"
                            stat_b = f"{stat}B"
                            
                            if stat_a in headers and stat_b in headers:
                                idx_a = headers.index(stat_a)
                                idx_b = headers.index(stat_b)
                                # Add stat value based on whether player is A or B
                                if pA == player:
                                    stats[player][stat] += float(game[idx_a]) if game[idx_a] else 0
                                else:
                                    stats[player][stat] += float(game[idx_b]) if game[idx_b] else 0
                            else:
                                log.warning(f'Statistic {stat} not found in headers')
                    
                    log.debug(f'....Updated stats: {stats[player]}')
                    log.debug(f'')
    # Build sort key from indiv_tie_breakers
    from globals import _tie_break_to_stat
    sort_key_stats = []
    for tie_break in config.get('indiv_tie_breakers', []):
        if tie_break in _tie_break_to_stat:
            log.debug(f'Sorting by tie breaker: {tie_break}')
            sort_key_stats.append(_tie_break_to_stat[tie_break])
    
    # If no tie breakers defined, fall back to points and touchdown_scored
    if not sort_key_stats:
        sort_key_stats = ['points', 'touchdown_scored']
    
    # Sort by the dynamic tie breaker keys
    def sort_key(item):
        player_stats = item[1]
        return tuple(player_stats.get(stat, 0) for stat in sort_key_stats)
    
    ranked_stats = dict(sorted(stats.items(), key=sort_key, reverse=True))
    for rank, player in enumerate(ranked_stats, start=1):
        ranked_stats[player]["rank"] = rank
    return ranked_stats

def updateTeamStats(players_dict: Dict[str, Dict[str, Any]], stats_dict: Dict[str, Dict[str, Any]], team_stats: Dict[str, Dict[str, Any]], last_round: List[List[str]]) -> Dict[str, Dict[str, Any]]:
    """
    Aggregate player statistics into team statistics.
    Returns a dictionary of team stats, sorted by performance using team_tie_breakers.
    """
    for player, pdata in players_dict.items():
        team = pdata.get('Team', None)
        if not team:
            continue
        pstats = stats_dict.get(player, {})
        if team not in team_stats:
            team_stats[team] = {key: 0 for key in config['base_statistics'] + config['statistics'] + config['additional_statistics']}
        
        log.debug(f'Aggregating stats for player {player} into team {team}')
        log.debug(f'....Player stats: {pstats}')
        # Aggregate all stats from player to team
        for stat_key in team_stats[team]:
            if stat_key not in ['rank', 'points', 'wins', 'draws', 'losses']:  # rank will be assigned later, points, wins/draws/losses are not aggregated
                log.debug(f'........Adding {stat_key}: {pstats.get(stat_key, 0)} to team {team}')
                team_stats[team][stat_key] += pstats.get(stat_key, 0)
        
    for team in team_stats:
        log.debug(f'Computing W/D/L for team: {team}')
        team_wins = 0
        team_draws = 0
        team_losses = 0
        t1_index = t2_index = td1_index = td2_index = None
        for idx, game in enumerate(last_round):
            if idx == 0:  # header
                headers = game
                if 'TeamA' not in headers or 'TeamB' not in headers or 'TouchdownA' not in headers or 'TouchdownB' not in headers:
                    raise ValueError('Invalid round header for team stats')
                t1_index = headers.index('TeamA')
                t2_index = headers.index('TeamB')
                td1_index = headers.index('TouchdownA')
                td2_index = headers.index('TouchdownB')
            else:
                t1, t2 = game[t1_index], game[t2_index]
                if t1 == team or t2 == team:
                    score1, score2 = int(game[td1_index]), int(game[td2_index])
                    if (t1 == team and score1 > score2) or (t2 == team and score2 > score1):
                        team_wins   += 1
                    elif score1 == score2:
                        team_draws  += 1
                    else:
                        team_losses += 1
        log.debug(f'....Team {team} W/D/L: {team_wins}/{team_draws}/{team_losses}')
        team_wr = ((team_wins + team_draws*0.5) / (team_wins + team_draws + team_losses)) if (team_wins + team_draws + team_losses) > 0 else 0
        log.debug(f'....Team {team} Win Rate: {team_wr:.2f}')
        if team_wr > 0.5:
            team_stats[team]['points'] += 4
            team_stats[team]['wins'] += 1
            log.debug(f'....Team {team} awarded 4 points for win')
        elif team_wr == 0.5:
            team_stats[team]['points'] += 2
            team_stats[team]['draws'] += 1
            log.debug(f'....Team {team} awarded 2 points for draw')
        else:
            team_stats[team]['points'] += 0
            team_stats[team]['losses'] += 1
            log.debug(f'....Team {team} awarded 0 points for loss')

    
    # Build sort key from team_tie_breakers
    sort_key_stats = []
    for tie_break in config.get('team_tie_breakers', []):
        from globals import _tie_break_to_stat

        if tie_break in _tie_break_to_stat:
            log.debug(f'Sorting teams by tie breaker: {tie_break}')
            sort_key_stats.append(_tie_break_to_stat[tie_break])
    
    # If no tie breakers defined, fall back to points and touchdown_scored
    if not sort_key_stats:
        sort_key_stats = ['points', 'touchdown_scored']
    
    # Sort by the dynamic tie breaker keys
    def sort_key(item):
        team_stats_vals = item[1]
        return tuple(team_stats_vals.get(stat, 0) for stat in sort_key_stats)
    
    sorted_teams = dict(sorted(team_stats.items(), key=sort_key, reverse=True))
    for rank, team in enumerate(sorted_teams, start=1):
        sorted_teams[team]["rank"] = rank
    return sorted_teams

if __name__ == '__main__':
    # Setup logging infrastructure
    Path('log').mkdir(exist_ok=True)
    log_time = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_filename = f'log/log_{log_time}.log'

    # Configure logging with console and file handlers
    formatter = log.Formatter('%(levelname)s - %(message)s')
    log.basicConfig(format='%(levelname)s - %(message)s', level=args.loglevel.upper())

    # Add file handler for persistent logging
    file_handler = log.FileHandler(log_filename)
    file_handler.setFormatter(formatter)
    log.getLogger().addHandler(file_handler)

    log.info(f'Touchdown Tracker v{version}')
    log.debug(f'Config: {config}')

    # Seed random number generator for reproducible pairings
    random.seed(config['random_seed'])

    # Load player data from configuration file
    players_dict = loadPlayers(filepath=config['players_file'])

    # Determine current round number based on existing round files
    round_number = len([f for f in os.listdir('rounds/') if f.endswith('.csv')]) + 1
    log.info(f'Round number: {round_number}')
    team_stats = {}
    
    # Compute statistics from previous rounds if any exist
    if round_number > 1:
        log.info('Computing statistics...')
        # Clean up old statistics files
        if os.path.exists('stats/statistics.csv'):
            os.remove('stats/statistics.csv')
        if os.path.exists('stats/team_statistics.csv'):
            os.remove('stats/team_statistics.csv')

        # Aggregate stats from all previous rounds
        stats_dict = {}
        for round_idx in range(1, round_number):
            log.info(f'...from round {round_idx}')
            round_data = loadRound(f'rounds/round{round_idx}.csv')
            stats_dict = updateStats(players_dict, stats_dict, round_data)
            if config.get('team_size', 1) > 1:
                team_stats = updateTeamStats(players_dict, stats_dict, team_stats, round_data)
        
        # Persist updated statistics
        saveStats(stats_dict)
        if config.get('team_size', 1) > 1:
            saveTeamStats(team_stats)
    else:
        stats_dict = {}

    # Generate next round pairings unless in stats-only mode
    if not args.stats:
        log.info(f'Generating round {round_number}...')
        pairings = generatePairing(round_number, players_dict, stats_dict, team_stats)
        if pairings:
            savePairing(round_number, pairings, players_dict)
            savePairingHtml(round_number, pairings, players_dict)

