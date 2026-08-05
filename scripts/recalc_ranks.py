from listings.services.ranking import recalculate_all_rank_scores
from listings.services.search import reindex_published_posts

n = recalculate_all_rank_scores()
print("recalc", n)
print("reindex", reindex_published_posts())
