from django.conf.urls import url
from django.contrib.auth.decorators import login_required

from authentication.views import *

urlpatterns = [
    url(r'^$', index, name='index'),
    url(r'^logout', logout, name='logout')
]
