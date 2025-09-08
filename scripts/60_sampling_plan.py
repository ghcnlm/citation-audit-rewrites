import pandas as pd
import yaml
from pathlib import Path

CONFIG = yaml.safe_load(open("config/config.yaml","r",encoding="utf-8"))
OUT_DIR = Path(CONFIG["paths"]["outputs_dir"])

CCP = OUT_DIR/"ccp_registry.csv"
ADJ = OUT_DIR/"adjudications.csv"
PLAN = OUT_DIR/"sampling_plan.csv"

LOW_SAMPLE_FRACTION = 0.3
FAIL_REVIEW_ESCALATE_THRESHOLD = 0.05

def main():
    ccp = pd.read_csv(CCP)
    adj = pd.read_csv(ADJ) if ADJ.exists() else pd.DataFrame(columns=["claim_id","verdict","section","review_id"])

    if not adj.empty:
        adj["is_bad"] = adj["verdict"].isin(["UNSUPPORTED_FAIL","AMBIGUOUS_REVIEW"])
        rates = adj.groupby(["review_id","section"])["is_bad"].mean().reset_index().rename(columns={"is_bad":"bad_rate"})
    else:
        rates = pd.DataFrame(columns=["review_id","section","bad_rate"])

    plan_rows = []
    for (rid, sec), group in ccp.groupby(["review_id","section"]):
        high = group[group["priority"]=="High"]
        low  = group[group["priority"]=="Low"]

        n_sample = max(10, int(len(low)*LOW_SAMPLE_FRACTION)) if len(low)>0 else 0
        low_sample = low.sample(n=min(n_sample, len(low)), random_state=42) if n_sample>0 else low.iloc[0:0]

        bad_rate = rates[(rates["review_id"]==rid)&(rates["section"]==sec)]["bad_rate"]
        escalate = (not bad_rate.empty) and (bad_rate.values[0] > FAIL_REVIEW_ESCALATE_THRESHOLD)
        include = pd.concat([high, low_sample], ignore_index=True)
        include["escalate_to_full_section"] = bool(escalate)
        for _, r in include.iterrows():
            plan_rows.append({
                "review_id": rid,
                "section": sec,
                "claim_id": r["claim_id"],
                "priority": r["priority"],
                "escalate_to_full_section": bool(escalate)
            })

    pd.DataFrame(plan_rows).to_csv(PLAN, index=False)
    print(f"[OK] wrote sampling plan -> {PLAN}")

if __name__ == "__main__":
    main()
