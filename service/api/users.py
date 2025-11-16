from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse

from connection import connection
from utils.properties import ErrorCodes
from utils.schemas import ErrorResponse, Error, User
from utils.db_queries import select_query, change_data_query


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
