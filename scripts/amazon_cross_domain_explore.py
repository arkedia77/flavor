"""탐색(사전등록 밖, 결과 본 뒤 작성): 식품 축을 하위 묶음으로 나눠 음악·영화 강도와 대 본다.

    python3 -I scripts/amazon_cross_domain_explore.py scripts <meta_g> <rev_g> <meta_c> <rev_c> <meta_m> <rev_m> <out.json>
"""
import json, random, re, sys
sys.path.insert(0, sys.argv[1])
import amazon_cross_domain as X
from amazon_transfer import direction
mg, rg, mc, rc, mm, rm, out = sys.argv[2:9]
SUB = {
 "spicy": (re.compile(r"\b(extra hot|spicy|habanero|ghost pepper)\b"), re.compile(r"\bmild\b")),
 "coffee": (re.compile(r"\b(dark|french|italian|espresso) roast\b"), re.compile(r"\b(light|blonde|cinnamon) roast\b")),
 "choc": (re.compile(r"\bdark chocolate\b|\b(70|72|85|90)\s?% cacao\b"), re.compile(r"\bmilk chocolate\b")),
}
music = X.classify_cats(mc, X.MUSIC_A, X.MUSIC_B)
movie = X.classify_cats(mm, X.MOVIE_A, X.MOVIE_B)
ml, _, _, _ = X.liked(rc, music); vl, _, _, _ = X.liked(rm, movie)
M = {u: d for u, c in ml.items() if (d := direction(c))}
V = {u: d for u, c in vl.items() if (d := direction(c))}
X.B = 2000
res = {}
for k, (pa, pb) in SUB.items():
    food, _ = X.classify_title(mg, pa, pb)
    fl, _, _, _ = X.liked(rg, food)
    F = {u: d for u, c in fl.items() if (d := direction(c))}
    res[k] = {"music": X.test(F, M, random.Random(1)), "movie": X.test(F, V, random.Random(2))}
json.dump(res, open(out, "w"), ensure_ascii=False, indent=1)
for k, v in res.items():
    for t, r in v.items():
        print(k, t, r["n"], r["cells"], r["odds_ratio"], r["p_one_sided"])
