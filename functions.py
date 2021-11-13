##Return individual game dataframe from gameurl
def get_game(gameurl):
    import requests
    import pandas as pd
    import json
    import time
    from random import randint
    import itertools
    import numpy as np
    from collections import Counter
    import operator
    from bs4 import BeautifulSoup
    import dataframe_image as dfi
    from datetime import datetime

    ## Building JSON link
    # Send a request to game url
    resp = requests.get(gameurl)
    # Getting HTML content
    soup = BeautifulSoup(resp.content, features="html.parser")
    # Extracting key
    key = soup.main.div['data-feed_key']
    # Extracting league
    league = soup.main.div['data-league']
    # Extracting path
    path = soup.main.div['data-path']
    # Extracting lang
    lang = soup.main.div['data-lang']
    # Formulating JSON url
    jsonurl = "https://cluster.leaguestat.com/feed/index.php?feed=gc&key=" + key + "&client_code=" + league + "&game_id=" + path + "&lang_code=" + lang + "&fmt=json&tab=gamesummary"

    # Send a request to this URL to pull data
    response = requests.get(jsonurl)
    # System sleep between attempts
    time.sleep(randint(4, 5))
    # Pull JSON data from URL
    game_data = response.json()
    # Get home and away lineups
    home_data = game_data['GC']['Gamesummary']['home_team_lineup']['players']
    away_data = game_data['GC']['Gamesummary']['visitor_team_lineup']['players']
    # Convert JSON to a pandas dataframe
    home_lineup = pd.DataFrame(home_data)
    away_lineup = pd.DataFrame(away_data)
    # Get date
    date = game_data['GC']['Gamesummary']['meta']['date_played']
    # Get team names and abbreviations
    home_team = game_data['GC']['Gamesummary']['home']['name'].replace(",", "")
    home_code = game_data['GC']['Gamesummary']['home']['team_code'].upper()
    home_score = game_data['GC']['Gamesummary']['meta']['home_goal_count']
    away_team = game_data['GC']['Gamesummary']['visitor']['name'].replace(",", "")
    away_code = game_data['GC']['Gamesummary']['visitor']['team_code'].upper()
    away_score = game_data['GC']['Gamesummary']['meta']['visiting_goal_count']

    # Get game id and date
    date = game_data['GC']['Gamesummary']['meta']['date_played']
    gameid = game_data['GC']['Gamesummary']['meta']['id']

    # Adding home/away, team code, game id, game date, opponent team, and home/away goal count columns to dataframes
    full_lnuph = pd.DataFrame(data={'H_A': ['H'], 'team': [home_code], 'opp_team': [away_code], 'league': [league],
                                    'date': date,
                                    'gameid': [game_data['GC']['Gamesummary']['meta']['id']],
                                    'team_gf': [game_data['GC']['Gamesummary']['meta']['home_goal_count']], 'team_ga': [game_data['GC']['Gamesummary']['meta']['visiting_goal_count']]})
    final_lineup_home = home_lineup.assign(**full_lnuph.iloc[0])
    full_lnupa = pd.DataFrame(data={'H_A': ['A'], 'team': [away_code], 'opp_team': [home_code], 'league': [league],
                                    'date': date,
                                    'gameid': [game_data['GC']['Gamesummary']['meta']['id']],
                                    'team_gf': [game_data['GC']['Gamesummary']['meta']['visiting_goal_count']], 'team_ga': [game_data['GC']['Gamesummary']['meta']['home_goal_count']]})
    final_lineup_away = away_lineup.assign(**full_lnupa.iloc[0])

    # Identifying df columns to keep
    col_list = ['gameid', 'date', 'player_id', 'first_name', 'last_name', 'position_str', 'goals', 'assists',
                'plusminus',
                'pim', 'faceoff_wins', 'faceoff_attempts', 'shots', 'shots_on', 'team',
                'opp_team', 'league', 'H_A', 'team_gf', 'team_ga']
    # Combining home and away dataframes
    finallineup = final_lineup_home.append(final_lineup_away)
    # Selecting df columns to keep
    finallineup = finallineup[col_list]

    # Pulling goal data from JSON file
    goals_list = game_data['GC']['Gamesummary']['goals']
    # Creating a dataframe of goal data
    goalsdf = pd.DataFrame(goals_list)
    # Creating a list that specifies what game state each goal was at
    goal_state = []
    for i in range(len(goalsdf)):
        #Checking whether the goal was scored at even-strength
        if (goalsdf.power_play[i] == '0' and goalsdf.empty_net[i] == '0' and goalsdf.short_handed[i] == '0' and goalsdf.penalty_shot[i] == '0'):
            goal_state.append('EV')
        elif (goalsdf.power_play[i] == '1'):
            goal_state.append('PP')
        elif (goalsdf.short_handed[i] == '1'):
            goal_state.append('SH')
        elif (goalsdf.empty_net[i] == '1'):
            goal_state.append('EN')
        else:
            goal_state.append('OTHER')
    ###HANDLING GOAL SCORERS
    # Getting scorer_ids and goal counts
    scorer_ids = [d.get('player_id') for d in goalsdf.goal_scorer]
    # Creating a dictionary of scorer ids and game state
    scorer_df = pd.DataFrame({'scorer_ids': scorer_ids, 'game_state': goal_state})
    # Initializing a goal count column in lineup df
    finallineup = finallineup.assign(ev_goal_count = 0)
    finallineup = finallineup.assign(pp_goal_count = 0)
    finallineup = finallineup.assign(sh_goal_count = 0)
    finallineup = finallineup.assign(en_goal_count = 0)
    finallineup = finallineup.assign(other_goal_count = 0)
    # Adding 1 to the respective player's even strength goal count for each EV goal
    ev_goalsdf = scorer_df[scorer_df['game_state'] == 'EV'].reset_index()
    for i in range(len(ev_goalsdf)):
        goalid_temp = ev_goalsdf['scorer_ids'][i]
        finallineup.loc[finallineup['player_id'] == goalid_temp, 'ev_goal_count'] = finallineup.loc[finallineup['player_id'] == goalid_temp, 'ev_goal_count'] + 1
    # Adding 1 to the respective player's powerplay goal count for each PP goal
    pp_goalsdf = scorer_df[scorer_df['game_state'] == 'PP'].reset_index()
    for i in range(len(pp_goalsdf)):
        goalid_temp = pp_goalsdf['scorer_ids'][i]
        finallineup.loc[finallineup['player_id'] == goalid_temp, 'pp_goal_count'] = finallineup.loc[finallineup['player_id'] == goalid_temp, 'pp_goal_count'] + 1
    # Adding 1 to the respective player's shorthanded goal count for each SH goal
    sh_goalsdf = scorer_df[scorer_df['game_state'] == 'SH'].reset_index()
    for i in range(len(sh_goalsdf)):
        goalid_temp = sh_goalsdf['scorer_ids'][i]
        finallineup.loc[finallineup['player_id'] == goalid_temp, 'sh_goal_count'] = finallineup.loc[finallineup['player_id'] == goalid_temp, 'sh_goal_count'] + 1
    # Adding 1 to the respective player's empty net goal count for each EN goal
    en_goalsdf = scorer_df[scorer_df['game_state'] == 'EN'].reset_index()
    for i in range(len(en_goalsdf)):
        goalid_temp = en_goalsdf['scorer_ids'][i]
        finallineup.loc[finallineup['player_id'] == goalid_temp, 'en_goal_count'] = finallineup.loc[finallineup['player_id'] == goalid_temp, 'en_goal_count'] + 1
    # Adding 1 to the respective player's other goal count for each OTHER goal
    other_goalsdf = scorer_df[scorer_df['game_state'] == 'OTHER'].reset_index()
    for i in range(len(other_goalsdf)):
        goalid_temp = other_goalsdf['scorer_ids'][i]
        finallineup.loc[finallineup['player_id'] == goalid_temp, 'other_goal_count'] = finallineup.loc[finallineup['player_id'] == goalid_temp, 'other_goal_count'] + 1
    ### HANDLING FIRST ASSISTERS
    # Getting firstassister_ids and goal counts
    firstassister_ids = [d.get('player_id') for d in goalsdf.assist1_player]
    # Creating a dictionary of first assist ids and game state
    firstassister_df = pd.DataFrame({'firstassister_ids': firstassister_ids, 'game_state': goal_state})
    # Initializing first assist count columns in lineup df
    finallineup = finallineup.assign(ev_firstassist_count = 0)
    finallineup = finallineup.assign(pp_firstassist_count = 0)
    finallineup = finallineup.assign(sh_firstassist_count = 0)
    finallineup = finallineup.assign(en_firstassist_count = 0)
    finallineup = finallineup.assign(other_firstassist_count = 0)
    # Adding 1 to the respective player's even strength first assist count for each EV first assist
    ev_firstassistsdf = firstassister_df[firstassister_df['game_state'] == 'EV'].reset_index()
    for i in range(len(ev_firstassistsdf)):
        firstassistid_temp = ev_firstassistsdf['firstassister_ids'][i]
        finallineup.loc[finallineup['player_id'] == firstassistid_temp, 'ev_firstassist_count'] = finallineup.loc[finallineup['player_id'] == firstassistid_temp, 'ev_firstassist_count'] + 1
    # Adding 1 to the respective player's powerplay first assist count for each PP first assist
    pp_firstassistsdf = firstassister_df[firstassister_df['game_state'] == 'PP'].reset_index()
    for i in range(len(pp_firstassistsdf)):
        firstassistid_temp = pp_firstassistsdf['firstassister_ids'][i]
        finallineup.loc[finallineup['player_id'] == firstassistid_temp, 'pp_firstassist_count'] = finallineup.loc[finallineup['player_id'] == firstassistid_temp, 'pp_firstassist_count'] + 1
    # Adding 1 to the respective player's shorthanded first assist count for each SH first assist
    sh_firstassistsdf = firstassister_df[firstassister_df['game_state'] == 'SH'].reset_index()
    for i in range(len(sh_firstassistsdf)):
        firstassistid_temp = sh_firstassistsdf['firstassister_ids'][i]
        finallineup.loc[finallineup['player_id'] == firstassistid_temp, 'sh_firstassist_count'] = finallineup.loc[finallineup['player_id'] == firstassistid_temp, 'sh_firstassist_count'] + 1
    # Adding 1 to the respective player's empty net first assist count for each EN first assist
    en_firstassistsdf = firstassister_df[firstassister_df['game_state'] == 'EN'].reset_index()
    for i in range(len(en_firstassistsdf)):
        firstassistid_temp = en_firstassistsdf['firstassister_ids'][i]
        finallineup.loc[finallineup['player_id'] == firstassistid_temp, 'en_firstassist_count'] = finallineup.loc[finallineup['player_id'] == firstassistid_temp, 'en_firstassist_count'] + 1
    # Adding 1 to the respective player's other first assist count for each OTHER first assist
    other_firstassistsdf = firstassister_df[firstassister_df['game_state'] == 'OTHER'].reset_index()
    for i in range(len(other_firstassistsdf)):
        firstassistid_temp = other_firstassistsdf['firstassister_ids'][i]
        finallineup.loc[finallineup['player_id'] == firstassistid_temp, 'other_firstassist_count'] = finallineup.loc[finallineup['player_id'] == firstassistid_temp, 'other_firstassist_count'] + 1
    ### HANDLING SECOND ASSISTERS
    # Getting secondassist_ids and goal counts
    secondassister_ids = [d.get('player_id') for d in goalsdf.assist2_player]
    # Creating a dictionary of second assist ids and game state
    secondassister_df = pd.DataFrame({'secondassister_ids': secondassister_ids, 'game_state': goal_state})
    # Initializing second assist count columns in lineup df
    finallineup = finallineup.assign(ev_secondassist_count = 0)
    finallineup = finallineup.assign(pp_secondassist_count = 0)
    finallineup = finallineup.assign(sh_secondassist_count = 0)
    finallineup = finallineup.assign(en_secondassist_count = 0)
    finallineup = finallineup.assign(other_secondassist_count = 0)
    # Adding 1 to the respective player's even strength second assist count for each EV second assist
    ev_secondassistsdf = secondassister_df[secondassister_df['game_state'] == 'EV'].reset_index()
    for i in range(len(ev_secondassistsdf)):
        secondassistid_temp = ev_secondassistsdf['secondassister_ids'][i]
        finallineup.loc[finallineup['player_id'] == secondassistid_temp, 'ev_secondassist_count'] = finallineup.loc[finallineup['player_id'] == secondassistid_temp, 'ev_secondassist_count'] + 1
    # Adding 1 to the respective player's powerplay second assist count for each PP second assist
    pp_secondassistsdf = secondassister_df[secondassister_df['game_state'] == 'PP'].reset_index()
    for i in range(len(pp_secondassistsdf)):
        secondassistid_temp = pp_secondassistsdf['secondassister_ids'][i]
        finallineup.loc[finallineup['player_id'] == secondassistid_temp, 'pp_secondassist_count'] = finallineup.loc[finallineup['player_id'] == secondassistid_temp, 'pp_secondassist_count'] + 1
    # Adding 1 to the respective player's shorthanded second assist count for each SH second assist
    sh_secondassistsdf = secondassister_df[secondassister_df['game_state'] == 'SH'].reset_index()
    for i in range(len(sh_secondassistsdf)):
        secondassistid_temp = sh_secondassistsdf['secondassister_ids'][i]
        finallineup.loc[finallineup['player_id'] == secondassistid_temp, 'sh_secondassist_count'] = finallineup.loc[finallineup['player_id'] == secondassistid_temp, 'sh_secondassist_count'] + 1
    # Adding 1 to the respective player's empty net second assist count for each EN second assist
    en_secondassistsdf = secondassister_df[secondassister_df['game_state'] == 'EN'].reset_index()
    for i in range(len(en_secondassistsdf)):
        secondassistid_temp = en_secondassistsdf['secondassister_ids'][i]
        finallineup.loc[finallineup['player_id'] == secondassistid_temp, 'en_secondassist_count'] = finallineup.loc[finallineup['player_id'] == secondassistid_temp, 'en_secondassist_count'] + 1
    # Adding 1 to the respective player's other second assist count for each OTHER second assist
    other_secondassistsdf = secondassister_df[secondassister_df['game_state'] == 'OTHER'].reset_index()
    for i in range(len(other_secondassistsdf)):
        secondassistid_temp = other_secondassistsdf['secondassister_ids'][i]
        finallineup.loc[finallineup['player_id'] == secondassistid_temp, 'other_secondassist_count'] = finallineup.loc[finallineup['player_id'] == secondassistid_temp, 'other_secondassist_count'] + 1
    ###HANDLING PLUS/MINUS AND PENALTIES
    # Creating a list that specifies whether a goal counts towards plus/minus or not
    fvf_temp = []
    for i in range(len(goalsdf)):
        if (goalsdf.power_play[i] == '0' and goalsdf.empty_net[i] == '0' and goalsdf.short_handed[i] == '0' and
                goalsdf.penalty_shot[i] == '0'):
            fvf_temp.append(i)
    # Getting pluses and creating a counter dataframe with ids and plus counts
    plus_temp = []
    for i in fvf_temp:
        plus_temp.append([d.get('player_id') for d in game_data['GC']['Gamesummary']['goals'][i]['plus']])
    plus_ids = Counter(list(itertools.chain(*plus_temp)))
    plusdf = pd.DataFrame.from_dict(plus_ids, orient='index', columns=['gf_count']).reset_index()
    # Getting minuses and creating a counter dataframe with ids and minus counts
    minus_temp = []
    for i in fvf_temp:
        minus_temp.append([d.get('player_id') for d in game_data['GC']['Gamesummary']['goals'][i]['minus']])
    minus_ids = Counter(list(itertools.chain(*minus_temp)))
    minusdf = pd.DataFrame.from_dict(minus_ids, orient='index', columns=['ga_count']).reset_index()
    # Getting penalties taken and creating a counter dataframe with ids and penalty taken counts
    pen_temp = []
    for i in range(len(game_data['GC']['Gamesummary']['penalties'])):
        pen_temp.append(game_data['GC']['Gamesummary']['penalties'][i]['player_penalized_info'].get('player_id', None))
    pen_ids = Counter(pen_temp)
    pendf = pd.DataFrame.from_dict(pen_ids, orient='index', columns=['pen_count']).reset_index()
    # Merging in plus, minus, and penalty counts
    finallineup = pd.merge(finallineup, plusdf, how='left', left_on='player_id', right_on='index')
    finallineup = pd.merge(finallineup, minusdf, how='left', left_on='player_id', right_on='index')
    finallineup = pd.merge(finallineup, pendf, how='left', left_on='player_id', right_on='index')
    # Replacing Nan with 0
    finallineup = finallineup.fillna(0)
    # Converting non-int columns to integer
    finallineup['gf_count'] = finallineup['gf_count'].astype(int)
    finallineup['ga_count'] = finallineup['ga_count'].astype(int)
    finallineup['pen_count'] = finallineup['pen_count'].astype(int)
    finallineup['faceoff_wins'] = finallineup['faceoff_wins'].astype(int)
    finallineup['faceoff_attempts'] = finallineup['faceoff_attempts'].astype(int)
    finallineup['shots_on'] = finallineup['shots_on'].astype(int)
    # Adding faceoff losses column and full name column
    finallineup = finallineup.assign(faceoff_losses=finallineup.faceoff_attempts - finallineup.faceoff_wins)
    finallineup = finallineup.assign(name=finallineup.first_name + " " + finallineup.last_name)
    # Selecting relevant columns
    return finallineup[['gameid', 'date', 'league', 'opp_team', 'name', 'team', 'H_A', 'team_gf',
                        'team_ga', 'ev_goal_count', 'pp_goal_count', 'sh_goal_count', 'en_goal_count',
                        'other_goal_count', 'ev_firstassist_count', 'pp_firstassist_count', 'sh_firstassist_count',
                        'en_firstassist_count', 'other_firstassist_count', 'ev_secondassist_count',
                        'pp_secondassist_count', 'sh_secondassist_count', 'en_secondassist_count',
                        'other_secondassist_count', 'shots', 'shots_on', 'gf_count', 'ga_count',
                        'pen_count', 'faceoff_wins', 'faceoff_losses', 'pim']]

