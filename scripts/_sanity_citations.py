import sys
from pprint import pprint

sys.path.insert(0, "src")
from audit_lib.citations import parse_citations

samples = [
    "This was previously shown (Smith, 2020).",
    "As demonstrated by Smith and Lee (2020), the method works.",
    "The effect is robust (O’Connor, 2019, pp. 12–15).",
    "Prior work (Doe, 2018, as cited in Roe, 2021, p. 3) supports this.",
    "Johnson et al. (2017) argue this point.",
]

for s in samples:
    print("--", s)
    res = parse_citations(s)
    for r in res:
        print(r)
    print()

