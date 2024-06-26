"""
models.py

Base models for X12 parsing and validation.
"""
import abc
import datetime
from copy import deepcopy
from enum import Enum
from typing import List, Optional
from decimal import Decimal

from pydantic import BaseModel, Field, validator


class X12Delimiters(BaseModel):
    """
    X12Delimiters models the message delimiters used within a X12 transaction.
    """

    element_separator: str = Field("*", min_length=1, max_length=1)
    repetition_separator: str = Field("^", min_length=1, max_length=1)
    segment_terminator: str = Field("~", min_length=1, max_length=1)
    component_separator: str = Field(":", min_length=1, max_length=1)

    class Config:
        # the model is immutable and hashable
        allow_mutation = False
        frozen = True


class X12SegmentName(str, Enum):
    """
    Supported X12 Segment Names
    """

    AAA = "AAA"
    ACT = "ACT"
    AMT = "AMT"
    BGN = "BGN"
    BHT = "BHT"
    BPR = "BPR"
    CAS = "CAS"
    CLM = "CLM"
    CLP = "CLP"
    CL1 = "CL1"
    CN1 = "CN1"
    COB = "COB"
    CR1 = "CR1"
    CR2 = "CR2"
    CR3 = "CR3"
    CR5 = "CR5"
    CR6 = "CR6"
    CR7 = "CR7"
    CRC = "CRC"
    CTP = "CTP"
    CUR = "CUR"
    DMG = "DMG"
    DSB = "DSB"
    DTM = "DTM"
    DTP = "DTP"
    EB = "EB"
    EC = "EC"
    EQ = "EQ"
    FRM = "FRM"
    GE = "GE"
    GS = "GS"
    HCP = "HCP"
    HD = "HD"
    HI = "HI"
    HL = "HL"
    HLH = "HLH"
    HSD = "HSD"
    ICM = "ICM"
    IDC = "IDC"
    IEA = "IEA"
    III = "III"
    INS = "INS"
    ISA = "ISA"
    K3 = "K3"
    LE = "LE"
    LIN = "LIN"
    LUI = "LUI"
    LQ = "LQ"
    LS = "LS"
    LX = "LX"
    MEA = "MEA"
    MIA = "MIA"
    MOA = "MOA"
    MPI = "MPI"
    MSG = "MSG"
    N1 = "N1"
    N3 = "N3"
    N4 = "N4"
    NM1 = "NM1"
    NTE = "NTE"
    OI = "OI"
    PAT = "PAT"
    PER = "PER"
    PLA = "PLA"
    PLB = "PLB"
    PRV = "PRV"
    PS1 = "PS1"
    PWK = "PWK"
    QTY = "QTY"
    RDM = "RDM"
    REF = "REF"
    SBR = "SBR"
    SE = "SE"
    ST = "ST"
    STC = "STC"
    SVC = "SVC"
    SV1 = "SV1"
    SV2 = "SV2"
    SV5 = "SV5"
    SVD = "SVD"
    TRN = "TRN"
    TS2 = "TS2"
    TS3 = "TS3"


