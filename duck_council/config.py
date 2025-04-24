from pathlib import Path
from constants import Constants

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent

APP_HOST='0.0.0.0'
APP_PORT=8000

# Only these agents will be able to answer the prompt
ALLOWED_AGENT_LIST=[
    Constants.agent_names.WINNER,
    Constants.agent_names.PRAGMATIC,
    Constants.agent_names.ETHICAL
    ]