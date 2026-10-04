from fastapi import APIRouter
from api.v1 import auth, subjects, catalogs, cases, admin, saved_contacts, notifications, support

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(subjects.router, prefix="/subjects", tags=["subjects"])
api_router.include_router(catalogs.router, prefix="/catalogs", tags=["catalogs"])
api_router.include_router(cases.router, prefix="/cases", tags=["cases"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(saved_contacts.router, prefix="/contacts", tags=["contacts"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(support.router, prefix="/support", tags=["support"])
