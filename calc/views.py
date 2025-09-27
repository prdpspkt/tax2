import nepali_datetime
from django.shortcuts import render
import json

from .helper import get_taxes, calculated_taxes
from .models import FiscalYear, RegType, Category, CCRange, TaxRate
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
    form = TaxCalculatorForm(request.POST)
    if form.is_valid():
        last_paid_date = form.cleaned_data['last_paid_date']
        next_payment_date = form.cleaned_data['next_payment_date']

        last_paid_date = nepali_datetime.date(last_paid_date.year, last_paid_date.month,
                                              last_paid_date.day).to_datetime_date()
        next_payment_date = nepali_datetime.date(next_payment_date.year, next_payment_date.month,
                                                 next_payment_date.day).to_datetime_date()
        reg_type = form.cleaned_data['reg_type']
        category = form.cleaned_data['category']
        cc_power = form.cleaned_data['cc_power']

        calculated_taxes(next_payment_date, last_paid_date, reg_type, category, cc_power)

        taxes = get_taxes(due_date=next_payment_date, payment_date=last_paid_date)
        print(taxes)

        return render(request, 'calc/tax_calculator.html', {'form': form})

    else:
        return render(request, 'calc/tax_calculator.html', {'form': form})
