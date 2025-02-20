from typing import (
    List,
    Optional,
)

import numpy as np
from pydantic import (
    BaseModel,
    Field,
    field_validator,
)


class Floats(BaseModel):

    data: List[float] = Field(..., description="A list of float values.")

    def __getitem__(self, index):
        return self.data[index]

    def __iter__(self):
        return iter(self.data)

    def __len__(self):
        return len(self.data)

    def __add__(self, other):
        if isinstance(other, (list, Floats)):
            return Floats(data=self.data + list(other))
        raise TypeError("Can only add a list or another Floats object.")

    def sum(
        self,
    ) -> float:
        return sum(self.data)


class NonNegFloats(Floats):

    @field_validator("data")
    def check_non_negative(cls, values: List[Optional[float]]):
        for value in values:
            if value is not None and not np.isnan(value) and value < 0:
                raise ValueError(
                    f"All values must be non-negative floats, None, or np.nan. Got {type(value)}"
                )
        return values


class Ints(BaseModel):

    data: List[int] = Field(..., description="A list of int values.")

    def __getitem__(self, index):
        return self.data[index]

    def __iter__(self):
        return iter(self.data)

    def __len__(self):
        return len(self.data)

    def __add__(self, other):
        if isinstance(other, (list, Ints)):
            return Ints(data=self.data + list(other))
        raise TypeError("Can only add a list or another Ints object.")

    def sum(self) -> float:
        return sum(self.data)


class NonNegInts(Ints):

    @field_validator("data")
    def check_non_negative(cls, values: List[int]):
        if any(value < 0 for value in values):
            raise ValueError("All values must be non-negative floats.")
        return values


class Strs(BaseModel):

    data: List[str] = Field(..., description="A list of str values.")

    def __getitem__(self, index):
        return self.data[index]

    def __iter__(self):
        return iter(self.data)

    def __len__(self):
        return len(self.data)

    def __add__(self, other):
        if isinstance(other, (list, Strs)):
            return Strs(data=self.data + list(other))
        raise TypeError("Can only add a list or another Strs object.")
