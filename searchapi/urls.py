from django.urls import path, include

from .views import SearchView, FaqView

urlpatterns = [
    path('search/', SearchView.as_view()),
    path('faq/', FaqView.as_view()),
 
    
]