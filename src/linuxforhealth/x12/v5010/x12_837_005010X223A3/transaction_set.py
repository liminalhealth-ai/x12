"""
transaction_set.py

Defines the Institutional Claims 837 005010X223A3 transaction set model.
"""

from linuxforhealth.x12.models import X12SegmentGroup
from .loops import Header, Footer, Loop1000A, Loop1000B, Loop2000A
from pydantic import Field, model_validator
from typing import List
from linuxforhealth.x12.validators import validate_segment_count


class HealthCareClaimInstitutional(X12SegmentGroup):
    """
    The HealthCare Claim - Institutional transaction model (837)
    """

    header: Header
    loop_1000a: Loop1000A
    loop_1000b: Loop1000B
    loop_2000a: List[Loop2000A] = Field(min_length=1)
    footer: Footer

    # _validate_segment_count = model_validator(mode="after")(validate_segment_count)
