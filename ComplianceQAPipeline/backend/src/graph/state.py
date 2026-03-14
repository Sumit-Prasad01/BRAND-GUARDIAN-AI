import operator
from typing import Annotated, List, Dict , Optional, Any, TypedDict

# Schema for a single compliance result

class ComplianceIssue(TypedDict):
    category : str
    description : str
    severity : str  # Critical | Warning
    timestamp : Optional[str]

# Global Graph State
# Defines the state that get's passed around in the agentic workflow
class VideoAuditedState(TypedDict):
    '''
    Defines the data schema for langgraph execution content.
    Main Container : holds all the information about the audit
                     right from the initial URL to the final report.
    '''
    # input parameters
    video_url : str
    video_id : str

    # ingestion and extraction data
    local_file_path : Optional[str]
    video_metadata : Dict[str, Any]
    transcript : Optional[str]
    ocr_text : List[str]

    # analysis output
    # stores the list of all the violations found by AI
    compliance_result : Annotated[List[ComplianceIssue], operator.add]

    # final deliverables
    final_status : str # PASS | FAIL
    final_report : str # makrdown format

    # system observability
    # errors : system level errors, API Timeout
    errors : Annotated[List[str], operator.add]