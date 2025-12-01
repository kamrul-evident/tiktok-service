from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from config.database import Base


class InventoryRequest(Base):
    __tablename__ = "inventoryrequests"

    id = Column(
        BigInteger,
        nullable=False,
        primary_key=True,
        index=True,
        unique=True,
        autoincrement="auto",
    )
    channel_uid = Column(String(32), ForeignKey("channels.channel_uid"))
    sku = Column(String(64), nullable=False)
    item_id = Column(String(64), nullable=False)
    quantity = Column(Integer, nullable=False)
    status = Column(String(16), nullable=False, default="PENDING")
    request_id = Column(String(64))
    feed_id = Column(String(16))
    request_metadata = Column(JSON)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    channelInventoryRef = relationship("Channel", back_populates="inventoryrequests")

    class StatusChoices:
        PENDING = "PENDING"
        SUCCESS = "SUCCESS"
        IN_QUEUE = "IN_QUEUE"
        PROCESSING = "PROCESSING"
        DONE = "DONE"
        FAILED = "FAILED"
        WARNING = "WARNING"
