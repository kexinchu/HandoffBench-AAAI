"""One-off audited migration for semantically grounded negative-state reasons."""

from __future__ import annotations

import json
from pathlib import Path


PATH = Path(__file__).parents[1] / "data/tasks/dev/counterfactual_travel.json"
REASON_BY_FAMILY = {
    "01": "user_declined",
    "02": "invalid_input",
    "03": "invalid_input",
    "04": "invalid_input",
    "05": "invalid_input",
    "06": "user_declined",
}
REASON_SCHEMA = {
    "type": "string",
    "enum": ["user_declined", "invalid_input", "policy_blocked"],
    "enum_descriptions": {
        "user_declined": "The user explicitly declined an optional authorization or purchase.",
        "invalid_input": "A required identity, eligibility, or document value is explicitly invalid.",
        "policy_blocked": "All required values are valid, but an independent policy rule blocks execution.",
    },
}
VALIDITY_SLOT_BY_FAMILY = {
    "02": "guest_name",
    "03": "passenger_dob",
    "04": "license_country",
    "05": "passport_expiry",
}


def _replace_conditions(items: list[dict], key: str) -> None:
    for item in items:
        if "when" in item:
            item["when"] = [
                condition.replace(f"{key}=True", f"{key}=valid")
                .replace(f"{key}=False", f"{key}=invalid")
                for condition in item["when"]
            ]
        if "requires" in item:
            item["requires"] = [
                condition.replace(f"{key}=True", f"{key}=valid")
                .replace(f"{key}=False", f"{key}=invalid")
                for condition in item["requires"]
            ]


def main() -> None:
    tasks = json.loads(PATH.read_text())
    for task in tasks:
        task_id = task["episode"]["task_id"]
        family = task_id.split("_")[2]
        expected_reason = REASON_BY_FAMILY[family]
        validity_key = VALIDITY_SLOT_BY_FAMILY.get(family)
        if validity_key:
            for claim in task["episode"]["gold_state"]:
                if claim["key"] == validity_key and claim.get("value") is not None:
                    if claim["value"] is True:
                        claim["value"] = "valid"
                        claim["value_type"] = "string"
                    elif claim["value"] is False:
                        claim["value"] = "invalid"
                        claim["value_type"] = "string"
            for event in task["upstream_trace"]:
                content = event.get("content", {})
                if content.get(validity_key) is True:
                    content[validity_key] = "valid"
                elif content.get(validity_key) is False:
                    content[validity_key] = "invalid"
            for reply in task["mock_tool_world"]["user_replies"].values():
                update = reply.get("updates", {}).get(validity_key)
                if update and update.get("value") is True:
                    update["value"] = "valid"
            _replace_conditions(task["episode"]["allowed_next_actions"], validity_key)
            _replace_conditions(task["episode"]["forbidden_next_actions"], validity_key)
            _replace_conditions(task["mock_tool_world"]["public_actions"], validity_key)
        for public_action in task["mock_tool_world"]["public_actions"]:
            if public_action["action"] == "decline_or_offer_alternative":
                public_action["arguments"]["reason_code"] = REASON_SCHEMA
        if not task_id.endswith("_denied"):
            continue
        episode = task["episode"]
        for rule in episode["allowed_next_actions"]:
            if rule["action"] == "decline_or_offer_alternative":
                rule["expected_arguments"]["reason_code"] = expected_reason
        for event in episode["success_predicate"]["args"]["required_events"]:
            if event["name"] == "decline_or_offer_alternative":
                event["arguments"]["reason_code"] = expected_reason
    PATH.write_text(json.dumps(tasks, indent=2, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
