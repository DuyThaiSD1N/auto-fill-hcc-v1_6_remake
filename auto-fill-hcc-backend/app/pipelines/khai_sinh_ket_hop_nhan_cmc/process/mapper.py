"""Variant-specific adapters from shared facts to the two legacy eForms."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from app.pipelines._shared.compact_agent.issuer import default_issuer
from app.pipelines.khai_sinh_thuong.process import mapper as birth_mapper
from app.pipelines.nhan_cha_me_con.process import mapper as recognition_mapper

BIRTH_VARIANT = "birth_registration"
RECOGNITION_VARIANT = "parent_child_recognition"
VALID_VARIANTS = {BIRTH_VARIANT, RECOGNITION_VARIANT}


def _values(fields: list[dict]) -> dict[str, Any]:
    return {item["name"]: item["value"] for item in fields if item.get("value") not in (None, "", {}, [])}


def _fold(value: Any) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text.replace("Đ", "D").replace("đ", "d")).strip().lower()


def _replace(fields: list[dict], name: str, comp: str, value: Any) -> None:
    if value in (None, "", {}, []):
        return
    fields[:] = [item for item in fields if item.get("name") != name]
    fields.append({"name": name, "comp": comp, "value": value})


def _birth_relationship(value: Any) -> str:
    folded = _fold(value)
    if "me" in folded:
        return "MeDe"
    if "cha" in folded or "bo" in folded:
        return "ChaDe"
    return str(value or "").strip()


def _birth_area(value: Any) -> Any:
    return birth_mapper._area(value) if isinstance(value, dict) else value


def map_birth(fields: list[dict]) -> list[dict]:
    values = _values(fields)
    compact = [
        {"name": "Gcs_HoTenCon", "value": values.get("Child_FullName") or values.get("Child_NameOnBirthCertificate")},
        {"name": "Gcs_NgaySinhCon", "value": values.get("Child_BirthDate")},
        {"name": "Gcs_GioiTinhCon", "value": values.get("Child_Gender")},
        {"name": "Gcs_DanTocCon", "value": values.get("Child_Ethnicity")},
        {"name": "Gcs_NoiSinh", "value": values.get("Child_BirthPlaceDomestic")},
        {"name": "CccdNam_HoTen", "value": values.get("Father_FullName")},
        {"name": "CccdNam_SoDinhDanh", "value": values.get("Father_IdNumber")},
        {"name": "CccdNam_NgayCap", "value": values.get("Father_IdIssueDate")},
        {"name": "CccdNam_NoiCap", "value": values.get("Father_IdIssuePlace")},
        {"name": "CccdNam_NgaySinh", "value": values.get("Father_BirthDate")},
        {"name": "CccdNam_DanToc", "value": values.get("Father_Ethnicity")},
        {"name": "CccdNam_QuocTich", "value": values.get("Father_Nationality")},
        {"name": "CccdNam_QueQuan", "value": values.get("Father_OriginDomestic")},
        {"name": "CccdNam_NoiCuTru_TrongNuoc", "value": values.get("Father_ResidenceDomestic")},
        {"name": "CccdNu_HoTen", "value": values.get("Mother_FullName")},
        {"name": "CccdNu_SoDinhDanh", "value": values.get("Mother_IdNumber")},
        {"name": "CccdNu_NgayCap", "value": values.get("Mother_IdIssueDate")},
        {"name": "CccdNu_NoiCap", "value": values.get("Mother_IdIssuePlace")},
        {"name": "CccdNu_NgaySinh", "value": values.get("Mother_BirthDate")},
        {"name": "CccdNu_DanToc", "value": values.get("Mother_Ethnicity")},
        {"name": "CccdNu_QuocTich", "value": values.get("Mother_Nationality")},
        {"name": "CccdNu_NoiCuTru_TrongNuoc", "value": values.get("Mother_ResidenceDomestic")},
    ]
    output = birth_mapper.enrich(compact)

    requester_id = values.get("Requester_IdNumber")
    requester_issue_date = values.get("Requester_IdIssueDate")
    requester_issuer = values.get("Requester_IdIssuePlace") or default_issuer(requester_issue_date)
    _replace(output, "HoVaTenC", "x-input", values.get("Requester_FullName"))
    _replace(output, "SoDinhDanhC", "x-input", requester_id)
    _replace(output, "SoGiayToDinhDanhC", "x-input", requester_id)
    if requester_id:
        _replace(output, "LoaiGiayToDinhDanhC", "x-select", "Căn cước công dân")
    _replace(output, "NgayCapDDC", "x-date", requester_issue_date)
    _replace(output, "NoiCapDDC", "x-input", requester_issuer)
    if values.get("Requester_ResidenceDomestic"):
        _replace(output, "nycLoaiCuTru", "x-select", "Thường trú")
        _replace(output, "nycNoiCuTru", "x-radio", "1")
        _replace(
            output,
            "nycNoiCuTru_TrongNuoc",
            "x-select-area",
            _birth_area(values["Requester_ResidenceDomestic"]),
        )
    _replace(output, "QuanHe", "x-radio", _birth_relationship(values.get("Requester_RelationshipToChild")))
    if values.get("Child_OriginDomestic"):
        _replace(output, "nksQueQuan", "x-radio", "1")
        _replace(
            output,
            "nksQueQuan_TrongNuoc",
            "x-select-area",
            _birth_area(values["Child_OriginDomestic"]),
        )
    _replace(output, "ThongTin", "x-input", values.get("Parents_MarriageRegistrationInfo"))
    return output


def map_recognition(fields: list[dict], options: dict | None = None) -> list[dict]:
    values = _values(fields)
    compact = [
        {"name": "Requester_FullName", "value": values.get("Requester_FullName")},
        {"name": "Requester_BirthDate", "value": values.get("Requester_BirthDate")},
        {"name": "Requester_IdNumber", "value": values.get("Requester_IdNumber")},
        {"name": "Requester_IdIssueDate", "value": values.get("Requester_IdIssueDate")},
        {"name": "Requester_IdIssuePlace", "value": values.get("Requester_IdIssuePlace")},
        {"name": "Requester_ResidenceDomestic", "value": values.get("Requester_ResidenceDomestic")},
        {"name": "Requester_PhoneNumber", "value": values.get("Requester_PhoneNumber")},
        {"name": "Requester_Email", "value": values.get("Requester_Email")},
        {"name": "Requester_RelationshipToRecognized", "value": values.get("Requester_RelationshipToChild")},
        {"name": "Parent_FullName", "value": values.get("Father_FullName")},
        {"name": "Parent_BirthDate", "value": values.get("Father_BirthDate")},
        {"name": "Parent_Gender", "value": values.get("Father_Gender") or "Nam"},
        {"name": "Parent_Ethnicity", "value": values.get("Father_Ethnicity")},
        {"name": "Parent_Nationality", "value": values.get("Father_Nationality")},
        {"name": "Parent_IdNumber", "value": values.get("Father_IdNumber")},
        {"name": "Parent_IdIssueDate", "value": values.get("Father_IdIssueDate")},
        {"name": "Parent_IdIssuePlace", "value": values.get("Father_IdIssuePlace")},
        {"name": "Parent_ResidenceDomestic", "value": values.get("Father_ResidenceDomestic")},
        {"name": "Child_FullName", "value": values.get("Child_FullName") or values.get("Child_NameOnBirthCertificate")},
        {"name": "Child_BirthDate", "value": values.get("Child_BirthDate")},
        {"name": "Child_Gender", "value": values.get("Child_Gender")},
        {"name": "Child_Ethnicity", "value": values.get("Child_Ethnicity")},
        {"name": "Child_Nationality", "value": values.get("Child_Nationality")},
        {"name": "Child_ResidenceDomestic", "value": values.get("Child_ResidenceDomestic") or values.get("Mother_ResidenceDomestic")},
        {"name": "Child_BirthDocumentType", "value": "Giấy chứng sinh" if values.get("Child_BirthDocumentNumber") else None},
        {"name": "Child_BirthDocumentNumber", "value": values.get("Child_BirthDocumentNumber")},
        {"name": "Child_BirthDocumentIssueDate", "value": values.get("Child_BirthDocumentIssueDate")},
        {"name": "Child_BirthDocumentIssuePlace", "value": values.get("Child_BirthDocumentIssuePlace")},
        {"name": "Registration_Agency", "value": values.get("Registration_Agency")},
        {"name": "Registration_Type", "value": values.get("Recognition_RegistrationType")},
        {"name": "Confirmation_Type", "value": values.get("Recognition_ConfirmationType")},
        {"name": "Relationship_Claim", "value": values.get("Recognition_RelationshipClaim")},
        {"name": "CopyRequest_WantsCopy", "value": values.get("Recognition_CopyRequest")},
    ]
    return recognition_mapper.enrich(compact, options)


def enrich(fields: list[dict], variant: str, options: dict | None = None) -> list[dict]:
    if variant == BIRTH_VARIANT:
        return map_birth(fields)
    if variant == RECOGNITION_VARIANT:
        return map_recognition(fields, options)
    return []


def child_name_warning(fields: list[dict]) -> str:
    values = _values(fields)
    intended = values.get("Child_FullName")
    certificate = values.get("Child_NameOnBirthCertificate")
    if intended and certificate and _fold(intended) != _fold(certificate):
        return (
            "Tên trẻ không thống nhất: tờ khai đề nghị "
            f"'{intended}' nhưng giấy chứng sinh ghi '{certificate}'. Đã ưu tiên tên trên tờ khai."
        )
    return ""
