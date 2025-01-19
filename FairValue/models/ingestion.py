from pydantic import BaseModel, Field, field_validator, validator
from typing import List, Optional, Union
from FairValue.models.utils import validate_date


class Datum(BaseModel):

    end: str  # Must be a valid date
    val: int
    accn: Optional[str] = None
    fy: Optional[int] = None
    fp: Optional[str] = None
    form: str
    filed: str  # Must be a valid date
    frame: Optional[str] = None

    # Validator for 'end' field
    @validator("end", pre=True, always=True)
    def validate_end(cls, value):
        return validate_date("end", value)

    # Validator for 'filed' field
    @validator("filed", pre=True, always=True)
    def validate_filed(cls, value):
        return validate_date("filed", value)


class Shares(BaseModel):

    shares: List[Datum]

    @field_validator("shares", mode="before")
    def validate_currency_data(cls, value):
        if not value or len(value) == 0:
            raise ValueError(
                "The 'shares' field must contain at least one entry."
            )
        return value


class USD(BaseModel):

    USD: List[Datum]

    @field_validator("USD", mode="before")
    def validate_currency_data(cls, value):
        if not value or len(value) == 0:
            raise ValueError(
                "The 'USD' field must contain at least one entry."
            )
        return value


class CommonStockSharesOutstanding(BaseModel):

    label: str

    description: str

    units: Shares


class sharesOutstanding(BaseModel):

    label: str

    description: str

    units: Shares


class PublicFloat(BaseModel):

    label: str

    description: str

    units: USD


class Dei(BaseModel):

    EntityCommonStockSharesOutstanding: CommonStockSharesOutstanding

    EntityPublicFloat: Optional[PublicFloat] = None

    model_config = {"extra": "allow"}  # Allows additional fields


class NetOpsCash(BaseModel):

    label: str

    description: str

    units: USD


class CapEx(BaseModel):

    label: str
    description: str
    units: USD


class USGaap(BaseModel):

    NetCashProvidedByUsedInOperatingActivities: NetOpsCash

    PaymentsToAcquirePropertyPlantAndEquipment: Optional[CapEx] = None

    model_config = {"extra": "allow"}  # Allows additional fields


class Facts(BaseModel):

    dei: Dei

    us_gaap: USGaap = Field(alias="us-gaap")


class CompanyFacts(BaseModel):

    cik: Union[str, int]

    entityName: str

    facts: Facts
