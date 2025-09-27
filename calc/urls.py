from django.urls import path
from . import views

app_name = 'calc'

urlpatterns = [
    path('', views.TaxCalculationView.as_view(), name='tax_calculator')
]