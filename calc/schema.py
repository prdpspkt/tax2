import graphene
from graphene_django.types import DjangoObjectType

from calc.models import RegType, Province, FiscalYear, Category, CCRange


class CategoryType(DjangoObjectType):
    class Meta:
        model = Category
        fields = ('id', 'name', 'name_en', 'has_cc_range')


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


class CCRangeType(DjangoObjectType):
    name = graphene.String()

    def resolve_name(self, info, **kwargs):
        return f"{self.from_cc}-{self.to_cc}"

    class Meta:
        model = CCRange
        fields = ("id", "province", "reg_type", "category", "fiscal_year", "name", "from_cc", "to_cc")


class Query(graphene.ObjectType):
    provinces = graphene.List(ProvinceType)
    reg_types = graphene.List(RegTypeType)
    fiscal_years = graphene.List(FiscalYearType)
    categories = graphene.List(CategoryType)
    cc_ranges = graphene.List(CCRangeType,
                              province=graphene.ID(required=True),
                              fiscal_year=graphene.ID(required=True),
                              category=graphene.ID(required=True),
                              reg_type=graphene.ID(required=True)
                              )

    @staticmethod
    def resolve_provinces(root, info, **kwargs):
        return Province.objects.all()

    @staticmethod
    def resolve_reg_types(root, info, **kwargs):
        return RegType.objects.all()

    @staticmethod
    def resolve_fiscal_years(root, info, **kwargs):
        return FiscalYear.objects.all()

    @staticmethod
    def resolve_categories(root, info, **kwargs):
        return Category.objects.all()

    @staticmethod
    def resolve_cc_ranges(root, info, province, fiscal_year, category, reg_type):
        return CCRange.objects.filter(
            province=province,
            fiscal_year=fiscal_year,
            category=category,
            reg_type=reg_type
        )


# Define schema
schema = graphene.Schema(query=Query)
