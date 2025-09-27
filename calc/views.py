from django.shortcuts import render
from django.views import View

from calc.forms import TaxCalculatorForm


class TaxCalculationView(View):
    def get(self, request):
        form = TaxCalculatorForm()
        return render(request, 'calc/tax_calculator.html', {
            'form': form,
        })
