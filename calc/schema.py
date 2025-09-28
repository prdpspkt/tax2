import graphene
from graphene_django.types import DjangoObjectType

from calc.models import RegType, Province, FiscalYear, Category


class CategoryType(DjangoObjectType):
    class Meta:
        model = Category
        fields = ('id', 'name', 'name_en', 'has_cc_range', 'province', 'reg_type', 'fiscal_year')


class RegTypeType(DjangoObjectType):
    categories = graphene.List(CategoryType)

    def resolve_categories(self, info, **kwargs):
        return Category.objects.filter(reg_type=self)

    class Meta:
        model = RegType
        fields = ("id", "name", "name_en")


class ProvinceType(DjangoObjectType):
    class Meta:
        model = Province
        fields = ("id", "name", "name_en")


class FiscalYearType(DjangoObjectType):
    class Meta:
        model = FiscalYear
        fields = ("id", "name", "name_en")


class CategoryType(DjangoObjectType):
    class Meta:
        model = Category
        fields = ("id", "name", "name_en", "has_cc_range")


class Query(graphene.ObjectType):
    provinces = graphene.List(ProvinceType)
    reg_types = graphene.List(RegTypeType)
    fiscal_years = graphene.List(FiscalYearType)

    def resolve_provinces(self, info, **kwargs):
        return Province.objects.all()

    def resolve_reg_types(self, info, **kwargs):
        return RegType.objects.all()

    def resolve_fiscal_years(self, info, **kwargs):
        return FiscalYear.objects.all()


# Define schema
schema = graphene.Schema(query=Query)
