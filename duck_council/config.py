from pathlib import Path
from constants import Constants

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent

# APP_HOST='0.0.0.0'
APP_HOST='127.0.0.1'
APP_PORT=8000
BASE_URL='http://127.0.0.1:'+str(APP_PORT)
DEBUG=True

# Only these agents will be able to answer the prompt
ALLOWED_AGENT_LIST=[
    # Constants.agent_names.LAWYER,
    Constants.agent_names.WITCH,
    Constants.agent_names.DOCTOR,
    Constants.agent_names.RICH ,
    # Constants.agent_names.GAMER,
    # Constants.agent_names.GANGSTA,
    Constants.agent_names.SERIAL_KILLER,
    Constants.agent_names.DIPLOMAT,
    Constants.agent_names.TECHNO,
    # Constants.agent_names.KING ,
    Constants.agent_names.SPIRITUAL_MEDIUM,
    # Constants.agent_names.DETECTIVE,
    Constants.agent_names.REBEL,
    ]