import os
import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Boolean, JSON, ForeignKey, Text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

# Setup the DB URL. Default to PostgreSQL, but gracefully fallback to SQLite for sandbox/testing.
DATABASE_URL = os.environ.get("TRADEYAR_DATABASE_URL", "sqlite:///runtime_logs/product_data.db")

# Create engine & sessionmaker
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Role model (RBAC)
class Role(Base):
    __tablename__ = "roles"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False) # SuperAdmin, Admin, Researcher, User, Guest

# User model
class User(Base):
    __tablename__ = "users"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(100), nullable=False)
    role_id = Column(Integer, ForeignKey("roles.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    role = relationship("Role")
    preferences = relationship("UserPreference", uselist=False, back_populates="user")

# User preferences model
class UserPreference(Base):
    __tablename__ = "user_preferences"
    user_id = Column(String(36), ForeignKey("users.id"), primary_key=True)
    language = Column(String(10), default="fa") # fa, en, ar, tr
    theme = Column(String(20), default="dark") # dark, light, custom

    user = relationship("User", back_populates="preferences")

# Blog Article model
class BlogArticle(Base):
    __tablename__ = "blog_articles"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    slug = Column(String(100), unique=True, index=True, nullable=False)
    title_json = Column(JSON, nullable=False) # e.g. {"fa": "...", "en": "..."}
    content_json = Column(JSON, nullable=False) # e.g. {"fa": "...", "en": "..."}
    category = Column(String(50), nullable=False)
    tags = Column(JSON, nullable=False) # e.g. ["Market", "AI"]
    seo_meta = Column(JSON, nullable=False) # e.g. {"description": "...", "keywords": "..."}
    created_at = Column(DateTime, default=datetime.utcnow)

# System Audit Log model
class SystemAuditLog(Base):
    __tablename__ = "system_audit_logs"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), nullable=True)
    action = Column(String(100), nullable=False)
    details = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)


# Redis Cache Fallback (for environments without a running Redis server)
class MockRedis:
    def __init__(self):
        self._data = {}

    def get(self, key):
        return self._data.get(key)

    def set(self, key, value, ex=None):
        self._data[key] = value

    def delete(self, key):
        self._data.pop(key, None)

    def flushall(self):
        self._data.clear()


class RedisClient:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RedisClient, cls).__new__(cls)
            redis_host = os.environ.get("TRADEYAR_REDIS_HOST", "localhost")
            redis_port = int(os.environ.get("TRADEYAR_REDIS_PORT", 6379))
            try:
                import redis
                cls._instance.client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
                cls._instance.client.ping()
                cls._instance.is_mock = False
            except Exception:
                # Graceful fallback to MockRedis
                cls._instance.client = MockRedis()
                cls._instance.is_mock = True
        return cls._instance


def init_db():
    """Initializes the database, creating all tables and default roles."""
    os.makedirs("runtime_logs", exist_ok=True)
    Base.metadata.create_all(bind=engine)

    # Populate default roles and a dummy admin/user if they don't exist
    db = SessionLocal()
    try:
        roles_count = db.query(Role).count()
        if roles_count == 0:
            for rname in ["SuperAdmin", "Admin", "Researcher", "User", "Guest"]:
                db.add(Role(name=rname))
            db.commit()

        # Add pre-seeded blog articles for CMS testing/verification
        articles_count = db.query(BlogArticle).count()
        if articles_count == 0:
            import bcrypt
            # Seed default admin user
            admin_role = db.query(Role).filter(Role.name == "Admin").first()
            if admin_role:
                admin_pwd = bcrypt.hashpw("admin123".encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                admin_user = User(
                    id="usr-admin-default-id",
                    email="admin@tradeyar.ai",
                    password_hash=admin_pwd,
                    role_id=admin_role.id
                )
                db.add(admin_user)
                db.add(UserPreference(user_id=admin_user.id, language="fa", theme="dark"))

            # Seed pre-seeded articles
            db.add(BlogArticle(
                slug="tradeyar-cognitive-paradigm",
                title_json={
                    "fa": "پارادایم شناختی هوش معامله‌گر TradeYar",
                    "en": "TradeYar Trader Brain Cognitive Paradigm",
                    "ar": "النموذج المعرفي لدماغ المتداول TradeYar",
                    "tr": "TradeYar Yatırımcı Beyni Bilişsel Paradigması"
                },
                content_json={
                    "fa": "هوش مصنوعی TradeYar بر پایه سیستم تصمیم‌گیری مستقل و تحلیل بدون اندیکاتورهای کلاسیک بنا شده است.",
                    "en": "TradeYar AI is built upon an autonomous decision-making framework, entirely devoid of classical technical indicators.",
                    "ar": "يعتمد ذكاء TradeYar على نظام اتخاذ القرار المستقل والتحليل الخالي من المؤشرات الكلاسيكية.",
                    "tr": "TradeYar yapay zekası, klasik teknik göstergelerden tamamen arındırılmış, bağımsız bir karar verme yapısı üzerine kurulmuştur."
                },
                category="Research",
                tags=["AI", "Cognitive", "No-Indicators"],
                seo_meta={"description": "TradeYar Cognitive Paradigm article", "keywords": "AI, Cognitive, TradeYar"}
            ))
            db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()
