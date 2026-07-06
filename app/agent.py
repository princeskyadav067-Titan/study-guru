import os
import re
import json
from typing import Any

from google.adk import Workflow
from google.adk.workflow import START, Edge, node
from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool
from google.adk.events.event import Event
from google.adk.events.event_actions import EventActions
from google.adk.events.request_input import RequestInput
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types
from pydantic import BaseModel

from google.adk.tools import McpToolset
from google.adk.tools.mcp_tool import StdioConnectionParams
from mcp import StdioServerParameters
from app.config import config

# ---------------------------------------------------------------------------
# State Schema
# ---------------------------------------------------------------------------

class StudyState(BaseModel):
    user_query: str = ""
    schedule: str = ""
    feedback: str = ""
    is_approved: bool = False
    audit_log: list[str] = []

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def get_text_from_input(node_input: Any) -> str:
    if isinstance(node_input, str):
        return node_input
    if hasattr(node_input, 'parts') and node_input.parts:
        return "".join(part.text for part in node_input.parts if part.text)
    if isinstance(node_input, dict) and 'parts' in node_input:
        parts = node_input['parts']
        if isinstance(parts, list):
            return "".join(part.get('text', '') for part in parts if isinstance(part, dict) and part.get('text'))
    return str(node_input)

# ---------------------------------------------------------------------------
# Specialized Agents & Tools
# ---------------------------------------------------------------------------

mcp_toolset = McpToolset(
    connection_params=StdioConnectionParams(
        server_params=StdioServerParameters(
            command="uv",
            args=["run", "python", "-m", "app.mcp_server"]
        )
    )
)

schedule_agent = LlmAgent(
    name="schedule_agent",
    model=Gemini(model=config.model),
    instruction=(
        "You are a study schedule assistant. Design structured study blocks, breaks, "
        "and subject timelines based on study goals. Be detailed and organized. "
        "Use search_study_materials to find reference books to allocate study resources."
    ),
    description="Tool to design study schedules and allocate study time.",
    tools=[mcp_toolset]
)

tutor_agent = LlmAgent(
    name="tutor_agent",
    model=Gemini(model=config.model),
    instruction=(
        "You are an academic tutor. Explain difficult concepts simply, create quiz questions, "
        "and assess student understanding. Use get_topic_summary and generate_practice_questions "
        "to help answer user's requests."
    ),
    description="Tool to explain concepts, generate quizzes, and evaluate answers.",
    tools=[mcp_toolset]
)

schedule_tool = AgentTool(agent=schedule_agent)
tutor_tool = AgentTool(agent=tutor_agent)

study_coordinator = LlmAgent(
    name="study_coordinator",
    model=Gemini(model=config.model),
    instruction=(
        "You are the study coordinator. Your goal is to help the user build an excellent study plan. "
        "Use schedule_agent to design schedules, allocate study blocks, and set timelines. "
        "Use tutor_agent to explain concepts or generate quizzes for the plan. "
        "Your final response should contain the proposed study plan."
    ),
    description="Main coordinating agent for building and refining study plans.",
    tools=[schedule_tool, tutor_tool]
)


# ---------------------------------------------------------------------------
# Workflow Nodes
# ---------------------------------------------------------------------------

@node
def security_checkpoint(ctx: Any, node_input: Any) -> Event:
    text = get_text_from_input(node_input)
    
    # 1. PII Scrubbing
    email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    phone_pattern = r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'
    
    scrubbed_text = text
    scrubbed_emails = re.findall(email_pattern, text)
    scrubbed_phones = re.findall(phone_pattern, text)
    
    if scrubbed_emails:
        scrubbed_text = re.sub(email_pattern, "[EMAIL_REDACTED]", scrubbed_text)
    if scrubbed_phones:
        scrubbed_text = re.sub(phone_pattern, "[PHONE_REDACTED]", scrubbed_text)
        
    # 2. Prompt Injection Detection
    injection_keywords = ["ignore previous instructions", "system prompt", "you are now", "override instructions", "bypass security"]
    is_injection = any(kw in text.lower() for kw in injection_keywords)
    
    # 3. Domain-specific rule: content filter (prevent cheating on exams)
    banned_words = ["hack", "cheat on exam", "bypass test"]
    is_banned = any(word in text.lower() for word in banned_words)
    
    # 4. Audit Log
    severity = "INFO"
    audit_data = {
        "event": "security_check",
        "has_pii": bool(scrubbed_emails or scrubbed_phones),
        "is_injection": is_injection,
        "is_banned": is_banned,
        "text_length": len(text)
    }
    
    if is_injection or is_banned:
        severity = "CRITICAL"
        audit_data["action"] = "blocked"
    elif scrubbed_emails or scrubbed_phones:
        severity = "WARNING"
        audit_data["action"] = "scrubbed"
    else:
        audit_data["action"] = "allowed"
    # Print structured JSON audit log
    print(json.dumps({"severity": severity, "audit": audit_data}))
    audit_log = list(ctx.state.get("audit_log", []))
    audit_log.append(f"[{severity}] {audit_data['event']}: {audit_data['action']}")
    ctx.state["audit_log"] = audit_log
    
    ctx.state["user_query"] = scrubbed_text
    
    if is_injection or is_banned:
        return Event(
            output="Security check failed: input rejected due to security policy.",
            actions=EventActions(route="SECURITY_EVENT")
        )
        
    return Event(
        output=scrubbed_text,
        actions=EventActions(route="pass")
    )

@node
def security_failure(ctx: Any, node_input: Any) -> str:
    return "Your request was flagged by security rules and could not be processed."

@node
def human_review(ctx: Any, node_input: Any) -> Any:
    interrupt_id = "human_approval"
    
    current_schedule = ctx.state.get("schedule", "")
    if node_input and not current_schedule:
        current_schedule = get_text_from_input(node_input)
        ctx.state["schedule"] = current_schedule
        
    if interrupt_id in ctx.resume_inputs:
        user_response = str(ctx.resume_inputs[interrupt_id]).strip().lower()
        if "yes" in user_response or "approve" in user_response or "ok" in user_response:
            ctx.state["is_approved"] = True
            return Event(
                output=current_schedule,
                actions=EventActions(route="approve")
            )
        else:
            ctx.state["feedback"] = user_response
            ctx.state["schedule"] = ""  # Clear to trigger re-generation
            return Event(
                output=user_response,
                actions=EventActions(route="reject")
            )
            
    return RequestInput(
        interrupt_id=interrupt_id,
        message=f"I have generated the following study plan:\n\n{current_schedule}\n\nDo you approve this plan? (Reply 'yes' to approve, or describe any feedback/changes to revise it)."
    )

@node
def final_output(ctx: Any, node_input: Any) -> str:
    return f"Here is your finalized study plan:\n\n{ctx.state.get('schedule', '')}"

# ---------------------------------------------------------------------------
# Workflow Graph & App Definition
# ---------------------------------------------------------------------------

workflow = Workflow(
    name="study_workflow",
    state_schema=StudyState,
    edges=[
        Edge(from_node=START, to_node=security_checkpoint),
        Edge(from_node=security_checkpoint, to_node=study_coordinator, route="pass"),
        Edge(from_node=security_checkpoint, to_node=security_failure, route="SECURITY_EVENT"),
        Edge(from_node=study_coordinator, to_node=human_review),
        Edge(from_node=human_review, to_node=study_coordinator, route="reject"),
        Edge(from_node=human_review, to_node=final_output, route="approve"),
    ]
)

app = App(
    root_agent=workflow,
    name="app",
)
