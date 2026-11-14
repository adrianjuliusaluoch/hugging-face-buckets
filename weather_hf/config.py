# Settings and secrets, all read from environment variables
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

ROOT = Path(__file__).resolve().parents[1]
COUNTIES_FILE = ROOT / "data" / "reference" / "counties.csv"

OWM_API_KEY = os.environ["OWM_API_KEY"]
HF_NAMESPACE = os.environ["HF_NAMESPACE"]
HF_BUCKET = os.environ["HF_BUCKET"]
HF_S3_KEY_ID = os.environ["HF_S3_KEY_ID"]
HF_S3_SECRET = os.environ["HF_S3_SECRET"]
PG_CATALOG = os.environ["PG_CATALOG"]

WEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
PAUSE = 1.1       # seconds between calls (free plan allows 60 a minute)
MAX_TRIES = 3