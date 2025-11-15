from dataclasses import asdict

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from connection import connection
from utils.schemas import ErrorResponse, Error, Team
from utils.properties import ErrorCodes
from utils.db_queries import select_query, change_data_query


router = APIRouter()


@router.post("/add")
async def add_team(team: Team):
    # check if team already exists in DB
    if select_query("SELECT * FROM team WHERE team_name = %(team_name)s",
                    {'team_name': team.team_name}, return_one=True) is not None:
        return JSONResponse(status_code=400, content=ErrorResponse(Error(
            code=ErrorCodes.TEAM_EXISTS, message="team_name already exists")
        ).__dict__())

    # if insert operation failed, return internal server error
    if not change_data_query("INSERT INTO team(team_name) VALUES (%(team_name)s)",
                    {'team_name': team.team_name}):
        connection.rollback()
        return JSONResponse(status_code=500, content=ErrorResponse(Error(
            code=ErrorCodes.SERVER_ERROR, message="Internal Server Error, unable to add team")
        ).__dict__())

    # add team members to user table if they don't exist or update their properties if users with same user_ids exist
    for member in team.members:
        if not change_data_query('''
            INSERT INTO "user" (user_id, username, team_name, is_active) 
            VALUES (%(user_id)s, %(username)s, %(team_name)s, %(is_active)s)
            ON CONFLICT (user_id) DO UPDATE SET 
                username = %(username)s,
                team_name = %(team_name)s,
                is_active = %(is_active)s
        ''', {**asdict(member), 'team_name': team.team_name}):
            connection.rollback()
            return JSONResponse(status_code=500, content=ErrorResponse(Error(
                code=ErrorCodes.SERVER_ERROR, message="Internal Server Error, unable to add or update user")
            ).__dict__())

    connection.commit()
    return JSONResponse(status_code=201, content=asdict(team))


@router.get("/get")
async def get_team(team_name: str):
    team_users = select_query('''
                                   SELECT u.user_id, u.username, u.is_active
                                   FROM team t
                                   JOIN "user" u ON t.team_name = u.team_name
                                   WHERE t.team_name = %(team_name)s
                              ''', {'team_name': team_name})
    if team_users is None:
        return JSONResponse(status_code=404, content=ErrorResponse(Error(
            code=ErrorCodes.NOT_FOUND, message="team_name not found")
        ).__dict__())
    else:
        return JSONResponse(status_code=200, content={'team_name': team_name,
                                                      'members': [dict(user) for user in team_users]})
