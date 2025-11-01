"""Domain routers for the FastAPI application."""

from .._fastapi_compat import APIRouter

from . import auth, categories, clients, health, inventory, orders, pos, procurements, products, suppliers, users

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(categories.router)
api_router.include_router(clients.router)
api_router.include_router(suppliers.router)
api_router.include_router(orders.router)
api_router.include_router(procurements.router)
api_router.include_router(products.router)
api_router.include_router(inventory.router)
api_router.include_router(pos.router)
api_router.include_router(health.router)
