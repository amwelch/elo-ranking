from django.shortcuts import render
from django.http import HttpResponse
from django.template import RequestContext, loader

from hss_ranking.models import Team, Game, Conference
import scripts.scrape as scrape

# Create your views here.
def fetch_teams(request):
    teams = Team.objects.all()
    scrape.fetch_teams(teams)
    return HttpResponse("Done")

def fetch(request):
    print "Fetching"
    df = scrape.fetch_season(max_pages=0)
    return HttpResponse("Done")

def parse(request):
    print "Simulating"
    games = Game.objects.filter(simulated=False).order_by("date")
    scrape.simulate_games(games)
    return HttpResponse("Done")

def team_dash(request):
    template = loader.get_template('hss_ranking/team_dash.html')
    context = RequestContext(request, {
        'team_info': 'foo'
    })
    return HttpResponse(template.render(context))
def team_drill(request, team_id):
    template = loader.get_template('hss_ranking/team_drill.html')
    team = Team.objects.get(id=team_id)
    team_info = {}
    team_info['name'] = team.name
    data = []
    games = Game.objects.filter(home=team) 
    for game in games:
        data.append([game.home.name, game.away.name, game.score_home, game.score_away])
    games = Game.objects.filter(away=team)
    for game in games:
        data.append([game.home.name, game.away.name, game.score_home, game.score_away])
    context = RequestContext(request, {
        'team_schedule': data,
        'team_info': team_info
    })
    return HttpResponse(template.render(context))

def index(request):
    template = loader.get_template('hss_ranking/index.html')
    data = []
    rank = 1

    state = {
        "name": "Michigan",
        "id": 0
    }
    sport = {
        "name": "Men's Basketball",
        "id": 0
    }
    division = {
        "name": "1A",
        "id": 0
    }
    conference = {
        "name": "SEC",
        "id": 0
    }

    #Placeholder stats
    stats = [
      {
        "delta": "up",
        "title": "Spread",
        "measure": "20.2",
        "delta_measure": "2.2"
      },
      {
        "delta": "null",
        "title": "Rank",
        "measure": "1",
        "delta_measure": "0.0"
      },
      {
        "delta": "up",
        "title": "Games",
        "measure": "724",
        "delta_measure": "20"
      },
      {
        "delta": "down",
        "title": "Elo",
        "measure": "1151.124",
        "delta_measure": "14.5"
      }
    ]

    sidebar_data = [
      {
        "name": "Sport",
        "options": [
          {
            "name": "Men's Basketball"
          }
        ]
      },
      {
        "name": "State",
        "options": [
          {
            "name": "Michigan"
          }
        ]
      },
      {
        "name": "Division",
        "options": [
          {
            "name": "1A"
          }
        ]
      }
    ]

    sidebar_data.append(make_options(Conference.objects.all(), "Conference"))
    sidebar_data.append(make_options(Team.objects.all(), "Team"))

    teams = list(Team.objects.all())
    teams.sort(key=lambda x: x.elo, reverse=True)
    for team in teams:
        data.append([team.id, rank, team.name, team.wins, team.loses, team.elo])
        rank += 1
    context = RequestContext(request, {
        'team_rankings': data,
        'state': state,
        'sport': sport,
        'division': division,
        'conference': conference,
        'header_stats': stats,
        'sidebar_data': sidebar_data
    })
    return HttpResponse(template.render(context))

def make_options(objs, name):
    ret = {
        "name": name,
        "options": []
    }
    for obj in objs:
        ret['options'].append({'name': obj.name, 'id': obj.id})
    return ret
