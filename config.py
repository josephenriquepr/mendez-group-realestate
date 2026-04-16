from dotenv import load_dotenv
import os

load_dotenv()

OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL: str = "gpt-4o-mini"
UPLOAD_DIR: str = "uploads"

UPLOADPOST_API_KEY: str = os.getenv("UPLOADPOST_API_KEY", "")
UPLOADPOST_USER: str = os.getenv("UPLOADPOST_USER", "")

# Email / SMTP (Gmail App Password recomendado)
SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER: str = os.getenv("SMTP_USER", "")
SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_NAME: str = os.getenv("SMTP_FROM_NAME", "ListaPro CRM")

# Meta / Instagram / Facebook Webhooks
META_VERIFY_TOKEN: str = os.getenv("META_VERIFY_TOKEN", "listapro_verify_2024")
META_PAGE_ACCESS_TOKEN: str = os.getenv("META_PAGE_ACCESS_TOKEN", "")
META_INSTAGRAM_ACCOUNT_ID: str = os.getenv("META_INSTAGRAM_ACCOUNT_ID", "")
