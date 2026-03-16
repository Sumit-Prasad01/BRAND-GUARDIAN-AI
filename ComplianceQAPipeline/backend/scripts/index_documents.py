import os
import glob
import logging
from dotenv import load_dotenv
load_dotenv(override = True)

from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import AzureOpenAIEmbeddings
from langchain_community.vectorstores import AzureSearch

logging.basicConfig(
    level = logging.info,
    format = "%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("indexer")


def index_docs():
    '''
    Reads the PDFs, chunks them, and upload them to Azure AI search.
    '''

    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_folder = os.path.join(current_dir, "../../backend/data")

    # check the environment variables
    logger.info("="*60)
    logger.info("Environment Configuration Check")
    logger.info(f"AZURE_OPENAI_ENDPOINT : {os.getenv('AZURE_OPENAI_ENDPOINT')}")
    logger.info(f"AZURE_OPENAI_API_VERSION : {os.getenv('AZURE_OPENAI_API_VERSION')}")
    logger.info(f"Embedding Deployment : {os.getenv('AZURE_OPENAI_EMBEDDING_DEPLOYMENT', 'text-embedding-3-small')}")
    logger.info(f"AZURE_SEARCH_ENDPOINT : {os.getenv('AZURE_SEARCH_ENDPOINT')}")
    logger.info(f"AZURE_SEARCH_INDEX_NAME : {os.getenv('AZURE_SEARCH_INDEX_NAME')}")
    logger.info("="*60)

    # validate required env variables
    required_variables = [
        "AZURE_OPENAI_ENDPOINT",
        "AZURE_OPENAI_API_KEY",
        "AZURE_SEARCH_ENDPOINT",
        "AZURE_SEARCH_API_KEY",
        "AZURE_SEARCH_INDEX_NAME"
    ]

    missing_variables = [var for var in required_variables if not os.getenv(var)]
    if missing_variables:
        logger.info(f"Missing required environment variables : {missing_variables}")
        logger.error("Please check your .env files and ensure all the variables are set.")
        return 
    
    # initialize the embedding model : turns text into vectors
    try:
        logger.info("Initializing Azure OpenAI Embeddings")

        embeddings = AzureOpenAIEmbeddings(
            azure_deployment = os.getenv('AZURE_OPENAI_EMBEDDING_DEPLOYMENT', 'text-embedding-3-small'),
            azure_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT'),
            api_key = os.getenv("AZURE_OPENAI_API_KEY"),
            openai_api_version = os.getenv('AZURE_OPENAI_API_VERSION', '2024-02-01')
        )

        logger.info("Embeddings model initialized successfully.")
    
    except Exception as e:
        logger.error(f"Failed to initialized embeddings : {e}")
        logger.error("Please verify your Azure OpenAI deployemnt name and endpoint.")
        return 
    

    # initialize the Azure Search
    try:
        logger.info("Initializing Azure OpenAI Embeddings")

        embeddings = AzureOpenAIEmbeddings(
            azure_saerch_endpoint = os.getenv('AZURE_SEARCH_ENDPOINT'),
            azure_search_key = os.getenv('AZURE_SEARCH_API_KEY'),
            index_name = index_name,
           embeddings_function = embeddings.embed_query
        )

        logger.info(f"Vector store initialized for index : {index_name}")
    
    except Exception as e:
        logger.error(f"Failed to initialized Azure Search : {e}")
        logger.error("Please verify your Azure Search endpoint api key and index name.")
        return
    

    # Find PDF files
    pdf_files = glob.glob(os.path.join(data_folder, "*.pdf"))
    if not pdf_files:
        logger.warning(f"No PDFs found in {data_folder}. Please add files.")

    logger.info(f"Fopund {len(pdf_files)} PDFs to process : {[os.path.basename(f) for f in pdf_files]}")

    all_splits = []

    # process each pdf
    for pdf_path in pdf_files:
        try:
            logger.info(f"Loading {os.path.basename(pdf_path)}......")
            loader = PyPDFLoader(pdf_path)
            raw_docs = loader.load()

            # chunking strategy
            text_splitters = RecursiveCharacterTextSplitter(
                chunk_size = 1000,
                chunk_overlap = 200
            )

            splits = text_splitters.split_documents(raw_docs)
            for split in splits:
                split.metadata["source"] = os.path.basename(pdf_path)

            all_splits.extend(splits)
            logger.info(f"Splits into {len(splits)} chunks.")

        except Exception as e:
            logger.error(f"Failed to process {pdf_path} : {e}")


        # Upload to Azure
        if all_splits:
            logger.info(f"Uploading {len(all_splits)} chunks to Azure Search AI Index '{index_name}'")

            try:

                # azure search accepts batches automatically via the method
                vector_store.add_documents(documents = all_splits)
                
                logger.info("="*60)
                logger.info("Indexing Complete! Knowledge Base is ready...")
                logger.info(f"Total Chunks indexed : {len(all_splits)}")
                logger.info("="*60)

            except Exception as e:
                logger.error(f"Failed to upload the documents to Azure Search : {e}")
                logger.error("Please check the Azure Search configuration and try again.")

        else:
            logger.warning("No documents were processed.")

if __name__ == "__main__":
    index_docs()