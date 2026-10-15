CREATE DATABASE mosip_selfreg
	ENCODING = 'UTF8'
	LC_COLLATE = 'en_US.UTF-8'
	LC_CTYPE = 'en_US.UTF-8'
	TABLESPACE = pg_default
	OWNER = postgres
	TEMPLATE  = template0;
-- ddl-end --
COMMENT ON DATABASE mosip_selfreg IS 'To store registration details.';

ALTER DATABASE mosip_selfreg SET search_path TO selfreg,pg_catalog,public;

-- ddl-end --

\c mosip_selfreg postgres

-- object: regprc | type: SCHEMA --
DROP SCHEMA IF EXISTS selfreg CASCADE;
CREATE SCHEMA selfreg;
-- ddl-end --
ALTER SCHEMA selfreg OWNER TO postgres;
-- ddl-end --

CREATE ROLE selfreguser WITH
	INHERIT
	LOGIN
	PASSWORD :dbuserpwd;
-- ddl-end --

GRANT CONNECT
   ON DATABASE mosip_selfreg
   TO selfreguser;
-- ddl-end --

-- object: grant_3543fb6cf7 | type: PERMISSION --
GRANT USAGE
   ON SCHEMA selfreg
   TO selfreguser;
-- ddl-end --

-- object: grant_8e1a2559ed | type: PERMISSION --
GRANT SELECT,UPDATE
   ON ALL TABLES IN SCHEMA selfreg
   TO selfreguser;
-- ddl-end --

ALTER DEFAULT PRIVILEGES IN SCHEMA selfreg
	GRANT SELECT,UPDATE ON TABLES TO selfreguser;


CREATE TABLE selfreg.self_registration(
	rid character varying(36) NOT NULL,
	name character varying(100) NOT NULL,
	dob character varying(10),
	gender character varying(10),
	phone character varying(20),
	email_id character varying(256) NOT NULL,
	address character varying(256),
	lang_code character varying(3),
	uin character varying(20),
	bio_data bytea NOT NULL,
	id_type character varying(10),
    id_number character varying(20),
    issued_on timestamp,
    expires_on timestamp,
    token_id character varying(36),
	status character varying(10) NOT NULL,
	cr_by character varying(20) NOT NULL,
	cr_dtimes timestamp NOT NULL,
	upd_by character varying(20),
	upd_dtimes timestamp,
	CONSTRAINT pk_reg_id PRIMARY KEY (rid)
);
-- ddl-end --
COMMENT ON TABLE selfreg.self_registration IS 'To store demographic and phone of registered person';
-- ddl-end --

CREATE INDEX IF NOT EXISTS idx_reg_emailandstatus ON selfreg.self_registration USING btree (email_id, status);

CREATE INDEX IF NOT EXISTS idx_reg_status ON selfreg.self_registration USING btree (status);
