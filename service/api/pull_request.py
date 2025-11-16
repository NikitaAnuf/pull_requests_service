from datetime import datetime

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse

from connection import connection
from utils.schemas import ErrorResponse, Error
from utils.properties import ErrorCodes, PullRequestStatus
from utils.db_queries import select_query, change_data_query
from variables import JSON_DATETIME_FORMAT

router = APIRouter()


@router.post("/create")
async def create_pull_request(pull_request_id: str = Body(...), pull_request_name: str = Body(...),
                        author_id: str = Body(...)):
    # we can't create a user with non-existing team, that's why we only need to check for user to exist
    if select_query('SELECT user_id FROM "user" WHERE user_id = %(author_id)s',
                    {'author_id': author_id}, return_one=True) is None:
        return JSONResponse(status_code=404, content=ErrorResponse(Error(
            code=ErrorCodes.NOT_FOUND, message='user_id not found'
        )).__dict__())

    # check if pull request with the same pull_request_is already exists
    if select_query('SELECT pull_request_id FROM pull_request WHERE pull_request_id = %(pull_request_id)s',
                    {'pull_request_id': pull_request_id}) is not None:
        return JSONResponse(status_code=409, content=ErrorResponse(Error(
            code=ErrorCodes.PR_EXISTS, message='PR id already exists'
        )).__dict__())

    current_datetime = datetime.now()
    # create pull_request
    if change_data_query('''
                         INSERT INTO pull_request (pull_request_id, pull_request_name, author_id, status, created_at)
                         VALUES (%(pull_request_id)s, %(pull_request_name)s, %(author_id)s, %(status)s, %(created_at)s)
                         ''', {'pull_request_id': pull_request_id, 'pull_request_name': pull_request_name,
                               'author_id': author_id, 'status': PullRequestStatus.OPEN.value,
                               'created_at': current_datetime}):
        connection.commit()
    else:
        connection.rollback()
        return JSONResponse(status_code=500, content=ErrorResponse(Error(
            code=ErrorCodes.SERVER_ERROR, message='Internal Server Error, unable to create pull request')).__dict__())

    assigned_reviewers = []
    # assign from 0 to 2 reviewers to pull request
    # firstly, check what team users are active
    active_team_users = select_query('''
                                     SELECT user_id FROM "user"
                                     WHERE team_name = (SELECT team_name FROM "user"
                                                        WHERE user_id = %(author_id)s
                                                        LIMIT 1) AND
                                         user_id <> %(author_id)s AND
                                         is_active = TRUE
                                     ''', {'author_id': author_id})
    if active_team_users is not None:
        # gather 2 or less user_ids in an array
        assigned_reviewers = list(map(lambda user: user['user_id'], active_team_users[:2]))

    # assign reviewers to created pull_request
    for reviewer in assigned_reviewers:
        if change_data_query('''
            INSERT INTO "assignment" (pull_request_id, reviewer_id)
            VALUES (%(pull_request_id)s, %(reviewer_id)s)
        ''', {'pull_request_id': pull_request_id, 'reviewer_id': reviewer}):
            connection.commit()
        else:
            connection.rollback()
            return JSONResponse(status_code=500, content=ErrorResponse(Error(
                code=ErrorCodes.SERVER_ERROR,
                message='Internal Server Error, unable to assign reviewer pull request')).__dict__())

    # if everything was OK, return pull request data in response
    return JSONResponse(status_code=200, content={
        'pr':
            {'pull_request_id': pull_request_id, 'pull_request_name': pull_request_name, 'author_id': author_id,
             'status': PullRequestStatus.OPEN.name, 'assigned_reviewers': assigned_reviewers,
             'createdAt': current_datetime.strftime(JSON_DATETIME_FORMAT),
             'mergedAt': None}
    })


@router.post("/merge")
async def merge_pull_request(pull_request_id: str = Body(..., embed=True)):
    pull_request_info = select_query('''
                                     SELECT pull_request_id, pull_request_name, author_id, created_at FROM pull_request
                                     WHERE pull_request_id = %(pull_request_id)s
                                     ''', {'pull_request_id': pull_request_id}, return_one=True)
    # return 404 if pull request doesn't exist
    if pull_request_info is None:
        return JSONResponse(status_code=404, content=ErrorResponse(Error(
            code=ErrorCodes.NOT_FOUND, message='pull_request_id not found'
        )).__dict__())

    current_datetime = datetime.now()
    # change pull request status to merged and add mergedAt value
    if change_data_query('''
        UPDATE pull_request SET status = %(status)s, merged_at = %(merged_at)s
        WHERE pull_request_id = %(pull_request_id)s
    ''', {'pull_request_id': pull_request_id, 'status': PullRequestStatus.MERGED.name,
          'merged_at': current_datetime.strftime(JSON_DATETIME_FORMAT)}):
        connection.commit()
    else:
        connection.rollback()
        return JSONResponse(status_code=500, content=ErrorResponse(Error(
            code=ErrorCodes.SERVER_ERROR,
            message='Internal Server Error, unable to change pull request status')).__dict__())

    # get reviewers assigned to pull request
    assigned_reviewers = select_query('''
                                      SELECT reviewer_id FROM "assignment"
                                      WHERE pull_request_id = %(pull_request_id)s
                                      ''', {'pull_request_id': pull_request_id})
    if assigned_reviewers is None:
        assigned_reviewers = []
    else:
        assigned_reviewers = list(map(lambda reviewer: reviewer['reviewer_id'], assigned_reviewers))

    return JSONResponse(status_code=200, content={'pr': {
        'pull_request_id': pull_request_id, 'pull_request_name': pull_request_info['pull_request_name'],
        'author_id': pull_request_info['author_id'], 'status': PullRequestStatus.MERGED.name,
        'assigned_reviewers': assigned_reviewers,
        'createdAt': pull_request_info['created_at'].strftime(JSON_DATETIME_FORMAT),
        'mergedAt': current_datetime.strftime(JSON_DATETIME_FORMAT)
    }})


