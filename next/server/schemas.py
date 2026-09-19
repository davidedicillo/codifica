from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Mutation(Model):
    requestId: UUID


class Login(Model):
    email: str = Field(min_length=3, max_length=254)
    name: str = Field(min_length=1, max_length=100)


class ChannelCreate(Model):
    name: str = Field(min_length=1, max_length=100)


class ChannelPatch(Model):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    archived: bool | None = None
    ownerId: str | None = None


class InviteCreate(Model):
    kind: Literal["human", "agent"]
    email: str | None = Field(default=None, max_length=254)


class ParticipantPatch(Model):
    name: str = Field(min_length=1, max_length=100)


class Join(Mutation):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    provider: str | None = Field(default=None, max_length=100)


class DocRef(Model):
    docId: str
    revision: int | None = Field(default=None, ge=1)
    title: str | None = None
    startLine: int | None = Field(default=None, ge=1)
    endLine: int | None = Field(default=None, ge=1)


class MessageCreate(Mutation):
    body: str = Field(max_length=16384)
    rootMessageId: str | None = Field(default=None, min_length=1)
    mentions: list[str] = Field(default_factory=list, max_length=20)
    docRefs: list[DocRef] = Field(default_factory=list, max_length=20)


class Subscription(Model):
    following: bool


class DocCreate(Mutation):
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(max_length=262144)


class DocPatch(DocCreate):
    expectedRevision: int = Field(ge=1)


class DocUpload(Mutation):
    filename: str = Field(min_length=1, max_length=200)
    data: str = Field(max_length=6990508)
