from pydantic import BaseModel


class PublicTokenRequest(BaseModel):
    public_token: str
    institution_id: str | None = None
    institution_name: str | None = None


class PlaidConnectionResponse(BaseModel):
    id: str
    item_id: str
    institution_id: str | None
    institution_name: str | None
    connection_status: str
