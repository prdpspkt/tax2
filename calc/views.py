from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from datetime import datetime
from decimal import Decimal
import json

from .models import FiscalYear, RegType, Category, CCRange, TaxRate, IncomeTaxRate
from .forms import TaxCalculatorForm


def tax_calculator(request):
    """
    Display the tax calculator form with all necessary data
    """
    # Initialize form
    form = TaxCalculatorForm()

    # Get all data for dropdowns
    reg_types = RegType.objects.all().order_by('name')
    categories = Category.objects.all().order_by('name')
    fiscal_years = FiscalYear.objects.all().order_by('-start_date')

    # Get CC ranges for each category (for JavaScript)
    cc_ranges_data = {}
    for category in categories:
        if category.has_cc_range:
            ranges = CCRange.objects.filter(category=category).order_by('from_cc')
            cc_ranges_data[str(category.id)] = [
                {
                    'id': range.id,
                    'from_cc': float(range.from_cc),
                    'to_cc': float(range.to_cc),
                    'for_income_tax': range.for_income_tax
                }
                for range in ranges
            ]

    context = {
        'form': form,
        'reg_types': reg_types,
        'categories': categories,
        'fiscal_years': fiscal_years,
        'cc_ranges_data': json.dumps(cc_ranges_data),
    }

    return render(request, 'calc/tax_calculator.html', context)


def calculate_tax(request):
    """
    Calculate tax based on form submission
    """
    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'error': 'Invalid request method'
        })
    print(request.POST)