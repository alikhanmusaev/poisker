from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

from core.phone import normalize_phone, phone_digits


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError("Email обязателен")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """Registered seller account — email login, display name, phone for listings."""

    username = None
    email = models.EmailField("Email", unique=True)
    display_name = models.CharField("Имя", max_length=80)
    phone = models.CharField("Телефон", max_length=20)
    phone_digits = models.CharField("Телефон (цифры)", max_length=11, unique=True, editable=False)
    phone_verified = models.BooleanField(default=False)
    is_blocked = models.BooleanField("Заблокирован", default=False, db_index=True)
    rating_avg = models.FloatField("Средняя оценка", default=0.0)
    rating_count = models.PositiveIntegerField("Число отзывов", default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = ["display_name"]

    objects = UserManager()

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"

    def __str__(self):
        return self.display_name or self.email

    @property
    def seller_name(self):
        return self.display_name

    def save(self, *args, **kwargs):
        if self.phone:
            self.phone = normalize_phone(self.phone)
            self.phone_digits = phone_digits(self.phone)
        super().save(*args, **kwargs)
