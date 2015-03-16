from django.conf.urls import patterns, url

from hss_ranking import views

urlpatterns = patterns('',
    url(r'^$', views.index, name='index'),
    url(r'^scrape_schedule$', views.fetch, name='scrape_schedule'),
    url(r'^scrape_teams$', views.fetch_teams, name='scrape_team'),
    url(r'^team_drill$', views.team_drill, name='drill'),
    url(r'^sim$', views.parse, name='parse')
)
