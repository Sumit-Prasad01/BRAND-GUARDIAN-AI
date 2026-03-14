import json
import os
import logging
import re
from typing import Dict, Any, List

from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_community.vectorstores import AzureSearch
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import SystemMessage, HumanMessage

from backend.src.graph.state import VideoAuditedState, ComplianceIssue
from backend.src.services.video_indexer import VideoIndexerService

logger = logging.getLogger("brand-guradian")
logging.basicConfig(level = logging.info)

# Node 1 : Indexer
# Function responsible for converting video to text

def index_video_node(state : VideoAuditedState) -> Dict[str, Any]:
    '''
    Download the youtube video from the url.
    Uploads to the Azure Video Indexer.
    Extarcts the insight.
    '''

    video_url = state.get("video_url")
    video_id_input = state.get("video_id", "video_demo")

    logger.info(f"----[Node:Indexer] Processing : {video_url}")

    local_filename = "temp_audit_video.mp4"

    try:
        vi_service = VideoIndexerService()

        #download
        if "youtube.com" in video_url or "youtube.be" in video_url:
            local_path = vi_service.download_youtube_video(video_url, output_path = local_filename)
        else:
            raise Exception("Please provide a valid YouTube URL for this test.")
        
        # upload
        azure_video_id = vi_service.upload_video(local_path, video_name = video_id_input)
        logger.info(f"Upload Success. Azure ID : {azure_video_id}")

        # cleanup
        if os.path.exists(local_path):
            os.remove(local_path)
        
        raw_insights = vi_service.wait_for_processing(azure_video_id)
        clean_data = vi_service.extarct_data(raw_insights)

        logger.info("----[Node : Indexer] Extraction Complete -----")

        return clean_data

    except Exception as e:
        logger.error(f"Video Indexer Failed : {e}")
        return{
            "errors" : [str(e)],
            "final_status" : "FAIL",
            "transcript" : "",
            "ocr_text" : []
        }
    
# Node 2 : Compliance Auditor

def audio_content_node(state : VideoAuditedState) -> Dict[str, Any]:
    '''
    Performs Retrival Augmented Generation to audit the  content - brand video
    '''

    logger.info("----[Node : Auditor] querying knowledge base and LLM ----")

    transcript = state.get("transcript", "")
    if not transcript:
        logger.warning("No transcript available . Skipping the audit....")
        return {
            "final_status" : "FAIL",
            "final_report" : "Audit Skipped beacause the video processing failed (No transcript)."
        }
    
    # initialize Azure client
    llm = AzureChatOpenAI(
        azure_deployment = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT"),
        openai_api_version = os.getenv("AZURE_OPENAI_API_VERSION"),
        temperature = 0
    )

    embeddings = AzureOpenAIEmbeddings(
        azure_deployment = "text-embedding-3-small",
        openai_api_version = os.getenv("AZURE_OPENAI_API_VERSION")
    )

    vector_store = AzureSearch(
        azure_search_endpoint = os.getenv("AZURE_SEARCH_ENDPOINT"),
        azure_search_key = os.getenv("AZURE_SEARCH_API_KEY"),
        index_name = os.getenv("AZURE_SEARCH_INDEX_NAME"),
        embedding_function = embeddings.embed_query
    )

    # RAG Retrival
    ocr_text = state.get("ocr_text", [])
    query_text = f"{transcript} {''.join(ocr_text)}"
    docs = vector_store.similarity_search(query_text, k = 3)
    retrived_rules = "\n\n".join([doc.page_content for doc in docs])

    # System Prompt
    system_prompt = f"""
                        You are a senior barnd compliance auditor.
                        OFFICIAL REGULATORY RULES : 
                        {retrived_rules}
                        INSTRUCTIONS : 
                        1.Analyze the Transcript and OCR text below.
                        2.Identify any violation of the rules.
                        3.Return strict JSON in the follwiing format : 
                        {{
                            "compliance_results" : [
                            {{
                                "category" : "Claim Validation",
                                "severity" : "CRITICAL",
                                "description" : "Explanation of the violation..."

                            }}
                            ],
                            "status" : "FAIL",
                            "final_report" : "Summary of findings..."
                        }}

                        If no violations are found, set "status" to "PASS" and "compliance results" to []"

                    """
    
    # User Message
    user_message = f"""
                        VIDEO_METADATA : {state.get('video_metadata', {})}
                        TRANSCRIPT : {transcript}
                        ON-SCREEN TEXT (OCR) : {ocr_text}
                    """
    
    try:
        response = llm.invoke(
            SystemMessage(content = system_prompt),
            HumanMessage(content = user_message)
        )

        content = response.content
        if "```" in content:
            content = re.search(r"```(?:json)?(.?)```", content, re.DOTALL).group(1)

        audit_data = json.loads(content.strip())
        return {
            "compliance_results" : audit_data.get("compliance_results", []),
            "final_results" : audit_data.get("status", "FAIL"),
            "final_report" : audit_data.get("final_report", "No report generated")
        }
    

    except Exception as e:
        logger.error(f"System Error in Auditor Node : {str(e)}")

        # raw response
        logger.error(f"Raw LLM response : {response.content if 'response' in locals() else None}")
        return {
            "errors" : [str(e)],
            "final_status" : "FAIL"
        }