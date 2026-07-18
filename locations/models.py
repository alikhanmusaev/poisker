from django.db import models
from django.utils import timezone as django_timezone
from django.utils.text import slugify as django_slugify


def _slugify_ru(value: str) -> str:
    """Transliterate-friendly slug; falls back to django slugify."""
    from locations.slugify import slugify_ru

    return slugify_ru(value) or django_slugify(value, allow_unicode=False) or "location"


class Region(models.Model):
    name = models.CharField("Название", max_length=120, unique=True)
    slug = models.SlugField("Slug", max_length=120, unique=True)
    code = models.CharField("Код GeoNames", max_length=16, unique=True, db_index=True)
    federal_district = models.CharField(
        "Федеральный округ",
        max_length=80,
        blank=True,
        default="",
    )
    geoname_id = models.PositiveIntegerField(null=True, blank=True, unique=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(default=django_timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["slug"]),
            models.Index(fields=["code"]),
        ]
        verbose_name = "Регион"
        verbose_name_plural = "Регионы"

    def __str__(self):
        return self.name


class Settlement(models.Model):
    region = models.ForeignKey(
        Region,
        on_delete=models.PROTECT,
        related_name="settlements",
        verbose_name="Регион",
    )
    name = models.CharField("Название", max_length=160, db_index=True)
    slug = models.SlugField("Slug", max_length=160)
    type = models.CharField("Тип", max_length=64, blank=True, default="населённый пункт")
    geoname_id = models.PositiveIntegerField(null=True, blank=True, unique=True, db_index=True)
    fias_id = models.CharField(max_length=36, blank=True, default="", db_index=True)
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    population = models.PositiveIntegerField(default=0, db_index=True)
    timezone = models.CharField(max_length=64, blank=True, default="")
    is_active = models.BooleanField(default=True, db_index=True)
    is_popular = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(default=django_timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["region", "slug"],
                name="unique_settlement_slug_per_region",
            ),
        ]
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["region", "name"]),
            models.Index(fields=["region", "is_active", "population"]),
            models.Index(fields=["is_popular", "population"]),
        ]
        verbose_name = "Населённый пункт"
        verbose_name_plural = "Населённые пункты"

    def __str__(self):
        return f"{self.name}, {self.region.name}"

    @property
    def display_name(self) -> str:
        return f"{self.name}, {self.region.name}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = _slugify_ru(self.name)
        super().save(*args, **kwargs)
