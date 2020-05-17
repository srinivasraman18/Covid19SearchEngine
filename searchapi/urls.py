from django.urls import path, include

from .views import SearchView

urlpatterns = [
    path('search/', SearchView.as_view()),
 
    
]