from django.urls import path
from . import views

app_name = 'solapp'

urlpatterns = [
    path('', views.index, name='index'),  # Homepage
    path('test/', views.test_htmx, name='test_htmx'),  # For your button
    path('generate/', views.generate_mnemonics_view, name='generate'),
    path('info/', views.info, name='info'),
]