class X12Segment(abc.ABC, BaseModel):
    """
    X12BaseSegment serves as the abstract base class for all X12 segment models.
    """

    delimiters: Optional[X12Delimiters] = None
    segment_name: X12SegmentName
    

    @classmethod
    def unvalidated(__pydantic_cls__, **data):
        for name, field in __pydantic_cls__.__fields__.items():
            try:
                data[name]
            except KeyError:
                if field.required:
                    raise TypeError(f"Missing required keyword argument {name!r}")
                if field.default is None:
                    # deepcopy is quite slow on None
                    value = None
                else:
                    value = deepcopy(field.default)
                data[name] = value
        self = __pydantic_cls__.__new__(__pydantic_cls__)
        object.__setattr__(self, "__dict__", data)
        object.__setattr__(self, "__fields_set__", set(data.keys()))
        return self
    
    class Config:
        """
        Default configuration for X12 Models
        """
        use_enum_values = True
        extra = "forbid"
        
    def _process_multivalue_field(
        self,
        field_name: str,
        field_value: List,
        custom_delimiters: X12Delimiters = None,
    ) -> str:
        """
        Converts a X12 multi-value (list) field into a a single delimited string.

        A "multi-value" field is a field which contains sub-fields, or components, or allows repeats.
        The X12 specification uses separate delimiters for component and repeating fields.

        By default the method will use default X12 delimiters. Custom delimiters may be specified if desired using
        the `custom_delimiters` parameter.

        :param field_name: The field name used to lookup field metadata.
        :param field_value: The field's list values
        :param custom_delimiters: Used when custom delimiters are required. Defaults to None.
        """

        delimiters = custom_delimiters or X12Delimiters()
        is_component_field: bool = self.__fields__[field_name].field_info.extra.get(
            "is_component", False
        )
        if is_component_field:
            join_character = delimiters.component_separator
        else:
            join_character = delimiters.repetition_separator
        return join_character.join(field_value)

    def x12(self, custom_delimiters: X12Delimiters = None) -> str:
        """
        Generates a X12 formatted string for the segment.
        By default, the method will use default X12 delimiters. Custom delimiters may be specified if desired using
        the `custom_delimiters` parameter.

        :param custom_delimiters: Used when custom delimiters are required. Defaults to None.
        :return: the X12 representation of the model instance
        """

        delimiters = custom_delimiters or X12Delimiters()
        x12_values = []
        for k, v in self.dict(exclude={"delimiters"}).items():
            if isinstance(v, str):
                x12_values.append(v)
            elif isinstance(v, list):
                x12_values.append(
                    self._process_multivalue_field(k, v, custom_delimiters=delimiters)
                )
            elif isinstance(v, datetime.datetime):
                x12_values.append(v.strftime("%Y%m%d%H%M"))
            elif isinstance(v, datetime.date):
                x12_values.append(v.strftime("%Y%m%d"))
            elif isinstance(v, datetime.time):
                x12_values.append(v.strftime("%H%M"))
            elif isinstance(v, Decimal):
                x12_values.append("{:.2f}".format(v))
            elif v is None:
                x12_values.append("")
            else:
                x12_values.append(str(v))

        x12_str = delimiters.element_separator.join(x12_values).rstrip(
            delimiters.element_separator
        )
        return x12_str + delimiters.segment_terminator


class X12SegmentGroup(abc.ABC, BaseModel):
    """
    Abstract base class for a container, typically a loop or transaction, which groups x12 segments.
    """

    @classmethod
    def unvalidated(__pydantic_cls__, **data):
        for name, field in __pydantic_cls__.__fields__.items():
            try:
                data[name]
            except KeyError:
                if field.required:
                    raise TypeError(f"Missing required keyword argument {name!r}")
                if field.default is None:
                    # deepcopy is quite slow on None
                    value = None
                else:
                    value = deepcopy(field.default)
                data[name] = value
        self = __pydantic_cls__.__new__(__pydantic_cls__)
        object.__setattr__(self, "__dict__", data)
        object.__setattr__(self, "__fields_set__", set(data.keys()))
        return self

    def x12(
        self, use_new_lines: bool = True, custom_delimiters: X12Delimiters = None
    ) -> str:
        """
        Generates a X12 formatted string for the segment.

        By default the method will use default X12 delimiters. Custom delimiters may be specified if desired using
        the `custom_delimiters` parameter.

        :param use_new_lines: Indicates if the X12 output includes newline characters. Defaults to True.
        :param custom_delimiters: Used when custom delimiters are required. Defaults to None.
        :return: Generates a X12 representation of the loop using its segments.
        """
        delimiters = custom_delimiters or X12Delimiters()
        x12_segments: List[str] = []
        fields = [f for f in self.__fields__.values() if hasattr(f.type_, "x12")]

        for f in fields:
            field_instance = getattr(self, f.name)

            if field_instance is None:
                continue
            elif isinstance(field_instance, list):
                for item in field_instance:
                    if isinstance(item, X12Segment):
                        x12_segments.append(item.x12(custom_delimiters=delimiters))
                    else:
                        x12_segments.append(
                            item.x12(
                                use_new_lines=use_new_lines,
                                custom_delimiters=delimiters,
                            )
                        )
            else:
                if isinstance(field_instance, X12Segment):
                    x12_segments.append(
                        field_instance.x12(custom_delimiters=delimiters)
                    )
                else:
                    x12_segments.append(
                        field_instance.x12(
                            use_new_lines=use_new_lines, custom_delimiters=delimiters
                        )
                    )

        join_char: str = "\n" if use_new_lines else ""
        return join_char.join(x12_segments)
