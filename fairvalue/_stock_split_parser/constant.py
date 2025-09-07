import re

DEFAULT_KEYWORDS = [
    r"stock split",
    r"share split",
    r"reverse stock split",
    r"reverse split",
    r"forward split",
    r"stock dividend",
    r"share dividend",
]

RATIO_PATTERNS = [
    re.compile(r"\b(\d+)\s*(?:for|:|to|-)\s*(\d+)\b", re.I),
    re.compile(r"\b(\d+)\s*[-–—]\s*(\d+)\b", re.I),
]


MONTHS = (
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
    "jan",
    "feb",
    "mar",
    "apr",
    "may",
    "jun",
    "jul",
    "aug",
    "sep",
    "oct",
    "nov",
    "dec",
)

DATE_PATTERNS = [
    # March 15, 2024
    re.compile(rf"\b({'|'.join(MONTHS)})\s+\d{{1,2}},?\s+\d{{4}}\b", re.I),
    # 15 March 2024
    re.compile(rf"\b\d{{1,2}}\s+({'|'.join(MONTHS)})\s+\d{{4}}\b", re.I),
    # 2024-03-15
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),
    # 03/15/2024 or 3/15/2024
    re.compile(r"\b\d{1,2}/\d{1,2}/\d{4}\b"),
]

DATE_HINTS = [
    re.compile(
        r"\b(effective|effectiveness|record|payable|distribution|implementation)\b",
        re.I,
    )
]
