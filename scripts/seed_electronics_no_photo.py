"""One-off: seed 10 published electronics listings without photos."""
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from accounts.models import User
from listings.models import Post
from listings.services.ranking import calculate_rank_score
from listings.services.seo_urls import make_seo_slug
from locations.models import Settlement

ITEMS = [
    ("Смартфон Samsung A54", "Телефон в рабочем состоянии, без сколов. Комплект: коробка и зарядка. Торг.", 18500, "used"),
    ("iPhone 12 128 ГБ", "Батарея держит нормально, экран родной. Продаю после обновления.", 27900, "used"),
    ("Наушники Sony WH-1000XM4", "Шумодав работает, амбушюры целые. Чехол в комплекте.", 9900, "used"),
    ("Ноутбук Lenovo IdeaPad 15", "8/256, для учёбы и офиса. Без повреждений корпуса.", 24500, "used"),
    ("Планшет Xiaomi Pad 6", "Почти не пользовались, полный комплект документов.", 22000, "new"),
    ("Умные часы Amazfit GTR 4", "Ремешок новый, синхронизация с телефоном ок.", 6500, "used"),
    ("Колонка JBL Flip 6", "Громкий звук, влагозащита. Заряжается от USB-C.", 7800, "used"),
    ("Powerbank 20000 мАч", "Новый, в упаковке. Два выхода USB + Type-C.", 1900, "new"),
    ("Клавиатура и мышь Logitech", "Беспроводной комплект, батарейки в комплекте.", 3200, "used"),
    ("Монитор 24 дюйма Full HD", "IPS-матрица, HDMI кабель есть. Без битых пикселей.", 8900, "used"),
]


def main():
    user = (
        User.objects.filter(is_staff=False, is_blocked=False)
        .exclude(phone="")
        .order_by("id")
        .first()
    )
    if user is None:
        raise SystemExit("No suitable user found")

    settlement = (
        Settlement.objects.filter(is_active=True, name__iexact="Грозный").select_related("region").first()
        or Settlement.objects.filter(is_active=True, slug="grozny").select_related("region").first()
        or Settlement.objects.filter(is_active=True).select_related("region").order_by("-population").first()
    )
    if settlement is None:
        raise SystemExit("No settlement found")

    now = timezone.now()
    expiry = now + timedelta(days=getattr(settings, "POST_EXPIRY_DAYS", 30))
    created = []
    for title, body, price, condition in ITEMS:
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
            images=[],
            cover_index=0,
            has_photo=False,
            expires_at=expiry,
        )
        post.slug = make_seo_slug(title, settlement.slug)
        post.rank_score = calculate_rank_score(post)
        post.save()
        created.append(str(post.pk))

    print(f"created={len(created)} user={user.email} city={settlement.name} ids={','.join(created)}")


if __name__ == "__main__":
    main()
else:
    main()
