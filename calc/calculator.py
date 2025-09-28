from calc.models import FiscalYear, CCRange, TaxRate


class TaxCalculator():
    def __init__(self, form):
        self.province = form.cleaned_data['province']
        self.reg_type = form.cleaned_data['reg_type']
        self.cc_power = form.cleaned_data['cc_power']
        self.last_payment_date = form.cleaned_data['last_payment_date']
        self.next_payment_date = form.cleaned_data['next_payment_date']

    @staticmethod
    def find_fiscal_year(date):
        return FiscalYear.objects.filter(start_date__lte=date, end_date__gte=date).first()

    def find_cc_range(self):
        return CCRange.objects.filter(province=self.province, fiscal_year=self.find_fiscal_year, from_cc__lte=self.cc_power, to_cc__gte=self.cc_power).first()

    def find_vehicle_tax(self, fiscal_year):
        vehicle_tax = TaxRate.objects.filter(
            province=self.province,
            reg_type=self.reg_type,
            cc_power=self.cc_power,
            fiscal_year=fiscal_year
        )
