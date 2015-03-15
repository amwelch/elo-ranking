from django.conf.urls import patterns, url

from hss_ranking import views

urlpatterns = patterns('',
    url(r'^$', views.index, name='index'),
    url(r'^scrape_schedule$', views.fetch, name='fetch'),
    url(r'^scrape_teams$', views.fetch_teams, name='fetch'),
    url(r'^sim$', views.parse, name='parse')
)
