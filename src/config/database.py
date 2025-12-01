# from core.query_manager import SoftDeleteQueryManager
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from config.app_vars import DB_HOST, DB_NAME, DB_PASS, DB_PORT, DB_USER

POSTGRES_URL = f"postgresql+psycopg://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

engine = create_engine(POSTGRES_URL)


def get_db():
    db = Session(bind=engine)
    try:
        yield db
    finally:
        db.close()


# class SoftDeleteSession(Session):
#     """
#     Custom session to override the delete() method for soft deletion.
#     """
#     def delete(self, instance):
#         from models.project import Project
#         # Check if the instance has the soft delete fields
#         if hasattr(instance, 'deleted_at'):
#             # Perform soft delete
#             instance.deleted_at = datetime.now(timezone.utc)
#             if isinstance(instance,Project):
#                 instance.status='ARCHIVED'
#             self.commit()  # Commit the soft delete change
#         else:
#             # Fallback to hard delete if the model doesn't support soft deletion
#             super().delete(instance)

# Session = sessionmaker(bind=engine,query_cls=SoftDeleteQueryManager, class_=SoftDeleteSession)
# Session = sessionmaker(bind=engine)

Base = declarative_base()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
