from django.shortcuts import render
from django.http import HttpResponse
from django.template import RequestContext, loader

from hss_ranking.models import Team, Game
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
    games = Game.objects.all()
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
    team_info['rank'] = team.rank
    data = []
    games = Game.objects.filter(team1=team) 
    for game in games:
        data.append([game.team1.name, game.team2.name, game.score1, game.score2])
    games = Game.objects.filter(team2=team)
    for game in games:
        data.append([game.team1.name, game.team2.name, game.score1, game.score2])
    context = RequestContext(request, {
        'team_schedule': data,
        'team_info': team_info
    })
    return HttpResponse(template.render(context))

def index(request):
    template = loader.get_template('hss_ranking/index.html')
    data = []
    rank = 1
    teams = list(Team.objects.all())
    teams.sort(key=lambda x: x.elo, reverse=True)
    for team in teams:
        data.append([rank, team.name, team.wins, team.loses, team.elo])
        rank += 1
    context = RequestContext(request, {
        'team_rankings': data
    })
    return HttpResponse(template.render(context))
