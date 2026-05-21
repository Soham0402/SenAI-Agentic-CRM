import os
import json
from sqlalchemy.orm import Session
from google import genai
from google.genai import types
from dotenv import load_dotenv

import models
import tools

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Strict System Core Prompt enforcing ReAct execution loops
AGENT_SYSTEM_PROMPT = """
You are the primary Executive Autonomous Triage Agent operating inside an enterprise CRM platform.
Your core purpose is to resolve complex client incoming communications using step-by-step reasoning.

You must interact with the system using a formal loop: Thought, Action, Observation.
- Thought: Explicitly evaluate your current progress, goals, and missing data dependencies.
- Action: Call one of your exposed system tools via structural JSON configuration formatting:
  Available Tools:
    1. search_knowledge_base(query) - Access corporate policy references.
    2. get_contact_profile(email) - Read CRM profiles (VIP, values, risk).
    3. create_internal_ticket(title, body, assignee) - Spawn corporate workflow tracking.
    4. flag_for_legal(email_id, issue_type) - Route active regulatory, trademark, or GDPR actions.
    5. escalate_to_human(email_id, reason, priority) - Hand off high-priority issues to humans.

  Format your Tool invocations EXACTLY as a valid JSON string object match inside your action block:
  {"tool": "name_of_tool", "args": {"arg1": "val1"}}

- Observation: Evaluate the physical system outputs returned by the tool execution.

*** DISQUALIFICATION GUARDRAILS ***
1. If an email is classified as Spam, Ransomware, or Cease-and-Desist, you must NEVER generate an automated response to the client. Route it immediately to security or legal and conclude.
2. If an email is an explicit GDPR Data Access Request, you must invoke flag_for_legal() and create an internal compliance ticket. Never use a generic auto-reply template.
3. If an urgency tier is Critical or High, do not attempt automatic resolution. Gather profile indicators, prepare an internal brief, and execute escalate_to_human().
"""

def execute_agent_triage(email_id: int, db: Session, dry_run: bool = False) -> dict:
    email_rec = db.query(models.Email).filter(models.Email.id == email_id).first()
    if not email_rec:
        return {"error": "Target Email Reference not found."}

    # Pull complete thread history context
    thread_emails = db.query(models.Email).filter(
        models.Email.thread_id == email_rec.thread_id
    ).order_by(models.Email.timestamp.asc()).all()
    
    thread_history = "\n".join([f"Msg [{e.message_id}] Sender: {e.sender} Category: {e.category} Urgency: {e.urgency} Body: {e.body}" for e in thread_emails])

    reasoning_trace_log = []
    current_iteration = 0
    max_steps = 5 # Prevent cascading loops
    suggested_content = None
    final_action = "Ignored"

    # Seed initial context variables
    agent_context = f"""
    Target Inbound Email ID: {email_rec.id}
    Sender: {email_rec.sender}
    Subject: {email_rec.subject}
    Body: {email_rec.body}
    Heuristic Pre-layer Classifications: Category={email_rec.category}, Urgency={email_rec.urgency}

    Thread Conversation Timeline:
    {thread_history}
    """

    while current_iteration < max_steps:
        current_iteration += 1
        
        prompt = f"""
        {AGENT_SYSTEM_PROMPT}

        === CURRENT PROGRESS RUN (Step {current_iteration}/{max_steps}) ===
        History Context: {agent_context}
        Reasoning Steps Taken So Far: {json.dumps(reasoning_trace_log)}

        Determine your next logical step. Output a 'Thought' followed by an 'Action' JSON object if you require information or tools. If you have completed tracking or escalated, output 'Final Answer:'.
        """

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.0)
        )

        response_text = response.text
        reasoning_trace_log.append({"step": current_iteration, "raw_agent_output": response_text})

        # Parse Action Hooks out of the raw response text
        if "Final Answer:" in response_text or email_rec.urgency == "Critical":
            final_action = "Escalate" if email_rec.urgency == "Critical" else "Auto-Reply"
            
            # Formulate the response logic fallback if immediate action is needed
            if email_rec.urgency == "Critical":
                tools.escalate_to_human(email_rec.id, "Critical triage bypass requirement.", "Critical", db)
                final_action = "Escalate"
            break

        # Extract tool configuration maps
        try:
            # Look for JSON declaration matching parameters
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            if json_start != -1 and json_end != -1:
                tool_call = json.loads(response_text[json_start:json_end])
                tool_name = tool_call.get("tool")
                tool_args = tool_call.get("args", {})

                # Dry-Run Guard: Evaluate routes without mutating live database contexts
                if dry_run:
                    observation = f"DRY_RUN SUCCESS: Action '{tool_name}' evaluated syntactically without processing."
                else:
                    # Dynamically dispatch to your backend tool engine configurations
                    if tool_name == "search_knowledge_base":
                        observation = tools.search_knowledge_base(tool_args.get("query"), db)
                    elif tool_name == "get_contact_profile":
                        observation = tools.get_contact_profile(tool_args.get("email"), db)
                    elif tool_name == "create_internal_ticket":
                        observation = tools.create_internal_ticket(tool_args.get("title"), tool_args.get("body"), tool_args.get("assignee"), db)
                    elif tool_name == "flag_for_legal":
                        observation = tools.flag_for_legal(email_rec.id, tool_args.get("issue_type"), db)
                        final_action = "Legal-Flag"
                    elif tool_name == "escalate_to_human":
                        observation = tools.escalate_to_human(email_rec.id, tool_args.get("reason"), tool_args.get("priority"), db)
                        final_action = "Escalate"
                    else:
                        observation = f"Error: Tool name '{tool_name}' undefined."
                
                reasoning_trace_log.append({"step": current_iteration, "tool_executed": tool_name, "observation": observation})
            else:
                observation = "No structured action parsing blocks were identified by the compilation runtime framework."
                reasoning_trace_log.append({"step": current_iteration, "observation": observation})
        except Exception as err:
            observation = f"Execution Fault parsing tool inputs: {str(err)}"
            reasoning_trace_log.append({"step": current_iteration, "error_observation": observation})

    # 3. Save execution results to the Actions log database
    if not dry_run:
        new_action = models.Action(
            email_id=email_rec.id,
            agent_reasoning_log=reasoning_trace_log,
            action_type=final_action,
            proposed_content=suggested_content or "Action resolved via System Routing Protocols."
        )
        db.add(new_action)
        db.commit()

    return {
        "email_id": email_id,
        "final_action_taken": final_action,
        "execution_steps_count": current_iteration,
        "reasoning_trace_logs": reasoning_trace_log
    }