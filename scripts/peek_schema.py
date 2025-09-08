import json, pathlib
p = pathlib.Path("prompts/adjudicator_json_schema.json")
s = json.loads(p.read_text(encoding="utf-8"))
schema = s.get("schema") or s
props = schema.get("properties") or {}
print("Schema properties:", sorted(props.keys()))
print("Required:", schema.get("required"))
for k, v in props.items():
    print(f"- {k}: type={v.get('type')}, enum={v.get('enum')}")