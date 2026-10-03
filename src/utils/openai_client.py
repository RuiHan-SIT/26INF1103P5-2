from openai import OpenAI
import os
from pathlib import Path
from dotenv import load_dotenv

# Load variables from the .env file into environment
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Point directly to the .env in the root
dotenv_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=dotenv_path)

api_base_url = os.getenv("NVIDABUILD_URL")
api_key = os.getenv("NVDIA_API_KEY")
client = OpenAI(
  base_url = api_base_url,
  api_key = api_key
)


__all__ = ["client"]