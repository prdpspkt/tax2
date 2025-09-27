import decimal

import nepali_datetime
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple

from .models import FiscalYear, TaxRate, IncomeTaxRate, CCRange


def validate_nepali_date(date_string: str) -> bool:
    """
    Validate Nepali date string format and range

    Args:
        date_string: Date in YYYY-MM-DD format

    Returns:
        bool: True if valid, False otherwise
    """
    try:
        if not date_string or len(date_string) != 10:
            return False

        year, month, day = map(int, date_string.split('-'))

        # Validate ranges
        if not (2070 <= year <= 2090):
            return False
        if not (1 <= month <= 12):
            return False
        if not (1 <= day <= 32):
            return False

        # Try to create actual nepali_datetime object
        nepali_datetime.date(year, month, day)
        return True

    except (ValueError, TypeError):
        return False


def parse_nepali_date(date_string: str) -> Optional[nepali_datetime.date]:
    """
    Parse Nepali date string to nepali_datetime.date object

    Args:
        date_string: Date in YYYY-MM-DD format

    Returns:
        nepali_datetime.date object or None if invalid
    """
    try:
        if not validate_nepali_date(date_string):
            return None

        year, month, day = map(int, date_string.split('-'))
        return nepali_datetime.date(year, month, day)

    except Exception:
        return None


def get_fiscal_years_in_range(start_date: nepali_datetime.date,
                             end_date: nepali_datetime.date) -> List[FiscalYear]:
    """
    Get all fiscal years that overlap with the given date range

    Args:
        start_date: Start date in Nepali calendar
        end_date: End date in Nepali calendar

    Returns:
        List of FiscalYear objects
    """
    fiscal_years = []

    try:
        all_fiscal_years = FiscalYear.objects.all().order_by('start_date')

        for fy in all_fiscal_years:
            # Parse fiscal year dates
            fy_start = parse_nepali_date(str(fy.start_date))
            fy_end = parse_nepali_date(str(fy.end_date))

            if not fy_start or not fy_end:
                continue

            # Check if fiscal year overlaps with our date range
            if (fy_start <= end_date and fy_end >= start_date):
                fiscal_years.append(fy)

    except Exception as e:
        print(f"Error getting fiscal years: {e}")

    return fiscal_years


def calculate_days_between_dates(start_date: nepali_datetime.date,
                               end_date: nepali_datetime.date) -> int:
    """
    Calculate number of days between two Nepali dates

    Args:
        start_date: Start date
        end_date: End date

    Returns:
        Number of days
    """
    try:
        # Convert to English dates for calculation
        start_eng = start_date.to_datetime_date()
        end_eng = end_date.to_datetime_date()

        delta = end_eng - start_eng
        return delta.days

    except Exception:
        return 0


def get_applicable_tax_rate(reg_type, category, cc_range, fiscal_year) -> Optional[TaxRate]:
    """
    Find the applicable tax rate for given parameters

    Args:
        reg_type: RegType object
        category: Category object
        cc_range: CCRange object or None
        fiscal_year: FiscalYear object

    Returns:
        TaxRate object or None
    """
    try:
        query = TaxRate.objects.filter(
            reg_type=reg_type,
            category=category,
            fiscal_year=fiscal_year,
            tax_type=reg_type.tax_type
        )

        if cc_range:
            query = query.filter(cc_range=cc_range)
        else:
            query = query.filter(cc_range__isnull=True)

        return query.first()

    except Exception as e:
        print(f"Error finding tax rate: {e}")
        return None


def get_applicable_income_tax_rate(category, cc_range, fiscal_year) -> Optional[IncomeTaxRate]:
    """
    Find the applicable income tax rate for given parameters

    Args:
        category: Category object
        cc_range: CCRange object or None
        fiscal_year: FiscalYear object

    Returns:
        IncomeTaxRate object or None
    """
    try:
        query = IncomeTaxRate.objects.filter(
            category=category,
            fiscal_year=fiscal_year
        )

        if cc_range:
            # First try to find CC range specific income tax
            income_tax = query.filter(
                cc_range=cc_range,
                cc_range__for_income_tax=True
            ).first()

            if income_tax:
                return income_tax

        # Fall back to general income tax for category
        return query.filter(cc_range__isnull=True).first()

    except Exception as e:
        print(f"Error finding income tax rate: {e}")
        return None


