'''Azure OpenTelemetry Integration'''

import os
import logging

from azure.monitor.opentelemetry import configure_azure_monitor

logger = logging.getLogger("brand-guardian-telemetry")

def setup_telemetry():
    '''
    - Initializes Azure Monitor OpenTelemetry
    - Tracks : HTTP Requests, database quiries, errors, performance metrics
    - Send the data to azure monitor
    - It auto captures every API request
    - No Need to manually log each endpoint
    '''

    # retrive connection string
    connection_string = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    if not connection_string:
        logger.warning("No instrumentaion key found.Telemetry key is DISABLED.")
        return
    
    # coinfigure the azure monitor
    try:
        configure_azure_monitor(
            connection_string = connection_string,
            logger_name = "brand-guardian-tracer"
        )

        logger.info("Azure Monitor Tarcking Enabled and Connected")

    except Exception as e:
        logger.error(f"Failed to initialize Azure Monitor : {e}")