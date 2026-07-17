from django.core.management.base import BaseCommand

from listings.models import Post
from listings.services.storage import ensure_image_variants


class Command(BaseCommand):
    help = "Create or recompress image variants (full/sm JPEG+WebP) for listing photos."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=0, help="Max posts to process (0 = all)")
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-encode existing variants with current quality/size settings",
        )

    def handle(self, *args, **options):
        qs = Post.objects.exclude(images=[]).order_by("id")
        limit = options["limit"]
        force = bool(options["force"])
        if limit:
            qs = qs[:limit]
        posts = 0
        written = 0
        errors = 0
        for post in qs.iterator():
            posts += 1
            for url in post.images or []:
                try:
                    written += ensure_image_variants(url, force=force)
                except Exception as exc:
                    errors += 1
                    self.stderr.write(f"fail {post.pk} {url}: {exc}")
        self.stdout.write(
            self.style.SUCCESS(
                f"posts={posts} variants_written={written} errors={errors} force={force}"
            )
        )
