from dataclasses import dataclass
from enum import Enum


class ErrorCodes(Enum):
    TEAM_EXISTS = 'TEAM_EXISTS'
    PR_EXISTS = 'PR_EXISTS'
    PR_MERGED = 'PR_MERGED'
    NOT_ASSIGNED = 'NOT_ASSIGNED'
    NO_CANDIDATE = 'NO_CANDIDATE'
    NOT_FOUND = 'NOT_FOUND'
    SERVER_ERROR = 'SERVER_ERROR'


@dataclass
class Error:
    code: ErrorCodes
    message: str

    def __dict__(self):
        return {
            'code': self.code.value,
            'message': self.message,
        }


class PullRequestStatus(Enum):
    OPEN = 'OPEN',
    MERGED = 'MERGED'
