from datetime import date, timedelta
from calc.models import FiscalYear, TaxRate, CCRange


def get_taxes(due_date, payment_date):
    vehicle_taxes = [1, 1.05, 1.10, 1.20, 1.40, 1.60, 1.80, 2.00]
    today = date.today()
    taxes = []

    fiscal_years = FiscalYear.objects.order_by('-id')
    for year, fiscal_year in enumerate(fiscal_years):
        if not (fiscal_year.start_date <= today <= fiscal_year.end_date):
            continue  # only current fiscal year matters

        days = (today - due_date).days

        # due_date lies inside current fiscal year
        if fiscal_year.start_date <= due_date <= fiscal_year.end_date:

            if fiscal_year.start_date <= payment_date <= fiscal_year.end_date:
                # case i & ii
                renewal_tax = 2 if days > 90 else 1
                next_date = (due_date if days > 90 else today) + timedelta(days=365)
                taxes.append({
                    'fiscal_year': fiscal_year,
                    'vehicle_tax': 0,
                    'income_tax': 0,
                    'renewal_tax': renewal_tax,
                    'next_payment_date': next_date,
                })

            else:
                # case iii → vi
                if days < 90:
                    taxes.append({
                        'fiscal_year': fiscal_year,
                        'vehicle_tax': 1,
                        'income_tax': 1,
                        'renewal_tax': 1,
                        'next_payment_date': due_date + timedelta(days=365),
                    })
                elif 90 < days <= 120:
                    taxes.append({
                        'fiscal_year': fiscal_year,
                        'vehicle_tax': 1.05,
                        'income_tax': 1,
                        'renewal_tax': 2,
                        'next_payment_date': due_date + timedelta(days=365),
                    })
                elif 120 <= days <= 165:
                    taxes.append({
                        'fiscal_year': fiscal_year,
                        'vehicle_tax': 1.10,
                        'income_tax': 1,
                        'renewal_tax': 2,
                    })
                elif days >= 160:
                    taxes.append({
                        'fiscal_year': fiscal_year,
                        'vehicle_tax': 1.20,
                        'income_tax': 1,
                        'renewal_tax': 2,
                    })

        else:
            # due date lies outside current fiscal year
            if fiscal_year.end_date <= due_date <= fiscal_year.start_date:
                # case vii & viii
                if fiscal_year.end_date <= payment_date <= fiscal_year.start_date:
                    taxes.append({
                        'fiscal_year': fiscal_year,
                        'vehicle_tax': 0,
                        'income_tax': 0,
                        'renewal_tax': 1 if days < 90 else 2
                    })
                else:
                    taxes.append({
                        'fiscal_year': fiscal_year,
                        'vehicle_tax': vehicle_taxes[year],
                        'income_tax': 0,
                        'renewal_tax': 2 * year
                    })
            else:
                # case ix
                taxes.append({
                    'fiscal_year': fiscal_year,
                    'vehicle_tax': vehicle_taxes[year],
                    'income_tax': 0,
                    'renewal_tax': 2
                })

    return taxes


def calculated_taxes(next_payment_date, last_payment_date, reg_type, category, cc_power):
    tax_rates = get_taxes(next_payment_date, last_payment_date)
    c_taxes = []
    print(cc_power)
    for fy in tax_rates:
        cc_range = CCRange.objects.filter(from_cc__lte=cc_power, to_cc__lte=cc_power, category=category)
        if cc_range is None:
            cc_range = CCRange.objects.filter(from_cc__lte=cc_power, to_cc=0, category=category)
        else:
            cc_range = None

        if cc_range is not None:
            tax_rate = TaxRate.objects.filter(fiscal_year=fy['fiscal_year'], cc_range=cc_range, category=category,
                                              reg_type=reg_type)
        else:
            tax_rate = TaxRate.objects.filter(fiscal_year=fy['fiscal_year'], category=category, reg_type=reg_type)
        print(tax_rate)
