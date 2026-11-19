import os
from dotenv import load_dotenv

load_dotenv()


def _f(name: str, default: float) -> float:
    return float(os.getenv(name, default))


SUPABASE_URL = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", "")
DEVICE_API_KEY = os.getenv("DEVICE_API_KEY", "")
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",") if o.strip()]

WARNING_LEVEL_CM = _f("WARNING_LEVEL_CM", 40)
CRITICAL_LEVEL_CM = _f("CRITICAL_LEVEL_CM", 20)
STABLE_SLOPE_CM_PER_DAY = _f("STABLE_SLOPE_CM_PER_DAY", 0.5)
RATE_WARNING_CM_PER_DAY = _f("RATE_WARNING_CM_PER_DAY", 2)
RATE_CRITICAL_CM_PER_DAY = _f("RATE_CRITICAL_CM_PER_DAY", 5)
OFFLINE_MINUTES = _f("OFFLINE_MINUTES", 10)
