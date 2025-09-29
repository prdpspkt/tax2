import {gql} from "@apollo/client";

const REG_TYPES = gql`query regTypes{
    regTypes {
        id
        name
        nameEn
    }
}`

const PROVINCES = gql`query provinces{
    provinces{
        id
        name
        nameEn
    }
}`

const FISCAL_YEARS = gql`query fiscalYears{
    fiscalYears{
        id
        name
        nameEn
    }
}`

const CATEGORIES = gql`query categories{
    categories{
        id
        name
        nameEn
    }
}`

const CC_RANGE = gql`query ccRange(
    $province: ID!,
    $fiscalYear: ID!,
    $reg_type: ID!,
    $category: ID!
){
    ccRanges(
        province: $province,
        fiscalYear: $fiscalYear,
        regType: $reg_type,
        category: $category
    ){
        id
        name
        fromCc
        toCc
    }
}`