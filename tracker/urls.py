from django.urls import path

from . import views

app_name = 'tracker'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('kpi/', views.kpi_timetable, name='kpi_timetable'),
    path('activity/', views.activity_log, name='activity_log'),
    path('cv/', views.cv_list, name='cv_list'),

    path('add/<slug:model_slug>/', views.edit_object, name='add_object'),
    path('edit/<slug:model_slug>/<int:pk>/', views.edit_object, name='edit_object'),
    path('delete/<slug:model_slug>/<int:pk>/', views.delete_object, name='delete_object'),
    path('commitment/<int:pk>/toggle/', views.toggle_commitment, name='toggle_commitment'),
    path('kpi/<int:pk>/quick-update/', views.quick_update_kpi, name='quick_update_kpi'),
    path('course/<int:pk>/quick-update/', views.quick_update_course, name='quick_update_course'),
    path('course/<int:pk>/set-hours/', views.quick_set_course_hours, name='quick_set_course_hours'),
    path('cv/<int:pk>/set-default/', views.set_default_resume, name='set_default_resume'),
]
