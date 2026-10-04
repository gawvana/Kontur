import asyncio
import hashlib
import hmac
import json
import time
from urllib.parse import urlencode
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from db.database import get_db, Base
from db.models import User, Subject, Catalog, CatalogItem, Case, Session, Role
from main import app
from api.v1.auth import verify_telegram_data
from core.security import create_access_token

TOKEN = "123456789:local-test-only-not-a-real-token"

def signed(user=111, age=0, data=None):
    fields = {"auth_date": str(int(time.time()) - age), "user": json.dumps({"id": user})}
    if data is not None:
        fields.update(data)
    check = "\n".join(f"{key}={fields[key]}" for key in sorted(fields))
    secret = hmac.new(b"WebAppData", TOKEN.encode(), hashlib.sha256).digest()
    fields["hash"] = hmac.new(secret, check.encode(), hashlib.sha256).hexdigest()
    return urlencode(fields)

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", TOKEN)
    monkeypatch.setenv("JWT_SECRET", "local-test-only-" + "x" * 40)
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp_path / 'audit.db'}")
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async def setup():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        async with factory() as db:
            db.add_all([User(id=1, telegram_id="111"), User(id=2, telegram_id="222"), User(id=3, telegram_id="333", role=Role.OWNER)])
            await db.flush()
            db.add_all([Subject(id=1, telegram_id="444", username="contact_one", phone="private-phone"), Subject(id=2, telegram_id="555", username="private_other", phone="other-phone"), Subject(id=3, telegram_id="111", username="self_user")])
            db.add_all([Catalog(id=1, owner_id=1, name="private"), Catalog(id=2, owner_id=2, name="other")])
            await db.flush()
            db.add_all([CatalogItem(catalog_id=1, subject_id=1, note="my note"), CatalogItem(catalog_id=2, subject_id=2, note="other secret")])
            await db.commit()
    asyncio.run(setup())
    async def override():
        async with factory() as db:
            yield db
    app.dependency_overrides[get_db] = override
    with TestClient(app) as c:
        c.factory = factory
        yield c
    app.dependency_overrides.clear()
    asyncio.run(engine.dispose())

def login(client, user=111):
    response = client.post("/api/v1/auth/telegram", json={"initData": signed(user)})
    assert response.status_code == 200, response.text
    return {"Authorization": "Bearer " + response.json()["access_token"]}

def test_signature_valid():
    assert verify_telegram_data(signed(2**52), TOKEN)["id"] == 2**52

@pytest.mark.parametrize("data", ["", "anything", lambda: signed(age=301), lambda: signed(age=-60), lambda: signed(data={"user": "{}"}), lambda: signed(data={"user": "null"}), lambda: signed(data={"user": json.dumps({"id": True})}), lambda: signed(data={"user": json.dumps({"id": -1})}), lambda: signed(data={"user": json.dumps({"id": "111"})}), lambda: signed() + "&auth_date=1"])
def test_invalid_init_data(client, data):
    if callable(data):
        data = data()
    assert client.post("/api/v1/auth/telegram", json={"initData": data}).status_code == 401

def test_tampered_signature(client):
    assert client.post("/api/v1/auth/telegram", json={"initData": signed().replace('111','222')}).status_code == 401

def test_missing_bot_token(client, monkeypatch):
    monkeypatch.delenv("BOT_TOKEN")
    assert client.post("/api/v1/auth/telegram", json={"initData": signed()}).status_code == 503

def test_secret_required(monkeypatch):
    monkeypatch.delenv("JWT_SECRET", raising=False)
    with pytest.raises(RuntimeError):
        create_access_token(111, "session")

def test_auth_logout_revocation(client):
    headers = login(client)
    assert client.get("/api/v1/auth/me", headers=headers).json()["telegram_id"] == "111"
    assert client.post("/api/v1/auth/logout", headers=headers).status_code == 204
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 401

def test_revoked_database_session(client):
    from sqlalchemy import delete
    headers = login(client)
    async def revoke():
        async with client.factory() as db:
            await db.execute(delete(Session))
            await db.commit()
    asyncio.run(revoke())
    assert client.get("/api/v1/catalogs", headers=headers).status_code == 401

@pytest.mark.parametrize("path", ["catalogs", "subjects/1", "subjects/search?q=contact_one", "cases/my", "admin/cases"])
def test_no_auth(client, path):
    assert client.get('/api/v1/' + path).status_code == 401

def test_subject_privacy(client):
    headers = login(client)
    assert client.get("/api/v1/subjects/2", headers=headers).status_code == 404
    assert client.get("/api/v1/subjects/999", headers=headers).status_code == 404
    result = client.get("/api/v1/subjects/1", headers=headers)
    assert result.status_code == 200
    assert "phone" not in result.json()
    assert result.headers['cache-control'] == 'no-store'
    assert client.get("/api/v1/subjects/search?q=private_other", headers=headers).json() == []

@pytest.mark.parametrize("query", ["@CONTACT_ONE", "contact_one", "https://t.me/contact_one", "https://telegram.me/contact_one"])
def test_normalized_search(client, query):
    result = client.get("/api/v1/subjects/search", params={"q": query}, headers=login(client))
    assert result.status_code == 200
    assert [s['id'] for s in result.json()] == [1]

@pytest.mark.parametrize("query", ["", "%", "' OR 1=1 --", "https://evil.test/contact_one", "https://t.me/contact_one/1", "https://t.me@evil.test/contact_one", "https://t.me/contact_one?x=1", "https://t.me/+invite", "123456789", "javascript:alert(1)"])
def test_bad_search(client, query):
    assert client.get("/api/v1/subjects/search", params={"q": query}, headers=login(client)).status_code == 422