def calculate_penalty(tax_amount: Decimal, income_tax: Decimal,
                     days_late: int, penalty_rules: Dict[str, Any] = None) -> Tuple[Decimal, str]:
    """
    Calculate penalty for late payment

    Args:
        tax_amount: Vehicle tax amount
        income_tax: Income tax amount
        days_late: Number of days past due
        penalty_rules: Custom penalty calculation rules

    Returns:
        Tuple of (penalty_amount, penalty_note)
    """
    if days_late <= 0:
        return Decimal('0'), ''

    try:
        # Default penalty rules (can be customized)
        if not penalty_rules:
            penalty_rules = {
                'rate_per_month': Decimal('0.10'),  # 10% per month
                'minimum_penalty': Decimal('50'),    # Minimum Rs. 50
                'maximum_rate': Decimal('1.00'),     # Maximum 100% of tax
            }

        # Calculate monthly penalty
        months_late = max(1, days_late // 30)  # At least 1 month
        penalty_rate = penalty_rules['rate_per_month'] * months_late

        # Cap at maximum rate
        penalty_rate = min(penalty_rate, penalty_rules['maximum_rate'])

        # Calculate penalty amount
        taxable_amount = tax_amount + income_tax
        penalty_amount = taxable_amount * penalty_rate

        # Apply minimum penalty
        penalty_amount = max(penalty_amount, penalty_rules['minimum_penalty'])

        penalty_note = f"Late payment penalty: {penalty_rate*100:.1f}% ({months_late} month(s) late)"

        return penalty_amount, penalty_note

    except Exception as e:
        print(f"Error calculating penalty: {e}")
        return Decimal('0'), f'Penalty calculation error: {str(e)}'


def find_cc_range_for_power(category, cc_power: Decimal) -> Optional[CCRange]:
    """
    Find the appropriate CC range for given category and power

    Args:
        category: Category object
        cc_power: Engine capacity or power value

    Returns:
        CCRange object or None
    """
    try:
        if not category.has_cc_range or not cc_power:
            return None

        return CCRange.objects.filter(
            category=category,
            from_cc__lte=cc_power,
            to_cc__gte=cc_power
        ).first()

    except Exception as e:
        print(f"Error finding CC range: {e}")
        return None


def format_currency(amount: Decimal, currency_symbol: str = "Rs.") -> str:
    """
    Format decimal amount as currency string

    Args:
        amount: Decimal amount
        currency_symbol: Currency symbol to use

    Returns:
        Formatted currency string
    """
    try:
        if not amount:
            amount = Decimal('0')

        # Format with commas and 2 decimal places
        formatted = f"{currency_symbol} {amount:,.2f}"
        return formatted

    except Exception:
        return f"{currency_symbol} 0.00"


def get_current_nepali_date() -> nepali_datetime.date:
    """
    Get current date in Nepali calendar

    Returns:
        Current Nepali date
    """
    try:
        return nepali_datetime.date.today()
    except Exception:
        # Fallback - approximate conversion
        import datetime
        today = datetime.date.today()
        # Rough conversion: add ~57 years to get Nepali year
        nepali_year = today.year + 57
        return nepali_datetime.date(nepali_year, today.month, today.day)


def validate_calculation_input(data: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """
    Validate all input data for tax calculation

    Args:
        data: Dictionary containing form data

    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []

    try:
        # Check required fields
        required_fields = ['reg_type', 'category', 'last_paid_date', 'next_payment_date']
        for field in required_fields:
            if not data.get(field):
                errors.append(f"{field.replace('_', ' ').title()} is required")

        # Validate dates
        last_paid = data.get('last_paid_date')
        next_payment = data.get('next_payment_date')

        if last_paid and not validate_nepali_date(last_paid):
            errors.append("Invalid last paid date format")

        if next_payment and not validate_nepali_date(next_payment):
            errors.append("Invalid next payment date format")

        if last_paid and next_payment and last_paid >= next_payment:
            errors.append("Next payment date must be after last paid date")

        # Validate CC/Power if required
        cc_power = data.get('cc_power')
        category = data.get('category')

        if category and hasattr(category, 'has_cc_range') and category.has_cc_range:
            if not cc_power or cc_power <= 0:
                errors.append("CC/Power is required and must be greater than 0 for this category")

        return len(errors) == 0, errors

    except Exception as e:
        return False, [f"Validation error: {str(e)}"]


def generate_calculation_summary(results: Dict[str, Any]) -> str:
    """
    Generate a text summary of the calculation results

    Args:
        results: Dictionary containing calculation results

    Returns:
        Formatted text summary
    """
    try:
        summary_lines = []

        # Header
        summary_lines.append("=== VEHICLE TAX CALCULATION SUMMARY ===")
        summary_lines.append("")

        # Vehicle info
        vehicle_info = results.get('vehicle_info', {})
        summary_lines.append("VEHICLE INFORMATION:")
        summary_lines.append(f"Registration Type: {vehicle_info.get('reg_type', 'N/A')}")
        summary_lines.append(f"Category: {vehicle_info.get('category', 'N/A')}")
        if vehicle_info.get('cc_power'):
            summary_lines.append(f"CC/Power: {vehicle_info.get('cc_power')} CC/KW")
        if vehicle_info.get('cc_range'):
            summary_lines.append(f"CC Range: {vehicle_info.get('cc_range')}")
        summary_lines.append("")

        # Fiscal year details
        fiscal_years = results.get('fiscal_years', [])
        if fiscal_years:
            summary_lines.append("FISCAL YEAR BREAKDOWN:")
            for fy in fiscal_years:
                summary_lines.append(f"  {fy.get('fiscal_year', 'Unknown Year')}:")
                summary_lines.append(f"    Vehicle Tax: {format_currency(Decimal(str(fy.get('tax_amount', 0))))}")
                summary_lines.append(f"    Renewal Fee: {format_currency(Decimal(str(fy.get('renewal_fee', 0))))}")
                summary_lines.append(f"    Income Tax: {format_currency(Decimal(str(fy.get('income_tax', 0))))}")
                summary_lines.append(f"    Penalty: {format_currency(Decimal(str(fy.get('penalty', 0))))}")
                if fy.get('case_note'):
                    summary_lines.append(f"    Note: {fy.get('case_note')}")
                summary_lines.append("")

        # Totals
        summary_lines.append("TOTAL SUMMARY:")
        summary_lines.append(f"Total Vehicle Tax: {format_currency(Decimal(str(results.get('total_tax', 0))))}")
        summary_lines.append(f"Total Renewal Fee: {format_currency(Decimal(str(results.get('total_renewal_fee', 0))))}")
        summary_lines.append(f"Total Income Tax: {format_currency(Decimal(str(results.get('total_income_tax', 0))))}")
        summary_lines.append(f"Total Penalty: {format_currency(Decimal(str(results.get('total_penalty', 0))))}")
        summary_lines.append("-" * 40)
        summary_lines.append(f"GRAND TOTAL: {format_currency(Decimal(str(results.get('grand_total', 0))))}")

        # Footer
        summary_lines.append("")
        summary_lines.append(f"Generated on: {get_current_nepali_date()}")
        summary_lines.append("Gandaki Province Vehicle Tax Calculator")

        return "\n".join(summary_lines)

    except Exception as e:
        return f"Error generating summary: {str(e)}"


def get_tax_calculation_context() -> Dict[str, Any]:
    """
    Get context data needed for tax calculation forms and display

    Returns:
        Dictionary containing context data
    """
    try:
        from .models import RegType, Category, FiscalYear

        context = {
            'reg_types': RegType.objects.all().order_by('name'),
            'categories': Category.objects.all().order_by('name'),
            'fiscal_years': FiscalYear.objects.all().order_by('-start_date'),
            'current_nepali_date': get_current_nepali_date(),
        }

        # Get CC ranges for categories
        cc_ranges_data = {}
        for category in context['categories']:
            if category.has_cc_range:
                ranges = CCRange.objects.filter(category=category).order_by('from_cc')
                cc_ranges_data[str(category.id)] = [
                    {
                        'id': range_obj.id,
                        'from_cc': float(range_obj.from_cc),
                        'to_cc': float(range_obj.to_cc),
                        'for_income_tax': range_obj.for_income_tax,
                        'display': f"{range_obj.from_cc} - {range_obj.to_cc}"
                    }
                    for range_obj in ranges
                ]

        context['cc_ranges_data'] = cc_ranges_data

        return context

    except Exception as e:
        print(f"Error getting context: {e}")
        return {}


def get_sample_calculation_data() -> Dict[str, Any]:
    """
    Get sample data for testing the calculator

    Returns:
        Dictionary with sample form data
    """
    try:
        from .models import RegType, Category

        # Get first available options
        reg_type = RegType.objects.filter(tax_type='PRIVATE').first()
        category = Category.objects.filter(has_cc_range=True).first()

        if not reg_type or not category:
            return {}

        return {
            'reg_type': reg_type.id,
            'category': category.id,
            'cc_power': '1500',  # 1500 CC
            'last_paid_date': '2080-01-01',  # Sample last paid date
            'next_payment_date': '2081-01-01',  # Sample next payment date
        }

    except Exception:
        return {}


def export_calculation_results(results: Dict[str, Any], format_type: str = 'txt') -> str:
    """
    Export calculation results in various formats

    Args:
        results: Calculation results dictionary
        format_type: Export format ('txt', 'csv', 'json')

    Returns:
        Formatted export string
    """
    try:
        if format_type.lower() == 'txt':
            return generate_calculation_summary(results)

        elif format_type.lower() == 'csv':
            import csv
            import io

            output = io.StringIO()
            writer = csv.writer(output)

            # Headers
            writer.writerow(['Description', 'Amount (Rs.)'])

            # Vehicle info
            vehicle_info = results.get('vehicle_info', {})
            writer.writerow(['Vehicle Type', vehicle_info.get('reg_type', 'N/A')])
            writer.writerow(['Category', vehicle_info.get('category', 'N/A')])

            # Totals
            writer.writerow(['Total Vehicle Tax', results.get('total_tax', 0)])
            writer.writerow(['Total Renewal Fee', results.get('total_renewal_fee', 0)])
            writer.writerow(['Total Income Tax', results.get('total_income_tax', 0)])
            writer.writerow(['Total Penalty', results.get('total_penalty', 0)])
            writer.writerow(['Grand Total', results.get('grand_total', 0)])

            return output.getvalue()

        elif format_type.lower() == 'json':
            import json
            return json.dumps(results, indent=2, default=str)

        else:
            return generate_calculation_summary(results)

    except Exception as e:
        return f"Export error: {str(e)}"


def validate_fiscal_year_data() -> Tuple[bool, List[str]]:
    """
    Validate that required fiscal year data exists in database

    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []

    try:
        from .models import FiscalYear, RegType, Category, TaxRate

        # Check if we have fiscal years
        fiscal_years = FiscalYear.objects.all()
        if not fiscal_years.exists():
            errors.append("No fiscal years defined in database")

        # Check if we have registration types
        reg_types = RegType.objects.all()
        if not reg_types.exists():
            errors.append("No registration types defined in database")

        # Check if we have categories
        categories = Category.objects.all()
        if not categories.exists():
            errors.append("No vehicle categories defined in database")

        # Check if we have tax rates
        tax_rates = TaxRate.objects.all()
        if not tax_rates.exists():
            errors.append("No tax rates defined in database")

        # Check for orphaned records
        for tax_rate in TaxRate.objects.all():
            if tax_rate.category.has_cc_range and not tax_rate.cc_range:
                errors.append(f"Tax rate {tax_rate.id} missing CC range for category requiring it")

        return len(errors) == 0, errors

    except Exception as e:
        return False, [f"Database validation error: {str(e)}"]


# Constants for the application
TAX_CALCULATION_CONSTANTS = {
    'DEFAULT_PENALTY_RATE': Decimal('0.10'),  # 10% per month
    'MINIMUM_PENALTY': Decimal('50'),         # Rs. 50 minimum
    'MAXIMUM_PENALTY_RATE': Decimal('1.00'),  # 100% maximum
    'CURRENCY_SYMBOL': 'Rs.',
    'DATE_FORMAT': 'YYYY-MM-DD',
    'MIN_NEPALI_YEAR': 2070,
    'MAX_NEPALI_YEAR': 2090,
}


# Utility decorators
def handle_calculation_errors(func):
    """
    Decorator to handle common calculation errors gracefully
    """
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"Calculation error in {func.__name__}: {e}")
            return None
    return wrapper


@handle_calculation_errors
def safe_decimal_conversion(value, default=Decimal('0')) -> Decimal:
    """
    Safely convert value to Decimal

    Args:
        value: Value to convert
        default: Default value if conversion fails

    Returns:
        Decimal value
    """
    try:
        if value is None or value == '':
            return default
        return Decimal(str(value))
    except (ValueError, TypeError, decimal.InvalidOperation):
        return default

