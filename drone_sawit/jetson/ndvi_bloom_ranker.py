# ndvi_bloom_ranker.py – Rank trees by NDVI for prioritization
def rank_trees_by_ndvi(trees, ndvi_scores):
    enriched = []
    for tree in trees:
        score = ndvi_scores.get(tree["id"], 0)
        tree["ndvi"] = score
        enriched.append(tree)
    enriched.sort(key=lambda x: -x["ndvi"])
    return enriched