def test_catalog_owner_and_fields(client):
    headers = login(client)
    assert [c["id"] for c in client.get("/api/v1/catalogs", headers=headers).json()] == [1]
    assert client.get("/api/v1/catalogs/2/contacts", headers=headers).status_code == 404
    assert client.post("/api/v1/catalogs/2/contacts", headers=headers, json={"subject_id":1}).status_code == 404
    assert client.post("/api/v1/catalogs/1/contacts", headers=headers, json={"subject_id":2}).status_code == 404
    assert client.post("/api/v1/catalogs/1/contacts", headers=headers, json={"subject_id":999}).status_code == 404
    assert client.post("/api/v1/catalogs", headers={**headers, "Idempotency-Key":"catalog-test"}, json={"name":" ", "owner_id":2}).status_code == 422
    result = client.post("/api/v1/catalogs", headers={**headers, "Idempotency-Key":"catalog-test"}, json={"name":"new"})
    assert result.status_code == 200
    assert result.json()["owner_id"] == 1 and result.json()["is_private"] is True

def test_case_author_self_and_foreign(client):
    headers = login(client)
    for subject, status in [(3,422), (2,404), (999,404)]:
        assert client.post('/api/v1/cases', headers={**headers,'Idempotency-Key':str(subject)}, json={'subject_id':subject,'description':'experience'}).status_code == status
    assert client.post('/api/v1/cases', headers={**headers,'Idempotency-Key':'spoof'}, json={'subject_id':1,'description':'experience','creator_id':2}).status_code == 422

def test_case_idempotency(client):
    headers = {**login(client), 'Idempotency-Key':'case-1'}
    body = {'subject_id':1,'description':'experience'}
    first = client.post('/api/v1/cases', headers=headers,json=body)
    second = client.post('/api/v1/cases', headers=headers,json=body)
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()
    assert first.json()['status'] == 'PENDING'
    assert client.post('/api/v1/cases', headers=headers,json={**body,'description':'changed'}).status_code == 409
    assert len(client.get('/api/v1/cases/my', headers=headers).json()) == 1
    assert client.get('/api/v1/cases/my', headers=login(client,222)).json() == []
    assert client.post('/api/v1/cases', headers=login(client),json=body).status_code == 422

def test_concurrent_case_requests(client):
    from concurrent.futures import ThreadPoolExecutor
    headers = {**login(client), 'Idempotency-Key':'concurrent'}
    def post(_):
        return client.post('/api/v1/cases',headers=headers,json={'subject_id':1,'description':'same request'})
    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(post,range(2)))
    assert [r.status_code for r in results] == [200,200]
    assert results[0].json()['id'] == results[1].json()['id']

@pytest.mark.parametrize('user,status',[(111,403),(333,503)])
def test_staff_fail_closed(client,user,status):
    assert client.get('/api/v1/admin/cases',headers=login(client,user)).status_code == status

@pytest.mark.parametrize('path',['catalogs?limit=101','cases/my?offset=-1','catalogs/1/contacts?limit=0'])
def test_pagination_bounds(client,path):
    assert client.get('/api/v1/'+path,headers=login(client)).status_code == 422

@pytest.mark.parametrize('mode',['expired','unsigned','missing_session','forged'])
def test_invalid_jwt(client,mode):
    import jwt
    payload={'sub':'111','sid':'absent','iat':int(time.time()),'exp':int(time.time())+60}
    if mode=='expired':
        payload['exp']=int(time.time())-60
    if mode=='missing_session':
        payload.pop('sid')
    token=jwt.encode(payload,None if mode=='unsigned' else ('wrong-key-'+'z'*40 if mode=='forged' else 'local-test-only-'+'x'*40),algorithm='none' if mode=='unsigned' else 'HS256')
    assert client.get('/api/v1/auth/me',headers={'Authorization':'Bearer '+token}).status_code==401

def test_catalog_contact_retries(client):
    headers={**login(client),'Idempotency-Key':'catalog-retry'}
    body={'name':'repeated'}
    first=client.post('/api/v1/catalogs',headers=headers,json=body)
    second=client.post('/api/v1/catalogs',headers=headers,json=body)
    assert first.status_code==second.status_code==200
    assert first.json()==second.json()
    assert client.post('/api/v1/catalogs',headers=headers,json={'name':'changed'}).status_code==409
    path=f"/api/v1/catalogs/{first.json()['id']}/contacts"
    contact={'subject_id':1,'note':'private note'}
    a=client.post(path,headers=headers,json=contact)
    b=client.post(path,headers=headers,json=contact)
    assert a.status_code==b.status_code==200 and a.json()==b.json()
    assert client.post(path,headers=headers,json={**contact,'note':'overwrite'}).status_code==409
    assert len(client.get(path,headers=headers).json())==1

def test_concurrent_catalog_and_contact_requests(client):
    from concurrent.futures import ThreadPoolExecutor
    headers={**login(client),'Idempotency-Key':'catalog-concurrent'}
    with ThreadPoolExecutor(max_workers=2) as executor:
        results=list(executor.map(lambda _:client.post('/api/v1/catalogs',headers=headers,json={'name':'same catalog'}),range(2)))
    assert [r.status_code for r in results]==[200,200]
    assert results[0].json()['id']==results[1].json()['id']
    path=f"/api/v1/catalogs/{results[0].json()['id']}/contacts"
    with ThreadPoolExecutor(max_workers=2) as executor:
        contacts=list(executor.map(lambda _:client.post(path,headers=headers,json={'subject_id':1,'note':'same'}),range(2)))
    assert [r.status_code for r in contacts]==[200,200]
    assert contacts[0].json()['id']==contacts[1].json()['id']
