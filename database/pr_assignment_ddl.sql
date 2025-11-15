CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TYPE IF NOT EXISTS pull_request_status_type AS ENUM('OPEN', 'MERGED');

CREATE TABLE IF NOT EXISTS team (
	team_name TEXT PRIMARY KEY
);

CREATE TABLE IF NOT EXISTS "user" (
	user_id TEXT PRIMARY KEY,
	username TEXT NOT NULL,
	team_name TEXT REFERENCES team(team_name) NOT NULL,
	is_active BOOLEAN NOT NULL
);

CREATE TABLE IF NOT EXISTS pull_request (
	pull_request_id TEXT PRIMARY KEY,
	pull_request_name TEXT NOT NULL,
	author_id TEXT REFERENCES "user"(user_id) NOT NULL,
	status pull_request_status_type NOT NULL,
	created_at TIMESTAMP,
	merged_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS "assignment" (
	assignment_id CHARACTER VARYING(36) PRIMARY KEY DEFAULT uuid_generate_v4(),
	pull_request_id TEXT REFERENCES pull_request(pull_request_id) NOT NULL,
	reviewer_id TEXT REFERENCES "user"(user_id) NOT NULL
);