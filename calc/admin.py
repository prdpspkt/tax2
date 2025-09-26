# vehicles/admin.py
from django.contrib import admin
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget

from calc.models import FiscalYear, RegType, Category, CCRange, TaxRate, IncomeTaxRate


# --- Resources ---

class FiscalYearResource(resources.ModelResource):
    class Meta:
        model = FiscalYear
        fields = ('id', 'name', 'name_en', 'start_date', 'end_date')

class RegTypeResource(resources.ModelResource):
    class Meta:
        model = RegType
        fields = ('id', 'name', 'name_en', 'is_ambulance', 'needs_income_tax', 'tax_type')

class CategoryResource(resources.ModelResource):
    class Meta:
        model = Category
        fields = ('id', 'name', 'name_en', 'has_cc_range')

class CCRangeResource(resources.ModelResource):
    category = fields.Field(
        column_name='category',
        attribute='category',
        widget=ForeignKeyWidget(Category, 'id')
    )
    class Meta:
        model = CCRange
        fields = ('id', 'category', 'from_cc', 'to_cc', 'for_income_tax')

class IncomeTaxRateResource(resources.ModelResource):
    category = fields.Field(
        column_name='category',
        attribute='category',
        widget=ForeignKeyWidget(Category, 'id')
    )
    fiscal_year = fields.Field(
        column_name='fiscal_year',
        attribute='fiscal_year',
        widget=ForeignKeyWidget(FiscalYear, 'id')
    )
    cc_range = fields.Field(
        column_name='cc_range',
        attribute='cc_range',
        widget=ForeignKeyWidget(CCRange, 'id')
    )
    class Meta:
        model = IncomeTaxRate
        fields = ('id', 'fiscal_year', 'cc_range', 'income_tax')


class TaxRateResource(resources.ModelResource):
    reg_type = fields.Field(
        column_name='reg_type',
        attribute='reg_type',
        widget=ForeignKeyWidget(RegType, 'id')
    )
    category = fields.Field(
        column_name='category',
        attribute='category',
        widget=ForeignKeyWidget(Category, 'id')
    )
    fiscal_year = fields.Field(
        column_name='fiscal_year',
        attribute='fiscal_year',
        widget=ForeignKeyWidget(FiscalYear, 'id')
    )
    class Meta:
        model = TaxRate
        fields = ('id', 'reg_type', 'category', 'cc_range', 'fiscal_year', 'vehicle_tax', 'renewal_fee', 'tax_type')


# --- Admin ---

@admin.register(FiscalYear)
class FiscalYearAdmin(ImportExportModelAdmin):
    resource_class = FiscalYearResource
    list_display = ('name', 'name_en', 'start_date', 'end_date')

@admin.register(RegType)
class RegTypeAdmin(ImportExportModelAdmin):
    resource_class = RegTypeResource
    list_display = ('name', 'name_en', 'is_ambulance', 'needs_income_tax', 'tax_type')

@admin.register(Category)
class CategoryAdmin(ImportExportModelAdmin):
    resource_class = CategoryResource
    list_display = ('name', 'name_en', 'has_cc_range')

@admin.register(CCRange)
class CCRangeAdmin(ImportExportModelAdmin):
    resource_class = CCRangeResource
    list_display = ('category', 'from_cc', 'to_cc', 'for_income_tax')

@admin.register(TaxRate)
class TaxRateAdmin(ImportExportModelAdmin):
    resource_class = TaxRateResource
    list_display = ('reg_type', 'category', 'cc_range', 'fiscal_year', 'vehicle_tax', 'renewal_fee', 'tax_type')

@admin.register(IncomeTaxRate)
class IncomeTaxAdmin(ImportExportModelAdmin):
    resource_class = IncomeTaxRateResource
    list_display = ('fiscal_year', 'category', 'cc_range', 'income_tax')