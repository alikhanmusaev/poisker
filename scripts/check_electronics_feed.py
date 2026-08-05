from django.utils import timezone
from listings.models import Post
from listings.services.search import search_posts, index_post

now = timezone.now()
qs = Post.objects.filter(category="elektronika").order_by("-created_at")[:20]
print("now", now)
print("elektronika_published", Post.objects.filter(category="elektronika", status="published").count())
print("no_photo_published", Post.objects.filter(category="elektronika", status="published", has_photo=False).count())
for p in qs:
    live = p.status == "published" and p.expires_at and p.expires_at > now
    print("POST", p.pk, p.status, live, p.title[:40], "city=", p.city, "photo=", p.has_photo, "exp=", p.expires_at)

results, total = search_posts(query="", category="elektronika", limit=50, offset=0)
print("search_total", total)
print("search_titles", [getattr(r, "title", r) for r in results[:15]])

# reindex recent no-photo
fixed = 0
for p in Post.objects.filter(category="elektronika", status="published", has_photo=False).order_by("-created_at")[:20]:
    try:
        index_post(p)
        fixed += 1
    except Exception as e:
        print("index_fail", p.pk, e)
print("reindexed", fixed)
results2, total2 = search_posts(query="", category="elektronika", limit=50, offset=0)
print("search_total_after", total2)
