"""HTTP-контракт приложения офисины: каталог, касса, склад, сеть, журнал, возвраты, выгрузки."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from app.officine import exports, logic, receipt, reorder, returns
from app.officine.errors import OfficineError

router = APIRouter(prefix="/api/app", tags=["officine app"])


class Line(BaseModel):
    cip: str = Field(min_length=1, max_length=20)
    quantite: int = Field(ge=1, le=999)


class SaleRequest(BaseModel):
    officine_id: int = Field(default=1, ge=1, le=9999)
    canal: str = Field(default="comptoir", max_length=20)
    remise_pct: float = Field(default=0, ge=0, le=100)
    lignes: list[Line] = Field(default_factory=list)
    acteur: str = Field(default="pharmacien", max_length=60)
    role: str = Field(default="pharmacien", pattern="^(pharmacien|titulaire)$")


class ReturnRequest(BaseModel):
    lignes: list[Line] = Field(default_factory=list)
    acteur: str = Field(default="pharmacien", max_length=60)
    role: str = Field(default="pharmacien", pattern="^(pharmacien|titulaire)$")


class ReorderLine(BaseModel):
    cip: str = Field(min_length=1, max_length=20)
    quantite: int = Field(ge=1, le=100000)


class ReorderRequest(BaseModel):
    lignes: list[ReorderLine] = Field(default_factory=list)
    acteur: str = Field(default="pharmacien", max_length=60)


class ProductRequest(BaseModel):
    cip: str = Field(min_length=13, max_length=13)
    nom: str = Field(min_length=2, max_length=120)
    dci: str = Field(default="", max_length=80)
    categorie: str = Field(default="autre", max_length=40)
    prix_public: float = Field(gt=0, le=100000)
    taux_remboursement: int = Field(default=0, ge=0, le=100)
    thermosensible: bool = False
    stock_actuel: int = Field(default=0, ge=0, le=1000000)
    seuil: int = Field(default=10, ge=0, le=1000000)
    acteur: str = Field(default="pharmacien", max_length=60)


class ProductPatch(BaseModel):
    prix_public: float | None = Field(default=None, gt=0, le=100000)
    stock_actuel: int | None = Field(default=None, ge=0, le=1000000)
    seuil: int | None = Field(default=None, ge=0, le=1000000)
    taux_remboursement: int | None = Field(default=None, ge=0, le=100)
    acteur: str = Field(default="pharmacien", max_length=60)


class Restock(BaseModel):
    quantite: int = Field(ge=1, le=1000000)
    acteur: str = Field(default="pharmacien", max_length=60)


def guarded(call) -> dict:
    try:
        result = call()
    except OfficineError as error:
        raise HTTPException(status_code=error.status, detail=error.message) from error
    return result


def page_size(limit: int) -> int:
    return min(max(limit, 1), 200)


@router.get("/overview")
def overview(days: int = 30) -> dict:
    return logic.overview(min(max(days, 1), 365))


@router.get("/products")
def products(q: str = "", category: str = "", limit: int = 80) -> dict:
    return logic.list_products(q, category, page_size(limit))


@router.post("/products")
def create_product(payload: ProductRequest) -> dict:
    return guarded(lambda: logic.create_product(payload.model_dump()))


@router.get("/products/{cip}/movements")
def movements(cip: str, limit: int = 30) -> dict:
    return guarded(lambda: returns.movements(cip, page_size(limit)))


@router.patch("/products/{cip}")
def update_product(cip: str, payload: ProductPatch) -> dict:
    return guarded(lambda: logic.update_product(cip, payload.model_dump(exclude_none=True)))


@router.post("/products/{cip}/restock")
def restock(cip: str, payload: Restock) -> dict:
    return guarded(lambda: logic.restock(cip, payload.quantite, payload.acteur))


@router.delete("/products/{cip}")
def delete_product(cip: str, acteur: str = "pharmacien") -> dict:
    return guarded(lambda: logic.delete_product(cip, acteur))


@router.get("/stock")
def stock(limit: int = 40) -> dict:
    return {"alerts": logic.alerts(page_size(limit)), "kpi": logic.kpi()}


@router.get("/sales")
def sales(statut: str = "", date_from: str = "", date_to: str = "", limit: int = 25, offset: int = 0) -> dict:
    return logic.sales_page(statut, page_size(limit), date_from, date_to, max(offset, 0))


@router.get("/sales/{sale_id}")
def sale(sale_id: int) -> dict:
    return guarded(lambda: {**logic.sale_detail(sale_id), "retours": returns.returns_of(sale_id)})


@router.get("/sales/{sale_id}/returns")
def sale_returns(sale_id: int) -> dict:
    return {"items": returns.returns_of(sale_id)}


@router.post("/sales")
def create_sale(payload: SaleRequest) -> dict:
    return guarded(lambda: logic.create_sale(payload.model_dump()))


@router.post("/sales/{sale_id}/return")
def create_return(sale_id: int, payload: ReturnRequest) -> dict:
    return guarded(lambda: returns.create_return({"sale_id": sale_id, **payload.model_dump()}))


@router.post("/sales/{sale_id}/cancel")
def cancel_sale(sale_id: int, acteur: str = "pharmacien") -> dict:
    return guarded(lambda: logic.cancel_sale(sale_id, acteur))


@router.get("/sales/{sale_id}/receipt", response_class=HTMLResponse)
def sale_receipt(sale_id: int) -> str:
    return receipt.receipt_html(sale_id)


@router.get("/reorder")
def reorder_plan(limit: int = 60) -> dict:
    return {"plan": reorder.plan(page_size(limit)), "recent": reorder.recent_orders(8)}


@router.post("/reorder")
def reorder_apply(payload: ReorderRequest) -> dict:
    return guarded(lambda: reorder.create_order(payload.model_dump()))


@router.get("/pharmacies")
def pharmacies() -> dict:
    return {"items": logic.pharmacies()}


@router.get("/journal")
def journal(limit: int = 20, action: str = "") -> dict:
    return {"items": logic.journal(page_size(limit), action)}


@router.get("/export/sales.csv")
def export_sales(date_from: str = "", date_to: str = "") -> Response:
    return Response(content=exports.sales_csv(date_from, date_to), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": 'attachment; filename="sales.csv"'})


@router.get("/export/products.csv")
def export_products() -> Response:
    return Response(content=exports.products_csv(), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": 'attachment; filename="products.csv"'})
