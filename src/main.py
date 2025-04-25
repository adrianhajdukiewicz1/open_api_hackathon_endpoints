from loguru import logger

if __name__ == "__main__":
    logger.info("Server initialization")
    # The server is actually started by the run.sh script using uvicorn
    # This file can be used for any server setup that needs to happen before uvicorn starts