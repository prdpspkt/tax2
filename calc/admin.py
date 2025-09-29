# vehicles/admin.py
from django.contrib import admin
from import_export import resources, fields
from import_export.admin import ImportExportModelAdmin
from import_export.widgets import ForeignKeyWidget

from calc.models import FiscalYear, RegType, Category, CCRange, TaxRate, RegRule, Province

# --- Resources ---

class ProvinceResource(resources.ModelResource):
    class Meta:
        model = Province
        fields = ('name', 'name_en')


class FiscalYearResource(resources.ModelResource):
    class Meta:
        model = FiscalYear
        fields = ('id', 'name', 'name_en', 'start_date', 'end_date', 'previous')


class RegTypeResource(resources.ModelResource):
    class Meta:
        model = RegType
        fields = ("id", "name", "name_en")


class RegRuleResource(resources.ModelResource):
    class Meta:
        model = RegRule
        fields = (
            "id",
            "province"
            "fiscal_year",
            "regtype__name",
            "tax_exempted",
            "renewal_exempted",
            "income_tax_exempted",
        )


class CategoryResource(resources.ModelResource):
    class Meta:
        model = Category
        fields = ('id', 'name', 'name_en', 'has_cc_range')


class CCRangeResource(resources.ModelResource):
    province = fields.Field(column_name='province', attribute='province', widget=ForeignKeyWidget(Province, 'name'))
    fiscal_year = fields.Field(column_name='fiscal_year', attribute='fiscal_year', widget=ForeignKeyWidget(FiscalYear, 'name'))
    category = fields.Field(
        column_name='category',
        attribute='category',
        widget=ForeignKeyWidget(Category, 'name')
    )

    class Meta:
        model = CCRange
        fields = ('id', 'province', 'fiscal_year', 'category', 'from_cc', 'to_cc', 'for_income_tax')


class TaxRateResource(resources.ModelResource):
    reg_type = fields.Field(
        column_name='reg_type',
        attribute='reg_type',
        widget=ForeignKeyWidget(RegType, 'name')
    )
    category = fields.Field(
        column_name='category',
        attribute='category',
        widget=ForeignKeyWidget(Category, 'name')
    )
    fiscal_year = fields.Field(
        column_name='fiscal_year',
        attribute='fiscal_year',
        widget=ForeignKeyWidget(FiscalYear, 'name')
    )

    class Meta:
        model = TaxRate
        fields = ('id', 'province', 'fiscal_year', 'reg_type', 'category', 'cc_range', 'fiscal_year', 'vehicle_tax', 'renewal_fee')


# --- Admin ---
@admin.register(Province)
class ProvinceAdmin(ImportExportModelAdmin):
    resource_class = ProvinceResource
    list_display = ('id', 'name', 'name_en')


@admin.register(FiscalYear)
class FiscalYearAdmin(ImportExportModelAdmin):
    resource_class = FiscalYearResource
    list_display = ('name', 'name_en', 'start_date', 'end_date', 'previous')


# --- Inline for RegRule ---
class RegRuleInline(admin.TabularInline):  # or StackedInline for full form
    model = RegRule
    extra = 1


# --- Admin for RegType ---
@admin.register(RegType)
class RegTypeAdmin(ImportExportModelAdmin):
    resource_class = RegTypeResource
    inlines = [RegRuleInline]
    list_display = ("id", "name", "name_en")
    search_fields = ("name", "name_en")


@admin.register(RegRule)
class RegRuleAdmin(ImportExportModelAdmin):
    resource_class = RegRuleResource
    list_display = (
        "id",
        "province",
        "fiscal_year",
        "regtype",
        "tax_exempted",
        "renewal_exempted",
        "income_tax_exempted",
    )
    list_filter = ("tax_exempted", "renewal_exempted", "income_tax_exempted")
    search_fields = ("regtype__name",)


@admin.register(Category)
class CategoryAdmin(ImportExportModelAdmin):
    resource_class = CategoryResource
    list_display = ('name', 'name_en', 'has_cc_range')


@admin.register(CCRange)
class CCRangeAdmin(ImportExportModelAdmin):
    resource_class = CCRangeResource
    list_display = ('province', 'fiscal_year', 'category', 'from_cc', 'to_cc', 'for_income_tax')


@admin.register(TaxRate)
class TaxRateAdmin(ImportExportModelAdmin):
    resource_class = TaxRateResource
    list_display = ('province', 'fiscal_year', 'reg_type', 'category', 'cc_range', 'private_tax', 'public_tax', 'private_renewal', 'public_renewal')
