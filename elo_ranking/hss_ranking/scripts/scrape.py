import BeautifulSoup
import requests
import time
import re
import arrow
import urllib
from skills.elo import EloCalculator, EloGameInfo, EloRating
from skills import Match

from hss_ranking.models import Game, Team, Conference

import pandas as pd

K_VAL = 25
SLEEP_TIME = .25

def get_site_id(name, field="id"):
    url = "http://highschoolsports.mlive.com/find_school/?q={}".format(name.lower())
    r = requests.get(url)
    urls = r.json()
    for url in urls:
        if url.get("name").lower() == name.lower():
            return url.get(field)     

def get_conference(team, sport="boysbasketball"):
    school_url = get_site_id(team.name, field="url")
    url = "http://highschoolsports.mlive.com{}{}/".format(school_url,sport)
    req = requests.get(url)
    name = None
    page = BeautifulSoup.BeautifulSoup(req.text)
    if page:
        table = page.find('div', {'class': 'stats-table'})
        if table:
            conference = page.find('caption')
            name = conference.text
    if not name:
       name = "placeholder"

    conf,created = Conference.objects.get_or_create(name=name)
    return conf

def get_team(name):
    team,exists = Team.objects.get_or_create(name=name)
    if not team.site_id:
        site_id = get_site_id(team.name)
        if site_id:
            team.site_id = site_id
        else:
            print "Could not get id for {}".format(team.name)

    if not team.conference:
        team.conference = get_conference(team)

    team.save()
    return team

def add_game(home_name, away_name, score_home, score_away, date):

    #To avoid duplicates always sort by name to ensure that we don't get
    #duplicate games

    #Lookup the teams and create them if they don't exist
    home = get_team(home_name)
    away = get_team(away_name)
    game,exists = Game.objects.get_or_create(
      home=home, 
      away=away, 
      score_home=score_home, 
      score_away=score_away,
      date=date.datetime
    )
    if not exists:
        game.save()
        print "New game"

def extract_date(buf):
    tm = arrow.utcnow()
    for i in range(10):
        year = tm.format('YYYY')
        date = arrow.get("{}/{}".format(year, buf), "YYYY/MM/DD")
        if date < arrow.utcnow():
            return date
        else:
            tm = tm.replace(years=-1)

def get_pages(text):
    page_rgx = "Page [0-9]+ of ([0-9]+)"
    m = re.search(page_rgx, text)
    if m:
        return int(m.group(1)) + 1
    return 0

def get_teams(string):
    teams = string.split('\t')
    if len(teams) != 2:
        return

    for team in teams:
        if '@' in team:
            away = team.replace('@', '')
        else:
            home = team
    return home,away

def parse_games(df, team):
    for index,row in df.iterrows():
        parse_game(row, team)

def simulate_games(games):
    calculator = EloCalculator()
    for game in games:
        simulate_game(calculator, game)

def parse_game(row, team):

    home_first = True
    try:
        home, away = get_teams(row['TEAMS'])
    except KeyError:
        if '@' in row['OPPONENT']:
            home_first = False
            home = row['OPPONENT'].replace('@', '')
            away = team.name
        else:
            away = row['OPPONENT'].replace('@', '')
            home = team.name
    except (TypeError, ValueError) as e:
        print "Couldn't unpack {}".format(row['TEAMS'])
        return

    #Sigh, game results can come in many interesting flavors
    for k in ['SCORE', 'RESULT']:
        try:
            pat = "([0-9]+)-([0-9]+)"
            m = re.search(pat, row[k])
            if m: 
                score1 = m.group(1)
                score2 = m.group(2)
            else:
                score1, score2 = row[k].split('\t')
        except KeyError:
            pass
        except ValueError:
            print "Couldn't unpack score {}".format(row[k])
            return

    if home_first:
        home_score = score1
        away_score = score2
    else:
        away_score = score1
        home_score = score2

    #Game not recorded
    if '--' in score1 or '--' in score2:
        print "No scores"
        return

    try:
        date_str = row['DATE']
        date = extract_date(date_str)
    except ValueError:
        print "Could not parse {}".format(row['DATE'])
        return

    add_game(home, away, home_score, away_score, date)

def simulate_game(calculator, game):

    if game.simulated:
        return

    home = game.home
    away = game.away

    if game.score_home > game.score_away:
        rank = [1, 2]
        home.wins += 1
        away.loses += 1
    else:
        rank = [2, 1]
        home.loses += 1
        away.wins += 1

    game_info = EloGameInfo(1200, 25)
    team_info = Match(
      [ 
        {1: (home.elo, home.k_val)},
        {2: (away.elo, away.k_val)}
      ],
      rank)

    new_ratings = calculator.new_ratings(team_info, game_info)
    home.elo = new_ratings.rating_by_id(1).mean
    away.elo = new_ratings.rating_by_id(2).mean
    home.k_val = new_ratings.rating_by_id(1).k_factor
    away.k_val = new_ratings.rating_by_id(2).k_factor
    print "simulated {} vs {} [{} - {}]".format(home.name, away.name, game.score_home, game.score_away)   
    game.simulated=True
    home.save()
    away.save()
    game.save()

def get_page_count():
    url = "http://highschoolsports.mlive.com/sprockets/game_search_results/?config=3853&season=2327&sport=200&page={}".format(1)
    req = requests.get(url)
    page = BeautifulSoup.BeautifulSoup(req.text)
    pages = page.find('span', {'class': 'page-of'})
    num_pages = get_pages(pages.text)
    return num_pages

def parse_score_table(text, team):
    headings = None
    data_rows = []
    page = BeautifulSoup.BeautifulSoup(text)
    table = page.find("div", {"class": "stats-table scores"})
    if table:
         for row in table.findAll('tr'):
             if row.find('th'):
                 if not headings:
                     headings = []
                     cols = row.findAll('th')
                     for col in cols:
                         headings.append(col.text)
             else:
                 cols = row.findAll('td')
                 content = []
                 for col in cols:
                     divs = col.findAll('div')
                     if not divs:
                         #Some rows are just text
                         text = col.text
                     else:
                         text = "\t".join([div.text for div in divs])
                     content.append(text)
                 data_rows.append(tuple(content))
    print "Got {} rows".format(len(data_rows))
    games_df = pd.DataFrame(data_rows, columns=headings)
    parse_games(games_df, team) 
    

def fetch_teams(teams):
    for team in teams:
        get_team(team.name)
        if not team.site_id:
            continue
        base_url = "http://highschoolsports.mlive.com/boysbasketball/schedule/"
        params="game_search_start=&game_search_end=&game_search_school_search={}&game_search_grouping=&game_search_school_search_id_holder={}"
        name = team.name.replace(' ', '+')
        name = urllib.quote_plus(name)
        params = params.format(name,team.site_id)
        url = "{}?{}".format(base_url, params)
        #Uses + for space
        req = requests.get(url)
        time.sleep(SLEEP_TIME)
        print "Updating {}".format(team.name)
        parse_score_table(req.text, team)

def fetch_season(max_pages=None):
    num_pages = get_page_count()
    num_pages = 2
    for page_num in range(1,num_pages):
        if max_pages and page_num > max_pages:
            break
        print "Fetching page {}".format(page_num)
        url = "http://highschoolsports.mlive.com/sprockets/game_search_results/?config=3853&season=2327&sport=200&page={}".format(page_num)
        req = requests.get(url)
        parse_score_table(req.text, None)
        time.sleep(SLEEP_TIME)
