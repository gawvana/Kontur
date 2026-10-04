import os
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def alembic(url, *args):
    env = {**os.environ, 'DATABASE_URL':url}
    result = subprocess.run([sys.executable,'-m','alembic',*args],cwd=ROOT,env=env,capture_output=True,text=True)
    assert result.returncode == 0, result.stderr
    return result.stdout

def test_upgrade_preserves_existing_private_data(tmp_path):
    path=tmp_path/'migration.db'
    url='sqlite+aiosqlite:///'+path.as_posix()
    alembic(url,'upgrade','e2c31251b2de')
    with sqlite3.connect(path) as db:
        db.execute("INSERT INTO users(id,telegram_id,role) VALUES(1,'111','USER')")
        db.execute("INSERT INTO subjects(id,username) VALUES(1,'contact_one')")
        db.execute("INSERT INTO catalogs(id,owner_id,name,is_private) VALUES(1,1,'private',1)")
        db.execute("INSERT INTO catalog_items(id,catalog_id,subject_id,note,is_private) VALUES(1,1,1,'retain private note',1)")
        db.execute("INSERT INTO cases(id,creator_id,subject_id,status,description) VALUES(1,1,1,'PENDING','retain experience')")
    alembic(url,'upgrade','head')
    alembic(url,'check')
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT note FROM catalog_items').fetchone()[0]=='retain private note'
        assert db.execute('SELECT description FROM cases').fetchone()[0]=='retain experience'
        assert db.execute('SELECT version_num FROM alembic_version').fetchone()[0]=='full_features'
        assert db.execute('SELECT count(*) FROM sessions').fetchone()[0]==0
        plan=db.execute("EXPLAIN QUERY PLAN SELECT id FROM subjects WHERE lower(username)='contact_one'").fetchall()
        assert any('SEARCH' in row[3] and 'ix_subjects_username_lower' in row[3] for row in plan)
    alembic(url,'downgrade','e2c31251b2de')
    alembic(url,'upgrade','head')
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT count(*) FROM cases').fetchone()[0]==1

def test_postgres_offline_sql_and_percent_password():
    sql=alembic('postgresql+asyncpg://audit:p%40ss@localhost/audit','upgrade','head','--sql')
    assert 'CREATE TABLE sessions' in sql
    assert 'uq_case_request' in sql

def test_duplicate_memberships_are_not_silently_deleted(tmp_path):
    path=tmp_path/'duplicates.db'; url='sqlite+aiosqlite:///'+path.as_posix()
    alembic(url,'upgrade','audit_security')
    with sqlite3.connect(path) as db:
        db.execute("INSERT INTO users(id,telegram_id,role) VALUES(1,'111','USER')")
        db.execute("INSERT INTO subjects(id,username) VALUES(1,'contact_one')")
        db.execute("INSERT INTO catalogs(id,owner_id,name,is_private) VALUES(1,1,'private',1)")
        db.execute("INSERT INTO catalog_items(catalog_id,subject_id,note,is_private) VALUES(1,1,'first note',1)")
        db.execute("INSERT INTO catalog_items(catalog_id,subject_id,note,is_private) VALUES(1,1,'second note',1)")
    result=subprocess.run([sys.executable,'-m','alembic','upgrade','head'],cwd=ROOT,env={**os.environ,'DATABASE_URL':url},capture_output=True,text=True)
    assert result.returncode!=0 and 'Duplicate catalog memberships' in result.stderr
    with sqlite3.connect(path) as db:
        assert db.execute('SELECT note FROM catalog_items ORDER BY id').fetchall()==[('first note',),('second note',)]
        assert db.execute('SELECT version_num FROM alembic_version').fetchone()[0]=='audit_security'
