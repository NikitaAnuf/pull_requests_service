from dataclasses import dataclass
from datetime import datetime

from utils.properties import Error, PullRequestStatus

@dataclass
class ErrorResponse:
    error: Error

    def __dict__(self):
        return self.error.__dict__()


@dataclass
class TeamMember:
    user_id: str
    username: str
    is_active: bool


@dataclass
class Team:
    team_name: str
    members: list[TeamMember]


@dataclass
class User:
    user_id: str
    username: str
    team_name: str
    is_active: bool


@dataclass
class PullRequest:
    pull_request_id: str
    pull_request_name: str
    author_id: str
    status: PullRequestStatus
    assigned_reviewers: list[str]
    createdAt: datetime | None = None
    mergedAt: datetime | None = None


@dataclass
class PullRequestShort:
    pull_request_id: str
    pull_request_name: str
    author_id: str
    status: PullRequestStatus
