# import uuid

# from sqlalchemy import (
#     Column,
#     DateTime,
#     ForeignKey,
#     Integer,
#     String,
#     BigInteger
# )
# from sqlalchemy.dialects.postgresql import UUID
# from sqlalchemy.orm import relationship
# from sqlalchemy.sql import func

# from config.database import Base


# class Token(Base):
#     __tablename__ = "tokens"

#     id = Column(
#         UUID(as_uuid=True),
#         primary_key=True,
#         nullable=False,
#         index=True,
#         unique=True,
#         default=uuid.uuid4(),
#     )
#     channel = Column(String(32), ForeignKey("channels.channel_uid"), unique=True)
#     access_token = Column(String(500), nullable=False)
#     refresh_token = Column(String(500), nullable=False)
#     access_token_expiry = Column(BigInteger, nullable=False)
#     refresh_token_expiry = Column(BigInteger, nullable=False)
#     created_at = Column(DateTime, default=func.now())
#     updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

#     channelTokenRef = relationship("Channel", back_populates="tokens")
