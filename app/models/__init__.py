import uuid
from datetime import datetime, timezone

from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class Post(db.Model):
    __tablename__ = "posts"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(200), nullable=False)
    seller_name = db.Column(db.String(80), nullable=False, default="")
    body = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False, index=True)
    city = db.Column(db.String(50), nullable=False, index=True)
    price = db.Column(db.Integer, nullable=True)
    phone_hash = db.Column(db.String(64), nullable=False, index=True)
    phone_masked = db.Column(db.String(20), nullable=False)
    phone_encrypted = db.Column(db.Text, nullable=True)
    edit_token = db.Column(db.String(64), unique=True, nullable=False, index=True)
    slug = db.Column(db.String(120), nullable=True, unique=True, index=True)
    status = db.Column(db.String(20), nullable=False, default="published", index=True)
    images = db.Column(db.JSON, nullable=False, default=list)
    cover_index = db.Column(db.Integer, nullable=False, default=0)
    pending_revision = db.Column(db.JSON, nullable=True)
    ip_hash = db.Column(db.String(64), nullable=True)
    views = db.Column(db.Integer, nullable=False, default=0)
    contact_clicks = db.Column(db.Integer, nullable=False, default=0)
    reports_count = db.Column(db.Integer, nullable=False, default=0)
    rank_score = db.Column(db.Float, nullable=False, default=0.0, index=True)
    has_photo = db.Column(db.Boolean, nullable=False, default=False)
    paid_until = db.Column(db.DateTime(timezone=True), nullable=True)
    paid_boost = db.Column(db.Float, nullable=False, default=1.0)
    bumped_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=True)
    deleted_at = db.Column(db.DateTime(timezone=True), nullable=True)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False, index=True)

    reports = db.relationship("Report", backref="post", lazy="dynamic", cascade="all, delete-orphan")
    promotions = db.relationship("Promotion", backref="post", lazy="dynamic", cascade="all, delete-orphan")

    __table_args__ = (
        db.Index("ix_posts_city_category_rank", "city", "category", "rank_score"),
        db.Index("ix_posts_phone_created", "phone_hash", "created_at"),
        db.Index("ix_posts_status_expires", "status", "expires_at"),
    )

    @property
    def is_promoted(self):
        if not self.paid_until:
            return False
        return self.paid_until > utcnow()

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "seller_name": self.seller_name,
            "body": self.body,
            "category": self.category,
            "city": self.city,
            "price": self.price,
            "phone_masked": self.phone_masked,
            "status": self.status,
            "images": self.images or [],
            "views": self.views,
            "contact_clicks": self.contact_clicks,
            "reports_count": self.reports_count,
            "rank_score": self.rank_score,
            "has_photo": self.has_photo,
            "paid_boost": self.paid_boost,
            "created_at": int(self.created_at.timestamp()) if self.created_at else 0,
            "expires_at": int(self.expires_at.timestamp()) if self.expires_at else 0,
        }


class Report(db.Model):
    __tablename__ = "reports"

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.String(36), db.ForeignKey("posts.id"), nullable=False, index=True)
    reason = db.Column(db.String(50), nullable=False)
    comment = db.Column(db.Text, nullable=True)
    ip_hash = db.Column(db.String(64), nullable=True)
    status = db.Column(db.String(20), nullable=False, default="new", index=True)
    reviewed_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class Promotion(db.Model):
    __tablename__ = "promotions"

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.String(36), db.ForeignKey("posts.id"), nullable=False, index=True)
    type = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), nullable=False, default="pending", index=True)
    payment_ref = db.Column(db.String(100), nullable=True)
    starts_at = db.Column(db.DateTime(timezone=True), nullable=True)
    ends_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class BlockedPhone(db.Model):
    __tablename__ = "blocked_phones"

    id = db.Column(db.Integer, primary_key=True)
    phone_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)
    reason = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class PhoneDailyPublish(db.Model):
    __tablename__ = "phone_daily_publishes"

    id = db.Column(db.Integer, primary_key=True)
    phone_hash = db.Column(db.String(64), nullable=False, index=True)
    publish_date = db.Column(db.Date, nullable=False)
    post_id = db.Column(db.String(36), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    __table_args__ = (db.UniqueConstraint("phone_hash", "publish_date", name="uq_phone_daily_publish"),)


class AdminUser(db.Model):
    __tablename__ = "admin_users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)

    audit_logs = db.relationship("AdminAuditLog", backref="admin", lazy="dynamic")

    def get_id(self):
        return str(self.id)

    @property
    def is_authenticated(self):
        return True

    @property
    def is_active(self):
        return True

    @property
    def is_anonymous(self):
        return False

    def set_password(self, password):
        from werkzeug.security import generate_password_hash

        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        from werkzeug.security import check_password_hash

        return check_password_hash(self.password_hash, password)


class AdminAuditLog(db.Model):
    __tablename__ = "admin_audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey("admin_users.id"), nullable=False, index=True)
    action = db.Column(db.String(50), nullable=False)
    target_type = db.Column(db.String(50), nullable=False)
    target_id = db.Column(db.String(64), nullable=False)
    ip_hash = db.Column(db.String(64), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)
