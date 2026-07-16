from django.db.models.signals import post_save
from django.dispatch import receiver

from listings.models import Post
from listings.services.search import index_post, remove_post_from_index


@receiver(post_save, sender=Post)
def sync_search_index(sender, instance: Post, **kwargs):
    if instance.status == "published":
        index_post(instance)
    else:
        remove_post_from_index(str(instance.pk))
