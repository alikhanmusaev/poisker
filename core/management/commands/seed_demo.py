from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User
from listings.constants import CATEGORIES
from listings.models import Post
from listings.services.demo_assets import demo_image_for, ensure_demo_images
from listings.services.ranking import calculate_rank_score
from listings.services.seo_urls import make_seo_slug

SAMPLE_POSTS = [
    ("2-к квартира, пр. Путина", "nedvizhimost", "grozny", 4_500_000, 1),
    ("Toyota Camry 2018, 2.5 AT", "avto", "grozny", 1_850_000, 2),
    ("iPhone 14 Pro 256 ГБ", "elektronika", "gudermes", 75_000, 0),
    ("Угловой диван, б/u", "dlya-doma", "argun", 25_000, 3),
    ("Ремонт квартир под ключ", "uslugi", "grozny", None, 4),
    ("Продавец в продуктовый магазин", "rabota", "urus-martan", 45_000, 5),
    ("Щенки немецкой овчарки", "zhivotnye", "shali", 15_000, 2),
    ("Кроссовки Nike, 42 размер", "prodazha", "grozny", 5_500, 1),
    ("Бензопила Stihl MS 180", "stroitelstvo", "kurchaloy", 12_000, 6),
    ("Детская коляска 3 в 1", "detskie", "naurskaya", 8_000, 7),
    ("Запчасти на ВАЗ 2114", "zapchasti", "grozny", 3_000, 3),
    ("Фикус и монстера в горшках", "rasteniya", "shelkovskaya", 1_200, 2),
    ("Свежие овощи с огорода", "produkti", "shatoy", 500, 0),
    ("Магазин одежды — готовый бизнес", "biznes", "grozny", 800_000, 10),
    ("Горный велосипед 26″", "sport", "achkhoy-martan", 18_000, 4),
    ("Сдам гараж на длительный срок", "drugoe", "goyty", 5_000, 5),
]


class Command(BaseCommand):
    help = "Seed demo listings with images for development"

    def add_arguments(self, parser):
        parser.add_argument("--force", action="store_true", help="Recreate demo posts")

    def handle(self, *args, **options):
        images_created = ensure_demo_images()
        self.stdout.write(f"Demo images ready ({images_created} new)")

        user, _ = User.objects.get_or_create(
            email="demo@poisker.local",
            defaults={"display_name": "Демо продавец", "phone": "+7 (999) 000-00-01"},
        )
        if not user.has_usable_password():
            user.set_password("demo12345")
            user.save()

        if options["force"]:
            Post.objects.filter(user=user).delete()

        if Post.objects.exclude(user=user).filter(status="published").exists():
            hidden = Post.objects.filter(user=user, status="published").update(status="hidden")
            if hidden:
                self.stdout.write(f"Skipped demo listings ({hidden} hidden — site already has real posts)")
            return

        created = 0
        now = timezone.now()
        for title, category, city, price, days_ago in SAMPLE_POSTS:
            if Post.objects.filter(user=user, title=title).exists():
                post = Post.objects.get(user=user, title=title)
                if not post.images:
                    post.images = [demo_image_for(category)]
                    post.has_photo = True
                    post.save(update_fields=["images", "has_photo"])
                continue
            post = Post(
                user=user,
                title=title,
                body=f"Демо-объявление «{title}» для локальной разработки.",
                category=category,
                city=city,
                price=price,
                contact_phone=user.phone,
                status="published",
                images=[demo_image_for(category)],
                has_photo=True,
                created_at=now - timedelta(days=days_ago),
                expires_at=now + timedelta(days=30),
            )
            post.slug = make_seo_slug(title, city)
            post.rank_score = calculate_rank_score(post)
            post.save()
            created += 1

        self.stdout.write(self.style.SUCCESS(f"Demo posts created: {created}"))
