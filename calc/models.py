from django.db import models

class Province(models.Model):
    name = models.CharField(max_length=100)
    name_en = models.CharField(max_length=100)
    def __str__(self):
        return self.name

class FiscalYear(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    name_en = models.CharField(max_length=100, unique=True)
    start_date = models.DateField()
    end_date = models.DateField()
    income_tax_due_date = models.DateField()
    vehicle_tax_due_date = models.DateField()
    previous = models.OneToOneField(
        'self',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='next'
    )
    def __str__(self):
        return self.name

class RegType(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    name_en = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name

class RegRule(models.Model):
    id = models.AutoField(primary_key=True)
    regtype = models.ForeignKey(RegType, on_delete=models.PROTECT)
    tax_exempted = models.BooleanField(default=False)
    renewal_exempted = models.BooleanField(default=False)
    income_tax_exempted = models.BooleanField(default=False)
    province = models.ForeignKey(Province, on_delete=models.PROTECT)
    fiscal_year = models.ForeignKey('FiscalYear', on_delete=models.PROTECT)


class Category(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    name_en = models.CharField(max_length=100, unique=True)
    has_cc_range = models.BooleanField(default=False, verbose_name="Has CC/Watt range?")
    reg_type = models.ForeignKey(RegType, on_delete=models.PROTECT, null=True)
    province = models.ForeignKey(Province, on_delete=models.PROTECT, null=True)
    fiscal_year = models.ForeignKey(FiscalYear, on_delete=models.PROTECT, null=True)


    def __str__(self):
        return self.name

class CCRange(models.Model):
    id = models.AutoField(primary_key=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    from_cc = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="From CC/W/KW")
    to_cc = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="To CC/W/KW")
    for_income_tax = models.BooleanField(default=False)
    province = models.ForeignKey(Province, on_delete=models.PROTECT)
    fiscal_year = models.ForeignKey('FiscalYear', on_delete=models.PROTECT)

    def __str__(self):
        return f"{self.category.name} ({self.from_cc} - {self.to_cc})"

class TaxRate(models.Model):
    id = models.AutoField(primary_key=True)
    reg_type = models.ForeignKey(RegType, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    cc_range = models.ForeignKey(CCRange, on_delete=models.CASCADE, blank=True, null=True)
    fiscal_year = models.ForeignKey(FiscalYear, on_delete=models.CASCADE)
    vehicle_tax = models.DecimalField(max_digits=10, decimal_places=2)
    renewal_fee = models.DecimalField(max_digits=10, decimal_places=2)
    province = models.ForeignKey(Province, on_delete=models.PROTECT)

    def __str__(self):
        return f"{self.category.name} ({self.fiscal_year} - {self.cc_range})"


class IncomeTaxRate(models.Model):
    id = models.AutoField(primary_key=True)
    reg_type = models.ForeignKey(RegType, on_delete=models.CASCADE)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    cc_range = models.ForeignKey(CCRange, on_delete=models.CASCADE, blank=True, null=True)
    fiscal_year = models.ForeignKey(FiscalYear, on_delete=models.CASCADE)
    income_tax = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.category.name} ({self.fiscal_year} - {self.cc_range})"
