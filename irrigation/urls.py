from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),

    # Auth
    path('register/', views.register, name='register'),
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),

    # Main pages
    path('about/', views.about_page, name='about'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('ahp/', views.ahp_page, name='ahp'),
    path('map/', views.map_view, name='map'),
    path('sensor/', views.sensor_page, name='sensor'),
    path('irrigation/', views.irrigation_page, name='irrigation'),
    path('simulation/', views.simulation, name='simulation'),

    # API / Data
    path('calculate/', views.calculate_irrigation, name='calculate'),
    path('realtime/', views.realtime_data, name='realtime'),
    path('map_status/', views.map_status, name='map_status'),
    path('sensor_data/', views.sensor_data, name='sensor_data'),
    path('api/weather/', views.get_weather, name='get_weather'),
    path('chatbot/', views.chatbot_response, name='chatbot'),   
    
    #New AI và realtime
    path('gardens_realtime/', views.gardens_realtime, name='gardens_realtime'),
    path('api/compare-gardens/', views.compare_gardens, name='compare_gardens'),
    path('api/ahp-ai/', views.ahp_ai_data, name='ahp_ai_data'),
]