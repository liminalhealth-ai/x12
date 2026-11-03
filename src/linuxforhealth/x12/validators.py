"""
validators.py

The validator functions in this module are reused across loops within a X12 transaction model.

Model validators run "after" field validation and have the signature (self).

Field validators have the signature (cls, v, info), where info.data holds the previously
validated fields (dict).
"""
from typing import Union
from collections import defaultdict
from datetime import datetime

from pydantic import BaseModel, ValidationInfo

from .support import parse_x12_date, count_segments


def _validate_duplicate_codes(model: BaseModel, segment_name: str, code_field: str):
    """
    Validates duplicate code values for repeating segments.

    Example: Some transactional loops support multiple date, DTP, segments. For these cases this validation ensures
    that the date_time_qualifier is unique within the loop for the repeating segments.

    Given _validate_duplicate_codes(model, "amt_segment", "amount_qualifier_code"), the following segments are valid:
    AMT*D*411~
    AMT*A8*420~

    The following segments are invalid due to duplicate codes
    AMT*D*411~
    AMT*D*411~
    """
    codes = defaultdict(int)
    for segment in getattr(model, segment_name, []):
        # account for differing internal representation: model vs dict
        if not isinstance(segment, dict):
            segment = segment.model_dump()

        code = segment.get(code_field)
        codes[code] += 1

    duplicate_codes = {k for k, v in codes.items() if v > 1}
    if duplicate_codes:
        raise ValueError(
            f"Duplicate {segment_name}.{code_field} codes {duplicate_codes}"
        )
    return model


def validate_duplicate_ref_codes(self):
    """
    Validates that a loop does not contain duplicate REF codes.

    :raises: ValueError if duplicate REF codes are found.
    """
    return _validate_duplicate_codes(
        self, "ref_segment", "reference_identification_qualifier"
    )


def validate_duplicate_amt_codes(self):
    """
    Validates that a loop does not contain duplicate REF codes.

    :raises: ValueError if duplicate REF codes are found.
    """
    return _validate_duplicate_codes(self, "amt_segment", "amount_qualifier_code")


def validate_duplicate_date_qualifiers(self):
    """
    Validates that a loop does not contain duplicate DTP date qualifiers.

    :raises: ValueError if duplicate DTP date qualifiers are found.
    """
    return _validate_duplicate_codes(self, "dtp_segment", "date_time_qualifier")


def validate_date_field(
    cls, v, info: ValidationInfo
) -> Union[datetime.date, str, None]:
    """
    Validates a date field using the segment's date_time_period_format_qualifier (D8 or RD8).
    The date_time_period_format_qualifier is used to indicate if a date field is a specific date or a date range.
    Specific dates are have a "D8" qualifier value, while date ranges are qualified using "RD8".

    :param v: The date field value
    :param info: Validation info; info.data holds the segment's valid values.
    :return: The validated date field value
    :raises: ValueError if the date field value is an invalid format.
    """
    from linuxforhealth.x12.v5010.segments import DtpSegment

    def handle_x12_date(date_string: str):
        """Parses a x12 date string, raising a ValueError if an error occurs"""
        try:
            return parse_x12_date(date_string)
        except ValueError:
            raise ValueError(f"Invalid date value {date_string}")

    qualifier = info.data.get("date_time_period_format_qualifier")

    # the date field may be "optional" in which case the qualifier is not present
    # if the qualifier field is required, it will be validated at the field level
    if not qualifier:
        return v

    if (
        qualifier == DtpSegment.DateTimePeriodFormatQualifier.DATE_RANGE
        and "-" not in v
    ):
        raise ValueError(f"Invalid date range {v}")
    elif qualifier == DtpSegment.DateTimePeriodFormatQualifier.DATE_RANGE:
        for d in v.split("-"):
            handle_x12_date(d)
        return v
    else:
        return handle_x12_date(v)


def validate_segment_count(self):
    """
    Validates the segment count conveyed in the transaction set footer, or SE segment.
    This function is only able to count "valid" segments since it is invoked as a "post" validator.
    """
    expected_count: int = self.footer.se_segment.transaction_segment_count

    if not expected_count:
        raise ValueError("Expected transaction count not found in SE segment")

    actual_count: int = count_segments(dict(self))

    if expected_count != actual_count:
        raise ValueError(
            f"SE segment count {expected_count} != actual count {actual_count}"
        )

    return self
