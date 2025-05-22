import os
import logging
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SQLAlchemy setup
db = SQLAlchemy()

# Bcrypt setup
bcrypt = Bcrypt()

# Login manager setup
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.session_protection = 'strong'

# Redis or fallback
storage_uri = os.getenv('REDIS_URL', 'memory://')

if storage_uri == 'memory://':
    logger.warning("REDIS_URL not set. Using in-memory storage for rate limiter. Not recommended for production.")

# Rate limiter with fallback support
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri=storage_uri,
    strategy="fixed-window",
    headers_enabled=True,
    in_memory_fallback="memory://",  # ✅ Use correct fallback URI
    retry_after='http-date'
)
