"""OAuth2 auth strategy stub for partners that use OAuth."""

from __future__ import annotations

from aih.connectors.auth import AuthStrategy


class OAuth2Auth(AuthStrategy):
    """Bearer token from OAuth2 client-credentials (offline stub)."""

    def __init__(self, access_token: str, token_type: str = "Bearer") -> None:
        self._token = access_token
        self._type = token_type

    def headers(self) -> dict[str, str]:
        return {"Authorization": f"{self._type} {self._token}"}

    @classmethod
    def from_client_credentials(
        cls,
        token_url: str,
        client_id: str,
        client_secret: str,
        *,
        fake_token: str = "oauth-demo-token",
    ) -> OAuth2Auth:
        """Offline stub — real impl would POST to token_url."""
        _ = (token_url, client_id, client_secret)
        return cls(fake_token)
