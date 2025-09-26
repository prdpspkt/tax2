from django.db import models

class FiscalYear(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    name_en = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()

    def __str__(self):
        return self.name

class RegType(models.Model):
    TAX_TYPE_MATCHES_WITH = (
        ("PRIVATE", "PRIVATE"),
        ("PUBLIC", "PUBLIC"),
        ("FREE", "FREE"),
        ("RENEW_ONLY", "RENEW_ONLY"),
    )
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    name_en = models.CharField(max_length=100)
    is_ambulance = models.BooleanField(default=False)
    needs_income_tax = models.BooleanField(default=False)
    tax_type =models.CharField(max_length=100, choices=TAX_TYPE_MATCHES_WITH, default="PRIVATE")

    def __str__(self):
        return self.name

class Category(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    name_en = models.CharField(max_length=100)
    has_cc_range = models.BooleanField(default=False, verbose_name="Has CC/Watt range?")

    def __str__(self):
        return self.name

class CCRange(models.Model):
    id = models.AutoField(primary_key=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    from_cc = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="From CC/W/KW")
    to_cc = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="To CC/W/KW")
    for_income_tax = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.category.name} ({self.from_cc} - {self.to_cc})"

class TaxRate(models.Model):
    TAX_TYPE_MATCHES_WITH = (
        ("PRIVATE", "PRIVATE"),
        ("PUBLIC", "PUBLIC"),
        ("FREE", "FREE"),
        ("RENEW_ONLY", "RENEW_ONLY"),
    )
    id = models.AutoField(primary_key=True)
    tax_type = models.CharField(max_length=100, choices=TAX_TYPE_MATCHES_WITH, default="PRIVATE")
    reg_type = models.ForeignKey(RegType, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    cc_range = models.ForeignKey(CCRange, on_delete=models.CASCADE, blank=True, null=True)
    fiscal_year = models.ForeignKey(FiscalYear, on_delete=models.CASCADE)
    vehicle_tax = models.DecimalField(max_digits=10, decimal_places=2)
    renewal_fee = models.DecimalField(max_digits=10, decimal_places=2)

class IncomeTaxRate(models.Model):
    id = models.AutoField(primary_key=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    fiscal_year = models.ForeignKey(FiscalYear, on_delete=models.CASCADE)
    income_tax = models.DecimalField(max_digits=10, decimal_places=2)
    cc_range = models.ForeignKey(CCRange, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
       if self.cc_range is None:
           return f"{self.category.name}"
       else:
           return f"{self.cc_range.category.name} ({self.cc_range.from_cc} - {self.cc_range.to_cc})"

