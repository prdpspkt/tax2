from django import forms
from django.core.exceptions import ValidationError
import re
import nepali_datetime
from .models import RegType, Category, CCRange, FiscalYear
from .helper import validate_nepali_date, parse_nepali_date, find_cc_range_for_power


class TaxCalculatorForm(forms.Form):

    reg_type = forms.ModelChoiceField(
        queryset=RegType.objects.all(),
        empty_label="Select Registration Type",
        label="Registration Type",
        widget=forms.Select(attrs={
            'class': 'form-select',
            'data-bs-toggle': 'tooltip',
            'data-bs-placement': 'top',
            'title': 'Choose your vehicle registration type'
        }),
        help_text="Select the appropriate registration category for your vehicle"
    )

    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        empty_label="Select Vehicle Category",
        label="Vehicle Category",
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'category',
            'data-bs-toggle': 'tooltip',
            'data-bs-placement': 'top',
            'title': 'Select your vehicle category'
        }),
        help_text="Choose the category that matches your vehicle type"
    )

    cc_power = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        label="CC/Power/KW",
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': '0.01',
            'placeholder': 'Enter CC/Power value',
            'data-bs-toggle': 'tooltip',
            'data-bs-placement': 'top',
            'title': 'Enter your vehicle engine capacity in CC or power in KW'
        }),
        help_text="Enter engine capacity (CC) or power rating (KW/W)"
    )

    last_paid_date = forms.CharField(
        max_length=10,
        label="Last Paid Date (BS)",
        widget=forms.TextInput(attrs={
            'class': 'form-control date-input',
            'placeholder': 'YYYY-MM-DD',
            'maxlength': '10',
            'pattern': r'\d{4}-\d{2}-\d{2}',
            'data-bs-toggle': 'tooltip',
            'data-bs-placement': 'top',
            'title': 'Enter the last date you paid vehicle tax in Nepali date format'
        }),
        help_text="Nepali date format (e.g., 2080-04-15)"
    )

    next_payment_date = forms.CharField(
        max_length=10,
        label="Next Payment Date (BS)",
        widget=forms.TextInput(attrs={
            'class': 'form-control date-input',
            'placeholder': 'YYYY-MM-DD',
            'maxlength': '10',
            'pattern': r'\d{4}-\d{2}-\d{2}',
            'data-bs-toggle': 'tooltip',
            'data-bs-placement': 'top',
            'title': 'Enter the date until which you want to pay tax in Nepali date format'
        }),
        help_text="Nepali date format (e.g., 2081-04-15)"
    )

    def __init__(self, *args, **kwargs):
        """Initialize form with dynamic queryset ordering and additional setup"""
        super().__init__(*args, **kwargs)

        # Order querysets for better UX
        self.fields['reg_type'].queryset = RegType.objects.all().order_by('name')
        self.fields['category'].queryset = Category.objects.all().order_by('name')

        # Add CSS classes for better styling
        for field_name, field in self.fields.items():
            if 'class' not in field.widget.attrs:
                if isinstance(field.widget, forms.Select):
                    field.widget.attrs['class'] = 'form-select'
                else:
                    field.widget.attrs['class'] = 'form-control'

    def clean_reg_type(self):
        """Validate registration type"""
        reg_type = self.cleaned_data.get('reg_type')

        if not reg_type:
            raise ValidationError("Registration type is required.")

        # Check if registration type is active (you can add an 'is_active' field to model if needed)
        if not hasattr(reg_type, 'name') or not reg_type.name:
            raise ValidationError("Invalid registration type selected.")

        return reg_type

    def clean_category(self):
        """Validate vehicle category"""
        category = self.cleaned_data.get('category')

        if not category:
            raise ValidationError("Vehicle category is required.")

        if not hasattr(category, 'name') or not category.name:
            raise ValidationError("Invalid vehicle category selected.")

        return category

    def clean_cc_power(self):
        """Validate CC/Power field with enhanced logic"""
        cc_power = self.cleaned_data.get('cc_power')
        category = self.cleaned_data.get('category')

        # Check if CC/Power is required for this category
        if category and category.has_cc_range:
            if not cc_power:
                raise ValidationError("CC/Power is required for this vehicle category.")

            if cc_power <= 0:
                raise ValidationError("CC/Power must be greater than 0.")

            # Check if the CC/Power value has a valid range defined
            cc_range = find_cc_range_for_power(category, cc_power)
            if not cc_range:
                # Get available ranges for user guidance
                available_ranges = CCRange.objects.filter(category=category).order_by('from_cc')
                if available_ranges.exists():
                    ranges_text = ", ".join([f"{r.from_cc}-{r.to_cc}" for r in available_ranges])
                    raise ValidationError(
                        f"No tax range found for {cc_power} CC/Power. "
                        f"Available ranges: {ranges_text}"
                    )
                else:
                    raise ValidationError(
                        f"No CC/Power ranges are configured for {category.name} category."
                    )

            # Validate reasonable limits (you can adjust these)
            if category.name_en.lower() in ['motorcycle', 'motorbike']:
                if cc_power > 3000:  # 3000 CC seems unreasonable for motorcycles
                    raise ValidationError("CC value seems too high for a motorcycle.")
            elif category.name_en.lower() in ['car', 'jeep']:
                if cc_power > 10000:  # 10000 CC seems unreasonable for cars
                    raise ValidationError("CC value seems too high for a car.")

        elif cc_power and cc_power != 0:
            # CC/Power provided but not required
            raise ValidationError("CC/Power is not applicable for this vehicle category.")

        return cc_power

    def clean_last_paid_date(self):
        """Validate last paid date with enhanced Nepali date validation"""
        date_str = self.cleaned_data.get('last_paid_date')

        if not date_str:
            raise ValidationError("Last paid date is required.")

        # Basic format validation
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str.strip()):
            raise ValidationError(
                "Date must be in YYYY-MM-DD format (e.g., 2080-04-15)."
            )

        # Use helper function for validation
        if not validate_nepali_date(date_str.strip()):
            raise ValidationError(
                "Invalid Nepali date. Please enter a valid date between 2070-2090 BS."
            )

        # Parse the date to ensure it's valid
        parsed_date = parse_nepali_date(date_str.strip())
        if not parsed_date:
            raise ValidationError("Unable to parse the provided date.")

        # Check if date is not too far in the future
        try:
            current_nepali = nepali_datetime.date.today()
            if parsed_date > current_nepali:
                raise ValidationError(
                    "Last paid date cannot be in the future."
                )
        except Exception:
            pass  # If current date calculation fails, skip this validation

        return date_str.strip()

    def clean_next_payment_date(self):
        """Validate next payment date"""
        date_str = self.cleaned_data.get('next_payment_date')

        if not date_str:
            raise ValidationError("Next payment date is required.")

        # Basic format validation
        if not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str.strip()):
            raise ValidationError(
                "Date must be in YYYY-MM-DD format (e.g., 2081-04-15)."
            )

        # Use helper function for validation
        if not validate_nepali_date(date_str.strip()):
            raise ValidationError(
                "Invalid Nepali date. Please enter a valid date between 2070-2090 BS."
            )

        # Parse the date to ensure it's valid
        parsed_date = parse_nepali_date(date_str.strip())
        if not parsed_date:
            raise ValidationError("Unable to parse the provided date.")

        return date_str.strip()

    def clean(self):
        """Cross-field validation"""
        cleaned_data = super().clean()
        last_paid = cleaned_data.get('last_paid_date')
        next_payment = cleaned_data.get('next_payment_date')
        reg_type = cleaned_data.get('reg_type')
        category = cleaned_data.get('category')

        # Date range validation
        if last_paid and next_payment:
            try:
                last_paid_parsed = parse_nepali_date(last_paid)
                next_payment_parsed = parse_nepali_date(next_payment)

                if last_paid_parsed and next_payment_parsed:
                    if last_paid >= next_payment:
                        raise ValidationError({
                            'next_payment_date': 'Next payment date must be after last paid date.'
                        })

                    # Check if the date range is reasonable (not more than 10 years)
                    days_diff = (next_payment_parsed.to_datetime_date() -
                                 last_paid_parsed.to_datetime_date()).days

                    if days_diff > 365 * 10:  # 10 years
                        raise ValidationError(
                            'Date range seems too large. Please check your dates.'
                        )

                    if days_diff < 1:
                        raise ValidationError(
                            'Date range is too small. Minimum 1 day difference required.'
                        )

            except Exception as e:
                if "Date range" not in str(e):
                    raise ValidationError('Error validating date range. Please check your dates.')

        # Registration type and category compatibility validation
        if reg_type and category:
            # Check if there are any tax rates defined for this combination
            from .models import TaxRate

            # Check if we have tax rates for this reg_type and category
            tax_rates_exist = TaxRate.objects.filter(
                reg_type=reg_type,
                category=category
            ).exists()

            if not tax_rates_exist:
                raise ValidationError(
                    f'No tax rates are configured for {reg_type.name} vehicles '
                    f'in {category.name} category. Please contact administrator.'
                )

        return cleaned_data

    def get_cc_range(self):
        """Get CC range for selected category and power"""
        if self.is_valid():
            category = self.cleaned_data.get('category')
            cc_power = self.cleaned_data.get('cc_power')

            if category and category.has_cc_range and cc_power:
                return find_cc_range_for_power(category, cc_power)
        return None

    def get_applicable_fiscal_years(self):
        """Get fiscal years that will be affected by this calculation"""
        if self.is_valid():
            from .helper import get_fiscal_years_in_range

            last_paid = parse_nepali_date(self.cleaned_data.get('last_paid_date'))
            next_payment = parse_nepali_date(self.cleaned_data.get('next_payment_date'))

            if last_paid and next_payment:
                return get_fiscal_years_in_range(last_paid, next_payment)
        return []

    def get_calculation_summary(self):
        """Get a summary of what will be calculated"""
        if self.is_valid():
            data = self.cleaned_data
            summary = {
                'reg_type': data['reg_type'].name,
                'category': data['category'].name,
                'cc_power': data.get('cc_power'),
                'cc_range': str(self.get_cc_range()) if self.get_cc_range() else None,
                'date_range': f"{data['last_paid_date']} to {data['next_payment_date']}",
                'fiscal_years': [fy.name for fy in self.get_applicable_fiscal_years()],
                'needs_income_tax': data['reg_type'].needs_income_tax,
                'tax_type': data['reg_type'].tax_type
            }
            return summary
        return None
