from fastapi import APIRouter
from fastapi.responses import JSONResponse

from utils.schemas import ErrorResponse, Error
from utils.properties import ErrorCodes
from utils.db_queries import select_query


router = APIRouter()


# count reviewers amount on requested pull requests or on all pull requests if pull_request_id is None
@router.get("/pull_request_reviewers_amount")
async def pull_request_viewers_amount(pull_request_id: str | None = None):
    # check if pull_request exists or any pull_request_id exists
    if pull_request_id is not None and select_query('''
                                                    SELECT pull_request_id FROM pull_request
                                                    WHERE pull_request_id = %(pull_request_id)s
                                                    ''', {'pull_request_id': pull_request_id},
                                                    return_one=True) is None or \
            pull_request_id is None and select_query('SELECT * FROM pull_request') is None:
        return JSONResponse(status_code=404, content=ErrorResponse(Error(
            code=ErrorCodes.NOT_FOUND, message='pull request not found'
        )).__dict__())

    # build query to get reviewers amount
    query = 'SELECT pull_request_id, COUNT(reviewer_id) FROM "assignment"'
    if pull_request_id is not None:
        query += ' WHERE pull_request_id = %(pull_request_id)s\n'
    query += ' GROUP BY pull_request_id'
    reviewers_amount = select_query(query, {'pull_request_id': pull_request_id})

    response = {}
    for ra in reviewers_amount:
        response[ra['pull_request_id']] = ra['count']

    return JSONResponse(status_code=200, content={'reviewers_amount': response})
