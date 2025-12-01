import random
import string

from sqlalchemy import BigInteger, Column, DateTime, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from config.database import Base


class Channel(Base):
    __tablename__ = "channels"

    @staticmethod
    def gen_channel_uid():
        letters_and_digits = string.ascii_letters + string.digits
        result_str = "".join((random.choice(letters_and_digits) for i in range(15)))
        # print("Random alphanumeric String is:", result_str)
        return result_str

    # id = Column(BigInteger, primary_key=True,  nullable=False, index=True, unique=True, autoincrement='auto')
    channel_uid = Column(
        String(32),
        primary_key=True,
        nullable=False,
        index=True,
        unique=True,
        default=gen_channel_uid(),
    )
    company_uuid = Column(String(64))
    name = Column(String(128), nullable=False)
    country = Column(String(128))
    shop_id = Column(BigInteger, nullable=False)
    shop_cipher = Column(String, unique=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    # tokens = relationship(
    #     "Token",
    #     uselist=False,
    #     back_populates="channelTokenRef",
    #     cascade="all, delete-orphan",
    # )
    access_token = Column(String(500), nullable=True)
    refresh_token = Column(String(500), nullable=True)
    access_token_expiry = Column(BigInteger, nullable=True)
    refresh_token_expiry = Column(BigInteger, nullable=True)

    inventoryrequests = relationship(
        "InventoryRequest", back_populates="channelInventoryRef"
    )
