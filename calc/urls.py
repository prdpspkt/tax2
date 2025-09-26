from django.urls import path
from . import views

app_name = 'calc'

urlpatterns = [
    path('', views.tax_calculator, name='tax_calculator'),
    path('calculate/', views.calculate_tax, name='calculate_tax'),
]