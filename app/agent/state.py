from typing import TypedDict, Optional, List
from typing_extensions import Annotated
import operator
from langchain_core.messages import BaseMessage

class AgentState(TypedDict):
    phone_number: str
    messages: Annotated[list[BaseMessage], operator.add]
    is_eligible: Optional[bool]
    rejection_reason: Optional[str]
    aadhaar_number: Optional[str]
    land_survey_number: Optional[str]
    bank_account_verified: Optional[bool]
    missing_fields: List[str]
    human_escalation_required: bool