import sys, random
sys.path.insert(0, sys.argv[2])
import importlib.util
spec = importlib.util.spec_from_file_location("og", sys.argv[2] + "/scripts/og_saju_screen.py")
og = importlib.util.module_from_spec(spec); spec.loader.exec_module(og)
main, aux, _ = og.load_rows(sys.argv[1])
rng = random.Random(og.SEED)
occ = [r["occ"] for r in main]
dec = [r["y"] // 10 for r in main]
print("decade", og.perm_test(dec, occ, None, 200, rng))
cy = [r["cy"] for r in main]
print("country", og.perm_test(cy, occ, None, 200, rng))
