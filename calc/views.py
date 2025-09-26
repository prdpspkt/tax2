from django.shortcuts import render
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import json

from .models import FiscalYear, RegType, Category, CCRange, TaxRate, IncomeTaxRate


def tax_calculator(request):
    """Display the tax calculator form"""
    # Get all necessary data for form dropdowns
    reg_types = RegType.objects.all()
    categories = Category.objects.all()
    fiscal_years = FiscalYear.objects.all().order_by('-start_date')

    context = {
        'reg_types': reg_types,
        'categories': categories,
        'fiscal_years': fiscal_years,
    }
    return render(request, 'calc/tax_calculator.html', context)


def calculate_tax(request):
    """Calculate tax based on user inputs"""
    if request.method == 'POST':
        try:
            # Get form data
            reg_type_id = request.POST.get('reg_type')
            category_id = request.POST.get('category')
            cc_power = Decimal(request.POST.get('cc_power', '0'))
            last_paid_date_bs = request.POST.get('last_paid_date')
            next_payment_date_bs = request.POST.get('next_payment_date')

            # Convert Nepali dates to Gregorian (for now using placeholder conversion)
            # TODO: Implement proper Nepali date conversion
            last_paid_date = convert_bs_to_ad(last_paid_date_bs)
            next_payment_date = convert_bs_to_ad(next_payment_date_bs)
            current_date = timezone.now().date()

            # Get model instances
            reg_type = RegType.objects.get(id=reg_type_id)
            category = Category.objects.get(id=category_id)

            # Find applicable CC range
            cc_range = None
            if category.has_cc_range:
                cc_range = CCRange.objects.filter(
                    category=category,
                    from_cc__lte=cc_power,
                    to_cc__gte=cc_power
                ).first()

            # Calculate tax
            calculation_result = perform_tax_calculation(
                reg_type, category, cc_range, last_paid_date,
                next_payment_date, current_date
            )

            return JsonResponse({
                'success': True,
                'result': calculation_result
            })

        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            })

    return JsonResponse({'success': False, 'error': 'Invalid request method'})


def perform_tax_calculation(reg_type, category, cc_range, last_paid_date, next_payment_date, current_date):
    """
    Main tax calculation logic
    """
    result = {
        'vehicle_info': {
            'reg_type': reg_type.name,
            'category': category.name,
            'cc_range': str(cc_range) if cc_range else 'N/A'
        },
        'fiscal_years': [],
        'total_tax': Decimal('0'),
        'total_renewal_fee': Decimal('0'),
        'total_income_tax': Decimal('0'),
        'total_penalty': Decimal('0'),
        'grand_total': Decimal('0')
    }

    # Find fiscal years between last_paid_date and current_date
    fiscal_years = get_applicable_fiscal_years(last_paid_date, current_date)

    for fiscal_year in fiscal_years:
        year_calculation = calculate_year_tax(
            reg_type, category, cc_range, fiscal_year,
            last_paid_date, next_payment_date, current_date
        )
        result['fiscal_years'].append(year_calculation)

        # Add to totals
        result['total_tax'] += year_calculation['tax_amount']
        result['total_renewal_fee'] += year_calculation['renewal_fee']
        result['total_income_tax'] += year_calculation['income_tax']
        result['total_penalty'] += year_calculation['penalty']

    result['grand_total'] = (
            result['total_tax'] +
            result['total_renewal_fee'] +
            result['total_income_tax'] +
            result['total_penalty']
    )

    return result


def calculate_year_tax(reg_type, category, cc_range, fiscal_year, last_paid_date, next_payment_date, current_date):
    """
    Calculate tax for a specific fiscal year
    """
    year_calc = {
        'fiscal_year': fiscal_year.name,
        'tax_amount': Decimal('0'),
        'renewal_fee': Decimal('0'),
        'income_tax': Decimal('0'),
        'penalty': Decimal('0'),
        'penalty_details': [],
        'is_renewal_only': False
    }

    # Check if this year is renewal only (same fiscal year as last_paid and next_payment)
    if (is_same_fiscal_year(last_paid_date, next_payment_date, fiscal_year)):
        year_calc['is_renewal_only'] = True

    # Get base rates
    tax_rate = get_tax_rate(reg_type, category, cc_range, fiscal_year)

    if tax_rate:
        # Determine what to pay based on vehicle type
        if reg_type.is_ambulance:
            # Ambulance only pays renewal fee
            year_calc['renewal_fee'] = tax_rate.renewal_fee
        elif year_calc['is_renewal_only']:
            # Only renewal fee for same fiscal year
            year_calc['renewal_fee'] = tax_rate.renewal_fee
        else:
            # Full tax payment
            year_calc['tax_amount'] = tax_rate.vehicle_tax
            year_calc['renewal_fee'] = tax_rate.renewal_fee

            # Income tax for eligible vehicles
            if reg_type.needs_income_tax and reg_type.name.lower() != 'government':
                income_tax_rate = get_income_tax_rate(category, cc_range, fiscal_year)
                if income_tax_rate:
                    year_calc['income_tax'] = income_tax_rate.income_tax

    # Calculate penalties
    penalty_calc = calculate_penalties(
        fiscal_year, current_date, year_calc['tax_amount'],
        year_calc['renewal_fee'], year_calc['is_renewal_only']
    )
    year_calc['penalty'] = penalty_calc['total_penalty']
    year_calc['penalty_details'] = penalty_calc['details']

    return year_calc


