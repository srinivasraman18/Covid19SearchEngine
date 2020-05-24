from django.urls import path, include

from .views import SearchView, FaqView, StatisticsView

urlpatterns = [
    path('search/', SearchView.as_view()),
    path('faq/', FaqView.as_view()),
    path('statistics/',StatisticsView.as_view()),
 
    
]