from django import forms
from django.core.exceptions import ValidationError
from decimal import Decimal
import re

from .models import RegType, Category, CCRange


class TaxCalculatorForm(forms.Form):
    """Simple Vehicle Tax Calculator Form"""

    reg_type = forms.ModelChoiceField(
        queryset=RegType.objects.all(),
        empty_label="Select Registration Type",
        label="Registration Type"
    )

    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        empty_label="Select Vehicle Category",
        label="Vehicle Category"
    )

    cc_power = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        label="CC/Power/KW"
    )

    last_paid_date = forms.CharField(
        max_length=10,
        label="Last Paid Date (BS)"
    )

    next_payment_date = forms.CharField(
        max_length=10,
        label="Next Payment Date (BS)"
    )

    def clean_cc_power(self):
        cc_power = self.cleaned_data.get('cc_power')
        category = self.cleaned_data.get('category')

        if category and category.has_cc_range:
            if not cc_power:
                raise ValidationError("CC/Power is required for this category.")
            if cc_power <= 0:
                raise ValidationError("CC/Power must be greater than 0.")

        return cc_power

    def clean_last_paid_date(self):
        return self._validate_date(self.cleaned_data.get('last_paid_date'), 'Last Paid Date')

    def clean_next_payment_date(self):
        return self._validate_date(self.cleaned_data.get('next_payment_date'), 'Next Payment Date')

    def _validate_date(self, date_str, field_name):
        if not date_str:
            raise ValidationError(f"{field_name} is required.")

        if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
            raise ValidationError(f"{field_name} must be in YYYY-MM-DD format.")

        year, month, day = map(int, date_str.split('-'))

        if not (2070 <= year <= 2090):
            raise ValidationError("Year must be between 2070 and 2090 BS.")
        if not (1 <= month <= 12):
            raise ValidationError("Month must be between 1 and 12.")
        if not (1 <= day <= 32):
            raise ValidationError("Day must be between 1 and 32.")

        return date_str

    def clean(self):
        cleaned_data = super().clean()
        last_paid = cleaned_data.get('last_paid_date')
        next_payment = cleaned_data.get('next_payment_date')

        if last_paid and next_payment and last_paid >= next_payment:
            raise ValidationError('Next payment date must be after last paid date.')

        return cleaned_data

    def get_cc_range(self):
        """Get CC range for selected category and power"""
        if self.is_valid():
            category = self.cleaned_data.get('category')
            cc_power = self.cleaned_data.get('cc_power')

            if category and category.has_cc_range and cc_power:
                return CCRange.objects.filter(
                    category=category,
                    from_cc__lte=cc_power,
                    to_cc__gte=cc_power
                ).first()
        return None