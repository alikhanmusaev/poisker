from pathlib import Path
from io import BytesIO

from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from datetime import timedelta
from PIL import Image, ImageDraw

from accounts.models import User
from listings.models import Post
from listings.services.ranking import calculate_rank_score
from listings.services.seo_urls import make_seo_slug
from listings.services.storage import upload_image
from locations.models import Settlement

ITEMS = [
    (
        "Смартфон Xiaomi Redmi Note 12",
        "Телефон с хорошей камерой, аккумулятор держит весь день. Чехол в комплекте.",
        14900,
        "used",
        "#7c3aed",
        "Xiaomi",
    ),
    (
        "AirPods Pro 2",
        "Наушники в отличном состоянии, кейс без царапин. Работают с шумодавом.",
        12900,
        "used",
        "#2563eb",
        "AirPods",
    ),
]


def make_jpeg(color: str, label: str) -> bytes:
    img = Image.new("RGB", (800, 600), color)
    draw = ImageDraw.Draw(img)
    draw.rectangle([24, 24, 776, 576], outline="#ffffff", width=4)
    draw.text((48, 270), label, fill="#ffffff")
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=88)
    return buf.getvalue()


def main():
    user = (
        User.objects.filter(is_staff=False, is_blocked=False)
        .exclude(phone="")
        .order_by("id")
        .first()
    )
    if user is None:
        raise SystemExit("No user")

    settlement = (
        Settlement.objects.filter(is_active=True, name__iexact="Грозный")
        .select_related("region")
        .first()
        or Settlement.objects.filter(is_active=True, slug="grozny")
        .select_related("region")
        .first()
        or Settlement.objects.filter(is_active=True)
        .select_related("region")
        .order_by("-population")
        .first()
    )
    if settlement is None:
        raise SystemExit("No settlement")

    now = timezone.now()
    expiry = now + timedelta(days=getattr(settings, "POST_EXPIRY_DAYS", 30))
    created = []
    for title, body, price, condition, color, label in ITEMS:
        raw = make_jpeg(color, label)
        uploaded = SimpleUploadedFile(
            f"{label.lower().replace(' ', '-')}.jpg",
            raw,
            content_type="image/jpeg",
        )
        image_url = upload_image(uploaded)
        post = Post(
            user=user,
            title=title,
            body=body,
            category="elektronika",
            city=settlement.slug,
            settlement=settlement,
            condition=condition,
            price=price,
            contact_phone=user.phone,
            status="published",
            ever_published=True,
            published_at=now,
            images=[image_url],
            cover_index=0,
            has_photo=True,
            expires_at=expiry,
        )
        post.slug = make_seo_slug(title, settlement.slug)
        post.rank_score = calculate_rank_score(post)
        post.save()
        created.append(f"{post.pk}:{image_url}")

    print("created", len(created))
    for row in created:
        print(row)


if __name__ == "__main__":
    main()
else:
    main()
