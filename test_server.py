import json
import subprocess

def send_request(proc, method, params=None, id=None):
    req = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params or {}
    }
    if id is not None:
        req["id"] = id
    
    msg = json.dumps(req) + "\n"
    proc.stdin.write(msg)
    proc.stdin.flush()
    
    if id is not None:
        line = proc.stdout.readline()
        return json.loads(line) if line else None
    return None

proc = subprocess.Popen(["uv", "run", "dietary-mcp"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)

# 1. Initialize
init_resp = send_request(proc, "initialize", {
    "protocolVersion": "2024-11-05",
    "capabilities": {},
    "clientInfo": {"name": "test-client", "version": "1.0.0"}
}, id=1)

send_request(proc, "notifications/initialized")

# 2. Parse Raw Survey Dataset
print("Calling dietary_parse_raw_survey_dataset...")
parse_resp = send_request(proc, "tools/call", {
    "name": "dietary_parse_raw_survey_dataset",
    "arguments": {
        "request": {
            "datasetId": "test_survey_01",
            "regionId": "eu",
            "populationGroup": "adult_general",
            "rawRecords": [
                {
                    "subjectId": "sub_1",
                    "bodyWeightKg": 70.0,
                    "daysInSurvey": 2,
                    "commodityCode": "apples",
                    "consumptionKgPerDay": 0.4
                },
                {
                    "subjectId": "sub_2",
                    "bodyWeightKg": 65.0,
                    "daysInSurvey": 2,
                    "commodityCode": "apples",
                    "consumptionKgPerDay": 0.0
                },
                {
                    "subjectId": "sub_3",
                    "bodyWeightKg": 80.0,
                    "daysInSurvey": 2,
                    "commodityCode": "apples",
                    "consumptionKgPerDay": 0.6
                }
            ]
        }
    }
}, id=2)

parsed_dataset = parse_resp["result"]["content"][0]["text"]
print("Parsed Dataset RAW:", parsed_dataset)
parsed_json = json.loads(parsed_dataset)
print("Parsed Dataset:", json.dumps(parsed_json, indent=2))

# 3. Summarize Survey Distribution
print("\nCalling dietary_summarize_survey_distribution...")
sum_resp = send_request(proc, "tools/call", {
    "name": "dietary_summarize_survey_distribution",
    "arguments": {
        "request": {
            "dataset": parsed_json,
            "residue_profile": {
                "chemical_identity": {"preferredName": "Glyphosate"},
                "region_id": "eu_screening_default",
                "records": [
                    {
                        "commodity": {
                            "commodity_code": "apples",
                            "canonical_name": "Apples",
                            "food_group": "fruit",
                            "default_processing_factor": 1.0,
                            "mapping_status": "curated",
                            "source_id": "dietary.taxonomy.apples"
                        },
                        "residue_concentration_mg_per_kg": 0.15,
                        "lower_bound_mg_per_kg": 0.15,
                        "upper_bound_mg_per_kg": 0.15,
                        "source_type": "monitoring",
                        "review_status": "reconciled_screening",
                        "provenance": {
                            "source_references": [],
                            "applicable_notes": []
                        }
                    }
                ],
                "provenance": {
                    "source_references": [],
                    "applicable_notes": []
                },
                "quality_flags": [],
                "limitations": []
            }
        }
    }
}, id=3)

print("Distribution Summary Response:")
if "result" in sum_resp and "content" in sum_resp["result"]:
    print(sum_resp["result"]["content"][0]["text"])
else:
    print(json.dumps(sum_resp, indent=2))

proc.terminate()