@router.post("/reassign")
async def reassign_pull_request(pull_request_id: str = Body(...), old_user_id: str = Body(...)):
    # check if pull request and user exist
    if select_query('SELECT pull_request_id FROM pull_request WHERE pull_request_id = %(pull_request_id)s',
                    {'pull_request_id': pull_request_id}, return_one=True) is None or \
        select_query('SELECT user_id FROM "user" WHERE user_id = %(old_user_id)s',
                     {'old_user_id': old_user_id}, return_one=True) is None:
        return JSONResponse(status_code=404, content=ErrorResponse(Error(
            ErrorCodes.NOT_FOUND, message='pull_request_id or user_id not found')).__dict__())

    # check if pull request is already merged
    if select_query('SELECT status FROM pull_request WHERE pull_request_id = %(pull_request_id)s',
                    {'pull_request_id': pull_request_id},
                    return_one=True)['status'] == PullRequestStatus.MERGED.name:
        return JSONResponse(status_code=409, content=ErrorResponse(Error(
            code=ErrorCodes.PR_MERGED, message='cannot reassign on merged PR'
        )).__dict__())

    # check if user assign as a reviewer for this pull request
    if select_query('''
                    SELECT * FROM "assignment"
                    WHERE pull_request_id = %(pull_request_id)s AND reviewer_id = %(old_user_id)s
                    ''', {'pull_request_id': pull_request_id, 'old_user_id': old_user_id},
                    return_one=True) is None:
        return JSONResponse(status_code=409, content=ErrorResponse(Error(
            code=ErrorCodes.NOT_ASSIGNED, message='reviewer is not assigned to this PR'
        )).__dict__())

    # check if we have another active reviewer in team to assign pull request
    reassign_candidate = select_query('''
        SELECT user_id FROM "user"
        WHERE team_name = (SELECT team_name FROM "user" WHERE user_id = %(old_user_id)s LIMIT 1) AND
            user_id NOT IN (SELECT reviewer_id FROM "assignment" WHERE pull_request_id = %(pull_request_id)s) AND
            user_id <> (SELECT author_id FROM pull_request WHERE pull_request_id = %(pull_request_id)s LIMIT 1) AND
            is_active = True
        ''', {'pull_request_id': pull_request_id, 'old_user_id': old_user_id}, return_one=True)
    if reassign_candidate is None:
        return JSONResponse(status_code=409, content=ErrorResponse(Error(
            code=ErrorCodes.NO_CANDIDATE, message='no active replacement in team'
        )).__dict__())

    # delete old assignment and create new assignment
    if change_data_query('''
                         DELETE FROM "assignment"
                         WHERE pull_request_id = %(pull_request_id)s AND reviewer_id = %(old_user_id)s
                         ''', {'pull_request_id': pull_request_id, 'old_user_id': old_user_id}):
        connection.commit()
    else:
        connection.rollback()
        return JSONResponse(status_code=500, content=ErrorResponse(Error(
            code=ErrorCodes.SERVER_ERROR, message='Internal Server Error, unable to unassign reviewer from pull request'
        )).__dict__())

    if change_data_query('''
                         INSERT INTO "assignment" (pull_request_id, reviewer_id)
                         VALUES (%(pull_request_id)s, %(reassign_candidate)s)
                         ''', {'pull_request_id': pull_request_id, 'reassign_candidate': reassign_candidate['user_id']}):
        connection.commit()
    else:
        connection.rollback()
        return JSONResponse(status_code=500, content=ErrorResponse(Error(
            code=ErrorCodes.SERVER_ERROR, message='Internal Server Error, unable to assign new reviewer from pull request'
        )).__dict__())

    # get pull request and reviewers data
    pull_request_info = select_query('''
                                     SELECT pull_request_name, author_id, status, created_at, merged_at
                                     FROM pull_request
                                     WHERE pull_request_id = %(pull_request_id)s
                                     ''', {'pull_request_id': pull_request_id}, return_one=True)
    if pull_request_info is None:
        return JSONResponse(status_code=500, content=ErrorResponse(Error(
            code=ErrorCodes.SERVER_ERROR, message='Internal Server Error, unable to get pull request information'
        )).__dict__())

    assigned_reviewers = select_query('''
                                      SELECT reviewer_id FROM "assignment"
                                      WHERE pull_request_id = %(pull_request_id)s
                                      ''', {'pull_request_id': pull_request_id})
    if assigned_reviewers is None:
        return JSONResponse(status_code=500, content=ErrorResponse(Error(
            code=ErrorCodes.SERVER_ERROR, message='Internal Server Error, unable to get reviewers assigned to pull request'
        )).__dict__())
    assigned_reviewers = list(map(lambda reviewer: reviewer['reviewer_id'], assigned_reviewers))

    return JSONResponse(status_code=200, content={
        'pr': {
            'pull_request_id': pull_request_id,
            'pull_request_name': pull_request_info['pull_request_name'],
            'author_id': pull_request_info['author_id'],
            'status': pull_request_info['status'],
            'assigned_reviewers': assigned_reviewers,
            'createdAt': pull_request_info['created_at'].strftime(JSON_DATETIME_FORMAT),
            'mergedAt': pull_request_info['merged_at'].strftime(JSON_DATETIME_FORMAT) if pull_request_info['merged_at'] is not None else None,
        },
        'replaced_by': reassign_candidate['user_id']})
