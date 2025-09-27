import nepali_datetime_field
from django import forms
from django.core.exceptions import ValidationError
import re

from nepali_datetime_field.forms import NepaliDateField

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

    last_paid_date = NepaliDateField(help_text="Date in BS")

    next_payment_date = NepaliDateField(help_text="Date in BS")

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