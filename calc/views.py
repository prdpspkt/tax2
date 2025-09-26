from django.shortcuts import render
from django.http import JsonResponse
from django.utils import timezone
from datetime import datetime, timedelta
from decimal import Decimal
import json

from .models import FiscalYear, RegType, Category, CCRange, TaxRate, IncomeTaxRate

try:
    from nepali_date import NepaliDate

    NEPALI_DATE_AVAILABLE = True
except ImportError:
    NEPALI_DATE_AVAILABLE = False


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

            # Convert Nepali dates to Gregorian
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

            # Calculate tax using new fiscal year logic
            calculation_result = perform_tax_calculation_new(
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


def perform_tax_calculation_new(reg_type, category, cc_range, last_paid_date, next_payment_date, current_date):
    """
    New tax calculation logic based on fiscal year comparisons
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
        'grand_total': Decimal('0'),
        'calculation_details': {
            'last_paid_fy': None,
            'next_payment_fy': None,
            'current_fy': None,
            'case_applied': None
        }
    }

    # Step 1: Find fiscal years for all three dates
    last_paid_fy = find_fiscal_year_for_date(last_paid_date)
    next_payment_fy = find_fiscal_year_for_date(next_payment_date)
    current_fy = find_fiscal_year_for_date(current_date)

    # Store for debugging
    result['calculation_details']['last_paid_fy'] = last_paid_fy.name if last_paid_fy else None
    result['calculation_details']['next_payment_fy'] = next_payment_fy.name if next_payment_fy else None
    result['calculation_details']['current_fy'] = current_fy.name if current_fy else None

    if not last_paid_fy or not next_payment_fy or not current_fy:
        raise Exception("Could not determine fiscal years for given dates")

    # Step 2: Compare fiscal years and apply appropriate case
    if last_paid_fy == next_payment_fy:
        # CASE I: Same fiscal year for last_paid and next_payment
        result = apply_case_1(result, reg_type, category, cc_range,
                              last_paid_fy, next_payment_fy, current_fy,
                              last_paid_date, next_payment_date, current_date)
    else:
        # CASE II: Different fiscal years
        result = apply_case_2(result, reg_type, category, cc_range,
                              last_paid_fy, next_payment_fy, current_fy,
                              last_paid_date, next_payment_date, current_date)

    # Calculate grand total
    result['grand_total'] = (
            result['total_tax'] +
            result['total_renewal_fee'] +
            result['total_income_tax'] +
            result['total_penalty']
    )

    return result


def apply_case_1(result, reg_type, category, cc_range, last_paid_fy, next_payment_fy, current_fy,
                 last_paid_date, next_payment_date, current_date):
    """
    CASE I: Same fiscal year for last_paid and next_payment
    """
    result['calculation_details']['case_applied'] = 'CASE_1'

    if current_fy == last_paid_fy:
        # Case 1b: All three dates in same fiscal year - only renewal fee
        year_calc = calculate_renewal_only(reg_type, category, cc_range, current_fy,
                                           next_payment_date, current_date)
        year_calc['case_note'] = 'Same fiscal year - renewal only'
        result['fiscal_years'].append(year_calc)
        add_to_totals(result, year_calc)

    else:
        # Case 1a: Need to check if within 90 days and add current fiscal year tax
        days_from_next_payment = (current_date - next_payment_date).days

        # Add renewal for the original fiscal year
        renewal_calc = calculate_renewal_only(reg_type, category, cc_range, last_paid_fy,
                                              next_payment_date, current_date)

        if days_from_next_payment <= 90:
            # Within 90 days - no penalty on renewal
            renewal_calc['case_note'] = 'Within 90 days of next payment - no penalty'
        else:
            # Beyond 90 days - apply penalty
            renewal_calc = apply_renewal_penalty(renewal_calc, days_from_next_payment)
            renewal_calc['case_note'] = f'{days_from_next_payment} days overdue - penalty applied'

        result['fiscal_years'].append(renewal_calc)
        add_to_totals(result, renewal_calc)

        # Add vehicle tax for current fiscal year if different
        if current_fy != last_paid_fy:
            current_year_calc = calculate_full_tax(reg_type, category, cc_range, current_fy,
                                                   current_date, next_payment_date)
            current_year_calc['case_note'] = 'Current fiscal year vehicle tax'
            result['fiscal_years'].append(current_year_calc)
            add_to_totals(result, current_year_calc)

    return result


def apply_case_2(result, reg_type, category, cc_range, last_paid_fy, next_payment_fy, current_fy,
                 last_paid_date, next_payment_date, current_date):
    """
    CASE II: Different fiscal years for last_paid and next_payment
    """
    result['calculation_details']['case_applied'] = 'CASE_2'

    # Calculate all fiscal years between last_paid and current
    fiscal_years_to_process = get_fiscal_years_between(last_paid_fy, current_fy)

    for i, fy in enumerate(fiscal_years_to_process):
        if fy == last_paid_fy:
            # First fiscal year - only renewal fee with potential penalty
            year_calc = calculate_renewal_with_penalty(reg_type, category, cc_range, fy,
                                                       last_paid_date, next_payment_date, current_date)
            year_calc['case_note'] = 'Original fiscal year - renewal with penalty calculation'

        elif fy == current_fy and fy != next_payment_fy:
            # Current fiscal year - full tax
            year_calc = calculate_full_tax(reg_type, category, cc_range, fy,
                                           current_date, next_payment_date)
            year_calc['case_note'] = 'Current fiscal year - full vehicle tax'

        else:
            # Intermediate fiscal years - full tax with penalties
            year_calc = calculate_full_tax_with_penalty(reg_type, category, cc_range, fy,
                                                        current_date, next_payment_date, i)
            year_calc['case_note'] = f'Intermediate fiscal year ({i + 1} years overdue)'

        result['fiscal_years'].append(year_calc)
        add_to_totals(result, year_calc)

    return result


def calculate_renewal_only(reg_type, category, cc_range, fiscal_year, next_payment_date, current_date):
    """Calculate only renewal fee for a fiscal year"""
    year_calc = {
        'fiscal_year': fiscal_year.name,
        'tax_amount': Decimal('0'),
        'renewal_fee': Decimal('0'),
        'income_tax': Decimal('0'),
        'penalty': Decimal('0'),
        'penalty_details': [],
        'is_renewal_only': True
    }

    # Get base renewal fee
    tax_rate = get_tax_rate(reg_type, category, cc_range, fiscal_year)
    if tax_rate:
        year_calc['renewal_fee'] = tax_rate.renewal_fee

    return year_calc


def calculate_full_tax(reg_type, category, cc_range, fiscal_year, current_date, next_payment_date):
    """Calculate full tax (vehicle tax + renewal fee + income tax)"""
    year_calc = {
        'fiscal_year': fiscal_year.name,
        'tax_amount': Decimal('0'),
        'renewal_fee': Decimal('0'),
        'income_tax': Decimal('0'),
        'penalty': Decimal('0'),
        'penalty_details': [],
        'is_renewal_only': False
    }

    # Get base rates
    tax_rate = get_tax_rate(reg_type, category, cc_range, fiscal_year)

    if tax_rate:
        if reg_type.is_ambulance:
            # Ambulance only pays renewal fee
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

    return year_calc


def calculate_renewal_with_penalty(reg_type, category, cc_range, fiscal_year,
                                   last_paid_date, next_payment_date, current_date):
    """Calculate renewal fee with penalty based on time overdue"""
    year_calc = calculate_renewal_only(reg_type, category, cc_range, fiscal_year,
                                       next_payment_date, current_date)

    days_overdue = (current_date - next_payment_date).days
    years_overdue = max(0, (current_date.year - next_payment_date.year))

    # Apply renewal fee penalties based on time overdue
    if days_overdue > 90:
        if years_overdue >= 1:
            # Triple renewal fee after 1 year
            penalty_multiplier = 3
            penalty_amount = year_calc['renewal_fee'] * 2  # Additional 2x to make it 3x total
            year_calc['penalty'] = penalty_amount
            year_calc['penalty_details'].append({
                'type': 'Renewal Fee Penalty (Triple)',
                'rate': f'{years_overdue} year(s) overdue',
                'amount': penalty_amount
            })
        else:
            # Double renewal fee after 90 days
            penalty_multiplier = 2
            penalty_amount = year_calc['renewal_fee']  # Additional 1x to make it 2x total
            year_calc['penalty'] = penalty_amount
            year_calc['penalty_details'].append({
                'type': 'Renewal Fee Penalty (Double)',
                'rate': f'{days_overdue} days overdue',
                'amount': penalty_amount
            })

    return year_calc


def calculate_full_tax_with_penalty(reg_type, category, cc_range, fiscal_year,
                                    current_date, next_payment_date, years_behind):
    """Calculate full tax with penalties for intermediate fiscal years"""
    year_calc = calculate_full_tax(reg_type, category, cc_range, fiscal_year,
                                   current_date, next_payment_date)

    # Apply vehicle tax penalties based on how long overdue
    if year_calc['tax_amount'] > 0:
        if years_behind == 0:
            # Within same fiscal year - apply percentage penalties
            days_in_fy = (current_date - fiscal_year.start_date).days
            if days_in_fy <= 30:
                penalty_rate = 5
            elif days_in_fy <= 75:
                penalty_rate = 10
            else:
                penalty_rate = 20

            penalty_amount = year_calc['tax_amount'] * (penalty_rate / 100)
            year_calc['penalty'] += penalty_amount
            year_calc['penalty_details'].append({
                'type': f'Vehicle Tax Penalty ({penalty_rate}%)',
                'rate': f'{days_in_fy} days in fiscal year',
                'amount': penalty_amount
            })
        else:
            # Multiple years behind - 20% penalty
            penalty_amount = year_calc['tax_amount'] * Decimal('0.20')
            year_calc['penalty'] += penalty_amount
            year_calc['penalty_details'].append({
                'type': 'Vehicle Tax Penalty (20%)',
                'rate': f'{years_behind} year(s) overdue',
                'amount': penalty_amount
            })

    return year_calc


def apply_renewal_penalty(year_calc, days_overdue):
    """Apply penalty to renewal fee calculation"""
    if days_overdue > 90:
        penalty_amount = year_calc['renewal_fee']  # Double the renewal fee
        year_calc['penalty'] = penalty_amount
        year_calc['penalty_details'].append({
            'type': 'Renewal Fee Penalty (Double)',
            'rate': f'{days_overdue} days overdue',
            'amount': penalty_amount
        })
    return year_calc


def add_to_totals(result, year_calc):
    """Add year calculation to result totals"""
    result['total_tax'] += year_calc['tax_amount']
    result['total_renewal_fee'] += year_calc['renewal_fee']
    result['total_income_tax'] += year_calc['income_tax']
    result['total_penalty'] += year_calc['penalty']


def find_fiscal_year_for_date(date):
    """Find the fiscal year that contains the given date"""
    return FiscalYear.objects.filter(
        start_date__lte=date,
        end_date__gte=date
    ).first()


def get_fiscal_years_between(start_fy, end_fy):
    """Get all fiscal years between start_fy and end_fy (inclusive)"""
    return FiscalYear.objects.filter(
        start_date__gte=start_fy.start_date,
        start_date__lte=end_fy.start_date
    ).order_by('start_date')


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


def convert_bs_to_ad(bs_date_string):
    """
    Convert Nepali BS date to Gregorian AD date
    """
    try:
        if NEPALI_DATE_AVAILABLE:
            # Use proper nepali-date library
            year, month, day = map(int, bs_date_string.split('-'))
            nepali_date = NepaliDate(year, month, day)
            return nepali_date.to_english_date()
        else:
            # Fallback approximation
            year, month, day = map(int, bs_date_string.split('-'))
            # Simple approximation (subtract 56/57 years)
            ad_year = year - 57 if month <= 9 else year - 56
            return datetime(ad_year, month, day).date()
    except Exception as e:
        # Return current date as fallback
        return timezone.now().date()


# Keep original functions for backward compatibility
def perform_tax_calculation(reg_type, category, cc_range, last_paid_date, next_payment_date, current_date):
    """Original tax calculation logic - kept for backward compatibility"""
    return perform_tax_calculation_new(reg_type, category, cc_range, last_paid_date, next_payment_date, current_date)


def calculate_year_tax(reg_type, category, cc_range, fiscal_year, last_paid_date, next_payment_date, current_date):
    """Original year tax calculation - kept for backward compatibility"""
    return calculate_full_tax(reg_type, category, cc_range, fiscal_year, current_date, next_payment_date)


def calculate_penalties(fiscal_year, current_date, tax_amount, renewal_fee, is_renewal_only):
    """Original penalty calculation - kept for backward compatibility"""
    return {
        'total_penalty': Decimal('0'),
        'details': []
    }


def get_tax_penalty_rate(days_overdue):
    """Original tax penalty rate calculation"""
    if days_overdue <= 90:
        return 0
    elif days_overdue <= 120:
        return 5
    elif days_overdue <= 165:
        return 10
    else:
        return 20


def get_renewal_penalty(fiscal_year, current_date):
    """Original renewal penalty calculation"""
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
    """Original applicable fiscal years function"""
    return FiscalYear.objects.filter(
        end_date__gt=last_paid_date,
        start_date__lte=current_date
    ).order_by('start_date')


def is_same_fiscal_year(last_paid_date, next_payment_date, fiscal_year):
    """Original same fiscal year check"""
    return (fiscal_year.start_date <= last_paid_date <= fiscal_year.end_date and
            fiscal_year.start_date <= next_payment_date <= fiscal_year.end_date)