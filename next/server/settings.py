import os
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass(frozen=True)
class Settings:
    database_path: str = "codifica.sqlite"
    secret_key: str = ""
    origin: str = "http://127.0.0.1:8000"
    dev_auth: bool = False
    pilot_emails: tuple[str, ...] = ()
    oidc_metadata_url: str = ""
    oidc_client_id: str = ""
    oidc_client_secret: str = ""
    session_seconds: int = 604800
    sendgrid_api_key: str = ""
    email_from: str = ""

    @classmethod
    def from_env(cls):
        return cls(
            database_path=os.getenv("CODIFICA_DATABASE_PATH", "codifica.sqlite"),
            secret_key=os.getenv("CODIFICA_SECRET_KEY", ""),
            origin=os.getenv("CODIFICA_ORIGIN", "http://127.0.0.1:8000").rstrip("/"),
            dev_auth=os.getenv("CODIFICA_DEV_AUTH") == "1",
            pilot_emails=tuple(
                e.strip().lower()
                for e in os.getenv("CODIFICA_PILOT_EMAILS", "").split(",")
                if e.strip()
            ),
            oidc_metadata_url=os.getenv("CODIFICA_OIDC_METADATA_URL", ""),
            oidc_client_id=os.getenv("CODIFICA_OIDC_CLIENT_ID", ""),
            oidc_client_secret=os.getenv("CODIFICA_OIDC_CLIENT_SECRET", ""),
            sendgrid_api_key=os.getenv("SENDGRID_API_KEY", ""),
            email_from=os.getenv("CODIFICA_EMAIL_FROM", ""),
        )

    def validate(self):
        if len(self.secret_key) < 32:
            raise ValueError("CODIFICA_SECRET_KEY must contain at least 32 characters")
        url = urlparse(self.origin)
        if (
            not url.hostname
            or url.path not in ("", "/")
            or url.query
            or url.fragment
            or url.username
        ):
            raise ValueError("CODIFICA_ORIGIN must be an origin without a path")
        if self.dev_auth:
            if (
                url.hostname not in ("127.0.0.1", "localhost", "::1")
                or url.scheme != "http"
            ):
                raise ValueError(
                    "Development authentication requires a loopback HTTP origin"
                )
        elif url.scheme != "https" or not (
            (self.sendgrid_api_key and self.email_from)
            or all((self.oidc_metadata_url, self.oidc_client_id, self.oidc_client_secret))
        ):
            raise ValueError(
                "Production requires HTTPS origin and complete email or OIDC configuration"
            )
        if (
            self.oidc_metadata_url
            and urlparse(self.oidc_metadata_url).scheme != "https"
        ):
            raise ValueError("OIDC metadata must use HTTPS")