##Get daily gameurls for specified date
def get_daily_urls(date):
    import requests
    #Setting league keys
    ohl_key = "2976319eb44abe94"
    whl_key = "41b145a848f4bd67"
    lhjmq_key = "f322673b6bcae299"
    #Getting OHL games
    ohl_jsonurl = "https://lscluster.hockeytech.com/feed/?feed=modulekit&view=gamesbydate&key=" + ohl_key + "&fmt=json&client_code=ohl" + "&lang=en&league_code=&fetch_date=" + date + "&fmt=json"
    ohl_resp = requests.get(ohl_jsonurl)
    ohl_json = ohl_resp.json()
    ohl_game_urls = []
    for i in range(len(ohl_json['SiteKit']['Gamesbydate'])):
        ohl_game_urls.append("https://ontariohockeyleague.com/gamecentre/" + ohl_json['SiteKit']['Gamesbydate'][i]['id'])
    #Getting WHL games
    whl_jsonurl = "https://lscluster.hockeytech.com/feed/?feed=modulekit&view=gamesbydate&key=" + whl_key + "&fmt=json&client_code=whl" + "&lang=en&league_code=&fetch_date=" + date + "&fmt=json"
    whl_resp = requests.get(whl_jsonurl)
    whl_json = whl_resp.json()
    whl_game_urls = []
    for i in range(len(whl_json['SiteKit']['Gamesbydate'])):
        whl_game_urls.append("https://whl.ca/gamecentre/" + whl_json['SiteKit']['Gamesbydate'][i]['id'])
    #Getting QMJHL games
    qmjhl_jsonurl = "https://lscluster.hockeytech.com/feed/?feed=modulekit&view=gamesbydate&key=" + lhjmq_key + "&fmt=json&client_code=lhjmq" + "&lang=en&league_code=&fetch_date=" + date + "&fmt=json"
    qmjhl_resp = requests.get(qmjhl_jsonurl)
    qmjhl_json = qmjhl_resp.json()
    qmjhl_game_urls = []
    for i in range(len(qmjhl_json['SiteKit']['Gamesbydate'])):
        qmjhl_game_urls.append("https://theqmjhl.ca/gamecentre/" + qmjhl_json['SiteKit']['Gamesbydate'][i]['id'])
    return ohl_game_urls + whl_game_urls + qmjhl_game_urls

