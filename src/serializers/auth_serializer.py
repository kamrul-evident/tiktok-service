from typing import Optional
from pydantic import BaseModel


class AuthRequest(BaseModel):
    auth_code: str
    name: str
    shop_id: Optional[str] = None
    country: str
    company_uid: str
