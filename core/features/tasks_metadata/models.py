from pydantic import field_serializer

from core.shared.base.model import BaseModel


class TaskMetaDataInCRUDResponseModel(BaseModel):
    id: int
    owner: str
    owner_timezone: str
    keywords: str
    original_user_input: str
    planning: str
    description: str
    accept_criteria: str

    @field_serializer("keywords")
    def _validator_keywords(self, keywords: str) -> list[str]:
        return keywords.split(",")


class TaskMetaDataCreateModel(BaseModel):
    owner: str
    owner_timezone: str
    keywords: list[str]
    original_user_input: str
    planning: str
    description: str
    accept_criteria: str

    @field_serializer("keywords")
    def _validator_keywords(self, keywords: list[str]) -> str:
        return ",".join(keywords)


class TaskMedataDataUpdateModel(BaseModel):
    keywords: str
    owner_timezone: str
    original_user_input: str
    planning: str
    description: str
    accept_criteria: str

    @field_serializer("keywords")
    def _validator_keywords(self, keywords: str) -> list[str]:
        return keywords.split(",")


class TaskMetaDataInDispatchModel(BaseModel):
    owner: str
    original_user_input: str
    planning: str
    description: str
    accept_criteria: str
