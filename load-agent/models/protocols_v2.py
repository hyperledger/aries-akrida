from typing import Any

from pydantic import BaseModel, Field


class BaseModel(BaseModel):
    def model_dump(self, **kwargs) -> dict[str, Any]:
        return super().model_dump(by_alias=True, exclude_none=True, **kwargs)


class CredentialPreview(BaseModel):
    type: str = Field("issue-credential/2.0/credential-preview", alias="@type")
    attributes: list = Field()


class Filter(BaseModel):
    cred_def_id: str = Field()
    schema_id: str | None = Field(None)


class AnonCredsFilter(BaseModel):
    anoncreds: Filter = Field()


class IndyFilter(BaseModel):
    indy: Filter = Field()


class IssueCredential(BaseModel):
    auto_issue: bool = Field(True)
    connection_id: str = Field()
    credential_preview: CredentialPreview = Field()
    filter: AnonCredsFilter | IndyFilter = Field()


class ProofRequest(BaseModel):
    name: str = Field()
    requested_attributes: dict = Field()
    requested_predicates: dict = Field()
    version: str = Field()


class AnonCredsPresReq(BaseModel):
    anoncreds: ProofRequest = Field()


class DifPresReq(BaseModel):
    dif: dict = Field()


class IndyPresReq(BaseModel):
    indy: ProofRequest = Field()


class RequestPresentation(BaseModel):
    auto_verify: bool = Field(False)
    auto_remove: bool = Field(False)
    connection_id: str = Field(None)
    presentation_request: AnonCredsPresReq | DifPresReq | IndyPresReq = Field()
