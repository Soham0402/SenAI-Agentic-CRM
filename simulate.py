import os
import json
import time
import requests

DATASET_PATH = "email-data-advanced.json"
INGEST_URL = "http://127.0.0.1:8000/api/ingest"
PROCESS_URL = "http://127.0.0.1:8000/api/process"
AGENT_URL = "http://127.0.0.1:8000/api/agent/run"

def execute_streaming_simulation(delay_seconds: float = 1.0):
    """
    Simulates real-time ingestion by iterating through the JSON email log,
    pushing elements sequentially down the API infrastructure lanes.
    """
    if not os.path.exists(DATASET_PATH):
        print(f"Error: Target data transmission file '{DATASET_PATH}' not found in runtime directory.")
        return

    with open(DATASET_PATH, "r", encoding="utf-8") as f:
        try:
            email_records = json.load(f)
        except Exception as err:
            print(f"Failed to parse target payload file: {err}")
            return

    print(f"Loaded {len(email_records)} messages. Initializing live injection protocol sequence...")
    
    for idx, payload in enumerate(email_records):
        print(f"\n[Transmission {idx+1}/{len(email_records)}] Ingesting msg: {payload['message_id']}...")
        
        try:
            # Step A: Fire Ingestion and Heuristics Pre-Filter Lanes
            ingest_resp = requests.post(INGEST_URL, json=payload)
            if ingest_resp.status_code not in [200, 201]:
                print(f"❌ Ingestion rejected with status {ingest_resp.status_code}: {ingest_resp.text}")
                continue
                
            resp_json = ingest_resp.json()
            print(f"➔ Ingestion Layer Result: {resp_json['status']} - {resp_json['reason']}")
            
            # If the email was skipped by heuristics (e.g. verified spam), don't process it further
            if resp_json["status"] == "ignored":
                continue

            # FIX: Grab the actual database ID returned from our patched backend
            actual_db_id = resp_json.get("email_id")
            if not actual_db_id:
                print("⚠️ Error: No database ID returned for processing.")
                continue
            
            # Step B: Fire Layer 2 Structured Classification Tasks
            print(f"➔ Triggering Layer 2 LLM Structure Mapping for ID {actual_db_id}...")
            class_resp = requests.post(f"{PROCESS_URL}/{actual_db_id}")
            
            # Step C: Trigger Autonomous Triage Agent ReAct Execution Loops
            print(f"➔ Spawning Autonomous Triage Agent loop processing lanes...")
            agent_resp = requests.post(f"{AGENT_URL}/{actual_db_id}")
            
            # FIX: Safely parse JSON to prevent decoding crashes if the server throws an error
            if agent_resp.status_code == 200:
                print(f"➔ Agent Status Output: {agent_resp.json().get('final_action_taken')}")
            else:
                print(f"❌ Agent Error Response: {agent_resp.text}")

        except Exception as network_error:
            print(f"💥 Operational disruption on network line paths: {network_error}")

        # Configurable loop spacing parameters
        time.sleep(delay_seconds)

if __name__ == "__main__":
    print("Starting Streaming Pipeline simulation tool...")
    execute_streaming_simulation(delay_seconds=1.5)