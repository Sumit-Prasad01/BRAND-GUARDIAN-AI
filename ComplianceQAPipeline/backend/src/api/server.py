import uuid
import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

from dotenv import load_dotenv
load_dotenv(override = True)

# initialize the telemetry
from backend.src.api.telemetry import setup_telemetry
setup_telemetry()

from backend.src.graph.workflow import app as compliance_graph

logging.basicConfig(
    level =logging.INFO
)

logger = logging.getLogger("api-server")

# fastapi app
app = FastAPI(
    title = "Brand Guardian AI API",
    description = "API for auditing video content against the brand compliance rules.",
    version = "1.0.0"
    )

# define data models
class AuditRequest(BaseModel):
    '''
    Defines the expected structure of imcoming API requests.
    Examples valid request :
    {"video_url" : "https://youtube.be/abc123"}
    Invalid : 422 error
    {"video_url" : 12345}
    '''

    video_url : str


class ComoplianceIssue(BaseModel):
    category : str
    severity : str
    description : str


class AuditResponse(BaseModel):
    session_id : str
    video_id : str
    status : str
    final_report : str
    compliance_results : List[ComoplianceIssue]


# Define the main endpoint
@app.post("/audit", response_model = AuditRequest)
async def audit_video(request : AuditRequest):
    '''
    Main API endpoint that triggers the compliance audit workflow
    '''

    session_id = str(uuid.uuid4())
    video_id_short = f"vid_{session_id[:8]}"

    logger.info(f"Received the Audit Request : {request.video_url} (Session : {session_id})")

    # graph inputs
    initial_inputs = {
        "video_url" : request.video_url,
        "video_id" : video_id_short,
        "compliance_results" : [],
        "errors" : []
    }

    try:
        final_state = compliance_graph.invoke(initial_inputs)
        return AuditResponse(
            session_id = session_id,
            video_id = final_state.get("video_id"),
            status = final_state.get("final_status", "UNKNOWN"),
            final_report = final_state.get("final_report", "No Report Generated."),
            compliance_results = final_state.get("compliance_results", [])
        )
    
    except Exception as e:
        logger.error(f"Audit Failed : {str(e)}")
        raise HTTPException(
            status_code = 500,
            detail = f"Workflow Execution Failed : {str(e)}" 
        )
    
# health check endpoint
@app.get("/health")
def health_check():
    '''
    Endpoint to verify if API is working or not.
    '''
    return {
        "status" : "healthy",
        "service" : "Brand Guardian AI"
    }