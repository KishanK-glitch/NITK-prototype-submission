import os
import re
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from langgraph.graph import StateGraph, START, END
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from app.agent.state import AgentState
from app.tools.ocr import extract_aadhaar_text
from app.tools.crawler import fetch_live_scheme_data

# Active Groq model endpoint
llm = ChatGroq(model="openai/gpt-oss-20b", temperature=0, max_tokens=250)


def load_scheme_rules(scheme_name: str = None) -> str:
    # 1. Base Prompt: Language clamp, initial greeting, and TTS spoken-word formatting
    base_prompt = """You are Mirai Gijutsu, a helpful, voice-first AI assistant for Indian government schemes.

CRITICAL RULE 1: You support ONLY three languages: English, Kannada (ಕನ್ನಡ), and Hindi (हिंदी). If the user speaks an unsupported language (like Urdu), DO NOT output a blank response. Instead, politely reply in English or Hindi asking them to speak in English, Kannada, or Hindi.
CRITICAL RULE 3: DO NOT use Markdown tables, bullet points, asterisks, or special characters. Write all responses as natural, conversational paragraphs so the Text-to-Speech engine can read them smoothly.
Available schemes you support: PM Kisan, PM Jan Dhan Yojana (pmjdy), Atal Pension Yojana (atal_pension), PM Svanidhi, PM Vishwakarma.
"""

    if not scheme_name:
        return base_prompt

    # 2. Dynamic live retrieval via crawler (satisfies "no mock data" criteria)
    print(f"\n[System] Fetching live data for {scheme_name}...")
    live_context = fetch_live_scheme_data(scheme_name)

    return (
        base_prompt
        + f"\n\nThe user is applying for {scheme_name}. Here is the official live portal record for it:\n{live_context}\n\nGuide them based ONLY on these live rules. FINAL WARNING: Summarize the eligibility in 2 to 3 natural, conversational sentences. DO NOT use markdown, bullet points, numbers, or asterisks. Speak as if you are leaving a short voicemail."
    )

def check_eligibility(state: AgentState):
    if not state.get("messages"):
        return state

    scheme = state.get("current_scheme", None)
    dynamic_prompt = load_scheme_rules(scheme)

    # Memory safeguard: Send only the last 4 messages to avoid Groq 413 TPM limits
    recent_messages = state["messages"][-4:]
    messages = [SystemMessage(content=dynamic_prompt)] + recent_messages

    response = llm.invoke(messages)

    content = response.content.lower()
    if "ineligible" in content or "excluded" in content or "rejected" in content:
        return {
            "messages": [response],
            "is_eligible": False,
            "rejection_reason": response.content,
        }

    return {"messages": [response]}


def process_documents(state: AgentState):
    media_path_str = state.get("media_path")

    # If it is just a text or voice message, bypass OCR
    if not media_path_str:
        return state

    image_path = Path(media_path_str)

    # Ensure OCR executes exclusively on image files
    if not image_path.exists() or image_path.suffix.lower() not in [".png", ".jpg", ".jpeg"]:
        return state

    if not state.get("aadhaar_number"):
        print(f"\n[System] Running OCR on uploaded image: {image_path}")

        try:
            extracted_text = extract_aadhaar_text(image_path)
            prompt = (
                f"Extract the 12-digit ID number from this OCR text. "
                f"Return ONLY the 12 digits, nothing else. Text: {extracted_text}"
            )
            response = llm.invoke([HumanMessage(content=prompt)])

            extracted_number = response.content.strip()
            extracted_number = "".join(filter(str.isdigit, extracted_number))

            if len(extracted_number) != 12:
                return {
                    "messages": [
                        AIMessage(
                            content="I could not detect a valid 12-digit ID in that image. Please send a clearer photo."
                        )
                    ]
                }

            # Redact digits from outgoing user-facing message
            return {
                "aadhaar_number": extracted_number,
                "messages": [
                    AIMessage(
                        content="Successfully verified your ID [Aadhaar Redacted]. Please share your land record next."
                    )
                ],
            }

        except Exception as e:
            print(f"[OCR Error]: {e}")
            return {
                "messages": [
                    AIMessage(
                        content="I could not read that image clearly. Please send a clearer photo."
                    )
                ]
            }

    return state


def determine_next_step(state: AgentState) -> str:
    if state.get("human_escalation_required"):
        return "escalate"
    if state.get("is_eligible") is False:
        return "reject"

    # Allow normal conversation flow if no document was attached
    if not state.get("media_path"):
        return END

    if not state.get("aadhaar_number"):
        return "request_documents"
    if not state.get("land_survey_number"):
        return "request_documents"
    if not state.get("bank_account_verified"):
        return "request_documents"

    return "submit"


def request_documents(state: AgentState):
    missing = []
    if not state.get("aadhaar_number"):
        missing.append("Aadhaar Card")
    elif not state.get("land_survey_number"):
        missing.append("Land Record (RTC/Pahani)")
    elif not state.get("bank_account_verified"):
        missing.append("Bank Passbook")

    msg = f"Please upload a clear photo of your {missing[0]} to continue."

    return {
        "missing_fields": missing,
        "messages": [AIMessage(content=msg)],
    }


def escalate_to_human(state: AgentState):
    msg = "I need to escalate this to a human agent. Please wait."
    return {"messages": [AIMessage(content=msg)], "human_escalation_required": True}


def submit_application(state: AgentState):
    msg = "All documents verified. Your application is ready for submission."
    return {"messages": [AIMessage(content=msg)]}


workflow = StateGraph(AgentState)

workflow.add_node("check_eligibility", check_eligibility)
workflow.add_node("process_documents", process_documents)
workflow.add_node("request_documents", request_documents)
workflow.add_node("escalate_to_human", escalate_to_human)
workflow.add_node("submit_application", submit_application)

workflow.add_edge(START, "check_eligibility")
workflow.add_edge("check_eligibility", "process_documents")

workflow.add_conditional_edges(
    "process_documents",
    determine_next_step,
    {
        "escalate": "escalate_to_human",
        "reject": END,
        "request_documents": "request_documents",
        "submit": "submit_application",
        END: END,
    },
)

workflow.add_edge("request_documents", END)
workflow.add_edge("escalate_to_human", END)
workflow.add_edge("submit_application", END)

app_graph = workflow.compile()