def get_range_urls(startdate, enddate):
    import pandas as pd
    import more_itertools as mit
    from datetime import datetime
    dates = pd.date_range(start=startdate, end=enddate).to_list()
    urls = []
    for i in dates:
        temp = get_daily_urls(i.strftime("%Y-%m-%d"))
        urls.append(temp)
    return list(mit.flatten(urls))

def get_games_list(urls):
    gamesdf_list = []
    for i in urls:
        gamesdf_list.append(get_game(i))
    return gamesdf_list

def get_games_df(urls):
    import pandas as pd
    from tqdm import tqdm
    gamesdf_list = []
    for i in tqdm(urls):
        try:
            temp = get_game(i)
        except:
            temp = None
            print("Error. Skipping game")
        gamesdf_list.append(temp)
    return pd.concat(gamesdf_list)

###Loading in old data, appending new data, then saving over old data
from datetime import datetime
import pandas as pd
dateinfo = datetime.now()
date = dateinfo.strftime("%Y") + "-" + dateinfo.strftime("%m") + "-" + str((int(dateinfo.strftime("%d"))-1))
print(date)
old_data = pd.read_csv(filepath_or_buffer="gamedata.csv")
new_data = get_games_df(get_range_urls(date,date)).reset_index(drop=True)
full_data = pd.concat([old_data, new_data])
full_data.to_csv(path_or_buf="gamedata.csv", index=False)
