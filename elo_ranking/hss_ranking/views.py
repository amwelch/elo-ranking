from django.shortcuts import render
from django.http import HttpResponse
from django.template import RequestContext, loader

import scripts.scrape as scrape

# Create your views here.



def index(request):
    template = loader.get_template('hss_ranking/index.html')
    df = scrape.parse_season(max_pages=5)

    data = []
    rank = 1
    for index, row in df.iterrows():
        data.append([rank, row[0], '10', '5', row[1]])
        rank += 1
    context = RequestContext(request, {
        'team_rankings': data
    })
#    context = RequestContext(request, {
#        'team_rankings': [
#          [1, 'Huron', '4', '2', '1200'],
#          [2, 'Pioneer', '2', '4', '1100']],
#    })
    return HttpResponse(template.render(context))
