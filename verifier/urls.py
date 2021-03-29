from django.conf.urls import url
from django.urls import path, include

from django.contrib import admin

admin.autodiscover()

# To add a new path, first import the app:
# import blog
#
# Then add the new path:
# path('blog/', blog.urls, name="blog")
#
# Learn more here: https://docs.djangoproject.com/en/2.1/topics/http/urls/

urlpatterns = [
    path("admin/", admin.site.urls),
    url(r'^', include(('social_django.urls', 'social_django'), namespace='social')),
    url(r'^', include(('authentication.urls', 'authentication'), namespace='auth')),
]
