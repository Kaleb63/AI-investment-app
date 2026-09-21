import asyncio
from typing import Any

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.dependencies import get_current_user
from backend.errors import AppError
from backend.models import PlaidItem, User
from backend.schemas.plaid import PlaidConnectionResponse, PublicTokenRequest
from backend.services.plaid_service import plaid_service
from backend.services.portfolio_service import portfolio_service
from backend.services.security_service import decrypt_secret, encrypt_secret

router = APIRouter(tags=["plaid and portfolios"])


def _user_items(db: Session, user_id: str) -> list[PlaidItem]:
    return list(
        db.scalars(
            select(PlaidItem).where(
                PlaidItem.user_id == user_id,
                PlaidItem.connection_status == "active",
            )
        )
    )


async def _all_holdings(db: Session, user: User) -> list[dict[str, Any]]:
    items = _user_items(db, user.id)
    if not items:
        raise AppError(
            "plaid_not_connected",
            "Connect a Plaid investment account first",
            400,
        )

    responses = await asyncio.gather(
        *(
            plaid_service.get_holdings(decrypt_secret(item.encrypted_access_token))
            for item in items
        ),
        return_exceptions=True,
    )
    holdings = []
    successful_responses = 0
    for item, response in zip(items, responses, strict=True):
        if isinstance(response, Exception):
            item.connection_status = "error"
            continue
        successful_responses += 1
        holdings.extend(plaid_service.clean_holdings(response))
        item.account_metadata = [
            {
                "account_id": account.get("account_id"),
                "name": account.get("name"),
                "type": account.get("type"),
                "subtype": account.get("subtype"),
            }
            for account in response.get("accounts", [])
        ]
    db.commit()
    if successful_responses == 0:
        raise AppError(
            "plaid_holdings_unavailable",
            "Holdings could not be retrieved from any connected account",
            502,
        )
    return holdings


@router.post("/create_link_token", summary="Create a Plaid Link token")
async def create_link_token(user: User = Depends(get_current_user)):
    return {"link_token": await plaid_service.create_link_token(user.id)}


@router.post("/sandbox_public_token", summary="Create a Plaid sandbox public token")
async def sandbox_public_token(_user: User = Depends(get_current_user)):
    return {"public_token": await plaid_service.create_sandbox_public_token()}


@router.post(
    "/exchange_public_token",
    response_model=PlaidConnectionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Exchange and securely store a Plaid public token",
)
async def exchange_public_token(
    request: PublicTokenRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    exchanged = await plaid_service.exchange_public_token(request.public_token)
    existing = db.scalar(select(PlaidItem).where(PlaidItem.plaid_item_id == exchanged["item_id"]))
    if existing is not None and existing.user_id != user.id:
        raise AppError("plaid_item_conflict", "Plaid item is already connected", 409)

    item = existing or PlaidItem(
        user_id=user.id,
        plaid_item_id=exchanged["item_id"],
        encrypted_access_token="",
    )
    item.encrypted_access_token = encrypt_secret(exchanged["access_token"])
    item.institution_id = request.institution_id
    item.institution_name = request.institution_name
    item.connection_status = "active"
    db.add(item)
    db.commit()
    db.refresh(item)
    return {
        "id": item.id,
        "item_id": item.plaid_item_id,
        "institution_id": item.institution_id,
        "institution_name": item.institution_name,
        "connection_status": item.connection_status,
    }


@router.get(
    "/plaid/connections",
    response_model=list[PlaidConnectionResponse],
    summary="List the signed-in user's Plaid connections",
)
def list_connections(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return [
        {
            "id": item.id,
            "item_id": item.plaid_item_id,
            "institution_id": item.institution_id,
            "institution_name": item.institution_name,
            "connection_status": item.connection_status,
        }
        for item in db.scalars(select(PlaidItem).where(PlaidItem.user_id == user.id))
    ]


@router.delete("/plaid/connections/{connection_id}", status_code=204)
def remove_connection(
    connection_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.scalar(
        select(PlaidItem).where(
            PlaidItem.id == connection_id,
            PlaidItem.user_id == user.id,
        )
    )
    if item is None:
        raise AppError("plaid_item_not_found", "Plaid connection was not found", 404)
    db.delete(item)
    db.commit()


@router.get("/holdings", summary="Retrieve cleaned Plaid holdings")
@router.get("/plaid_portfolio", summary="Retrieve the user's Plaid portfolio")
async def holdings(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return {"portfolio": await _all_holdings(db, user)}


@router.get("/portfolio", summary="Calculate portfolio allocations and concentration")
@router.get("/portfolio_analysis", summary="Analyze the signed-in user's portfolio")
async def portfolio_analysis(
    include_ai: bool = Query(default=False),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    holdings_data = await _all_holdings(db, user)
    return await portfolio_service.analyze(
        holdings_data,
        include_ai=include_ai,
    )
