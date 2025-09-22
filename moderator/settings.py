import os

from dotenv import load_dotenv

load_dotenv()

ORCHESTRATOR_ADDRESS = os.getenv("ORCHESTRATOR_ADDRESS")
