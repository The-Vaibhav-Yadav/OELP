import os
from dotenv import load_dotenv

# Load environment variables from a .env file if it exists
load_dotenv()

class Settings:
    """
    Holds all application settings and configuration.
    It loads sensitive data from environment variables for security.
    """
    # --- JWT Authentication Settings ---
    # This should be a long, randomly generated string.
    # Command to generate: openssl rand -hex 32
    SECRET_KEY: str = os.getenv("SECRET_KEY", "a_very_secret_key_that_should_be_changed")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 # Token expires in 24 hours

    # --- Razorpay Payment Settings ---
    RAZORPAY_KEY_ID: str = os.getenv("RAZORPAY_KEY_ID")
    RAZORPAY_KEY_SECRET: str = os.getenv("RAZORPAY_KEY_SECRET")
    RAZORPAY_WEBHOOK_SECRET: str = os.getenv("RAZORPAY_WEBHOOK_SECRET")
    
    # --- Database Settings ---
    DB_USER: str = os.getenv("DB_USER", "user")
    DB_PASSWORD: str = os.getenv("DB_PASSWORD", "password")
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: str = os.getenv("DB_PORT", "5432")
    DB_NAME: str = os.getenv("DB_NAME", "mock_test_db")
    
    @property
    def DATABASE_URL(self) -> str:
        """Constructs the full database URL from individual components."""
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

# Create a single settings instance to be used throughout the application
settings = Settings()

