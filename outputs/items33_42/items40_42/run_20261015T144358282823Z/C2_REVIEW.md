# Item 42, check C2: manual review of the flagged lines

This review was added after the run. The automated scan flagged 4 lines; `item42_checks.json` holds the full text of each.

| File | Line | Term | Verdict |
|---|---|---|---|
| `outputs/items33_42/item33/run_20261013T162344038252Z/REPORT_ADDENDUM.md` | 143 | equivalen | Acceptable. It describes a numerically equivalent bootstrap computation (code equivalence that was checked against scikit-learn). It makes no claim that model performance is equivalent. |
| `outputs/phase3/run_20261013T140820817642Z/REPORT.md` | 45 | independent | Acceptable. "Few independent trajectories" is a limitation about units of evidence, not a claim of independent replication. |
| `outputs/phase3/run_20261013T140820817642Z/REPORT.md` | 55 | independent | Acceptable. Same limitation statement: "few independent event trajectories". |
| `outputs/phase3/run_20261013T140820817642Z/REPORT_ADDENDUM.md` | 4 | equivalen | Acceptable. It is a file name (`equivalence_check.json`, the Item 30 decision-equivalence count). |

Result: no over-stated conclusion was found, and no report needed a change.
