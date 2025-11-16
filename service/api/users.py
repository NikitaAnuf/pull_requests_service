import json

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse

from connection import connection
from utils.properties import ErrorCodes
from utils.schemas import ErrorResponse, Error, User
from utils.db_queries import select_query, change_data_query
from api.pull_request import reassign_pull_request


router = APIRouter()


@router.post("/setIsActive")
async def set_is_active(user_id: str = Body(...), is_active: bool = Body(...)):
    if change_data_query('''
        UPDATE "user" SET
            is_active = %(is_active)s
        WHERE user_id = %(user_id)s
    ''', {'user_id': user_id, 'is_active': is_active}):
        connection.commit()
        user = select_query('SELECT * FROM "user" WHERE user_id = %(user_id)s',
                            {'user_id': user_id}, return_one=True)
        return JSONResponse(status_code=200, content=user)
    else:
        connection.rollback()
        return JSONResponse(status_code=400, content=ErrorResponse(Error(
            code=ErrorCodes.NOT_FOUND, message='user_id not found')).__dict__())


@router.get("/getReview")
async def get_review(user_id: str):
    user_pull_requests = select_query('''
                                      SELECT pr.pull_request_id, pr.pull_request_name, pr.author_id, pr.status
                                      FROM "user" u
                                      LEFT JOIN "assignment" a ON u.user_id = a.reviewer_id
                                      LEFT JOIN pull_request pr ON a.pull_request_id = pr.pull_request_id
                                      WHERE u.user_id = %(user_id)s
                              ''', {'user_id': user_id})
    if user_pull_requests is None:
        return JSONResponse(status_code=404, content=ErrorResponse(Error(
            code=ErrorCodes.NOT_FOUND, message="user_id not found")
        ).__dict__())
    else:
        return JSONResponse(status_code=200, content={'user_id': user_id,
                                                      'members': [dict(pr) for pr in user_pull_requests]})


# deactivate a list of users and reassign their reviewed opened pull requests
# if reassign is not possible, just delete this user from pull request
@router.post("/deactivateMany")
async def deactivate_users(users: list[str] = Body(..., embed=True)):
    reassign_responses = {}
    for user_id in users:
        if select_query('SELECT user_id FROM "user" WHERE user_id = %(user_id)s',
                        {'user_id': user_id}, return_one=True) is None:
            return JSONResponse(status_code=404, content=ErrorResponse(Error(
                code=ErrorCodes.NOT_FOUND, message="user_id not found"
            )).__dict__())

        # deactivate user
        change_data_query('UPDATE "user" SET is_active = FALSE WHERE user_id = %(user_id)s',
                          {'user_id': user_id})

        # get assigned opened pull requests
        assigned_requests = select_query('''
                                         SELECT pr.pull_request_id FROM pull_request pr
                                         JOIN assignment a ON pr.pull_request_id = a.pull_request_id
                                         JOIN "user" u ON a.reviewer_id = u.user_id
                                         WHERE u.user_id = %(user_id)s AND pr.status = 'OPEN'
                                         ''', {'user_id': user_id})
        # reassign opened pull requests where user was a reviewer
        if assigned_requests is None:
            continue
        reassign_responses[user_id] = []
        for pr in assigned_requests:
            reassign_response = await reassign_pull_request(pr['pull_request_id'], user_id)
            reassign_responses[user_id].append(json.loads(reassign_response.body))

    # return reassign responses content
    return JSONResponse(status_code=200, content={'reassignments': reassign_responses})
