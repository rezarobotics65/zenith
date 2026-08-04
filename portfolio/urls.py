from django.urls import path

from . import views

app_name = 'portfolio'

urlpatterns = [
    path('', views.home, name='home'),
    path('case-study/<slug:slug>/', views.case_study_detail, name='case_study_detail'),
    path('cv/download/', views.download_cv, name='download_cv'),
]
