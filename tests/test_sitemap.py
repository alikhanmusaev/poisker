"""Sitemap excludes non-public posts."""

from tests.conftest import create_test_post


def test_sitemap_excludes_deleted_post(client, app):
    from app.services.posts import delete_post

    with app.app_context():
        post = create_test_post(app, publish=True, phone="+79005556677")
        public_url = f"/obyavlenie/{post.city}/{post.category}/{post.slug}"
        slug = post.slug
        delete_post(post)

    text = client.get("/sitemap.xml").get_data(as_text=True)
    assert public_url not in text
    assert slug not in text