def get_tax_rate(reg_type, category, cc_range, fiscal_year):
    """Get tax rate for given parameters"""
    # Determine tax_type based on reg_type
    if reg_type.name.lower() == 'government':
        tax_type = 'PUBLIC'  # Government pays as public but no income tax
    else:
        tax_type = reg_type.tax_type

    return TaxRate.objects.filter(
        reg_type=reg_type,
        category=category,
        cc_range=cc_range,
        fiscal_year=fiscal_year,
        tax_type=tax_type
    ).first()


def get_income_tax_rate(category, cc_range, fiscal_year):
    """Get income tax rate for given parameters"""
    return IncomeTaxRate.objects.filter(
        category=category,
        cc_range=cc_range,
        fiscal_year=fiscal_year
    ).first()


def calculate_penalties(fiscal_year, current_date, tax_amount, renewal_fee, is_renewal_only):
    """
    Calculate penalties based on Gandaki province rules
    """
    penalty_calc = {
        'total_penalty': Decimal('0'),
        'details': []
    }

    # Calculate days overdue from fiscal year end
    days_overdue = (current_date - fiscal_year.end_date).days

    if days_overdue <= 90:
        # No penalty within 90 days
        return penalty_calc

    # Tax penalty calculation
    if not is_renewal_only and tax_amount > 0:
        tax_penalty_rate = get_tax_penalty_rate(days_overdue)
        tax_penalty = tax_amount * (tax_penalty_rate / 100)
        penalty_calc['total_penalty'] += tax_penalty
        penalty_calc['details'].append({
            'type': 'Tax Penalty',
            'rate': f"{tax_penalty_rate}%",
            'amount': tax_penalty
        })

    # Renewal fee penalty (flat rates)
    if renewal_fee > 0:
        renewal_penalty = get_renewal_penalty(fiscal_year, current_date)
        penalty_calc['total_penalty'] += renewal_penalty
        penalty_calc['details'].append({
            'type': 'Renewal Fee Penalty',
            'rate': 'Flat Rate',
            'amount': renewal_penalty
        })

    return penalty_calc


def get_tax_penalty_rate(days_overdue):
    """Get tax penalty percentage based on days overdue"""
    if days_overdue <= 90:
        return 0
    elif days_overdue <= 120:  # 91-120 days (first 30 days after 90)
        return 5
    elif days_overdue <= 165:  # 121-165 days (next 45 days)
        return 10
    else:  # After 165 days
        return 20


def get_renewal_penalty(fiscal_year, current_date):
    """Get renewal fee penalty (flat amounts)"""
    # Calculate how many years overdue
    years_overdue = current_date.year - fiscal_year.end_date.year

    if years_overdue <= 0:
        return Decimal('0')
    elif years_overdue == 1:
        return Decimal('100')
    elif years_overdue == 2:
        return Decimal('200')
    elif years_overdue == 3:
        return Decimal('300')
    elif years_overdue == 4:
        return Decimal('400')
    else:
        return Decimal('500')


def get_applicable_fiscal_years(last_paid_date, current_date):
    """Get all fiscal years between last_paid_date and current_date"""
    return FiscalYear.objects.filter(
        end_date__gt=last_paid_date,
        start_date__lte=current_date
    ).order_by('start_date')


def is_same_fiscal_year(last_paid_date, next_payment_date, fiscal_year):
    """Check if both dates fall within the same fiscal year"""
    return (fiscal_year.start_date <= last_paid_date <= fiscal_year.end_date and
            fiscal_year.start_date <= next_payment_date <= fiscal_year.end_date)


def convert_bs_to_ad(bs_date_string):
    """
    Convert Nepali BS date to Gregorian AD date
    TODO: Implement proper conversion using nepali-datetime library
    For now, this is a placeholder
    """
    try:
        # Placeholder implementation - need to install and use proper library
        # Assuming format: YYYY-MM-DD
        year, month, day = map(int, bs_date_string.split('-'))
        # Simple approximation (subtract 56/57 years)
        ad_year = year - 57 if month <= 9 else year - 56
        return datetime(ad_year, month, day).date()
    except:
        return timezone.now().date()