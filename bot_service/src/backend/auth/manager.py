import jwt
import requests
from common.configuration import Configuration
from common.logger import logger
from fastapi import HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader, HTTPBasic
from jwt.algorithms import RSAAlgorithm
from jwt.exceptions import ExpiredSignatureError, InvalidTokenError

# bearer_token_header = HTTPBearer()
bearer_token_header = APIKeyHeader(name="x-key")
basic_security = HTTPBasic()


class AuthManager:
    def __init__(self, config: Configuration) -> None:
        self.config_env: Configuration = config.configuration()
        self.config_ini = config.config_ini()
        # bearer_token_header = HTTPBearer()
        # self.jwks_url = self.config_env.auth_configuration.jwks_url
        # self.auth0_audience = self.config_env.auth_configuration.auth0_audience

    def authenticate(self, request: Request, bearer_token: str = Security(bearer_token_header)):
        """
        Authenticate the user using the provided bearer token.
        """
        logger.info("Starting API key validation")
        token = bearer_token.credentials
        jwks_url = self.jwks_url
        jwks = requests.get(jwks_url, timeout=10).json()
        if not jwks:
            logger.error("JWKS URL timeout")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="JWKS URL timeout")
        headers = jwt.get_unverified_header(token)
        kid = headers["kid"]

        public_key = None
        for key in jwks["keys"]:
            if key["kid"] == kid:
                public_key = RSAAlgorithm.from_jwk(key)
                break

        if not public_key:
            logger.error("Public key not found")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Public key not found")

        try:
            decoded_token = jwt.decode(token, public_key, algorithms=["RS256"], audience=self.auth0_audience)
            logger.info("Token successfully validated")
            request.state.user = decoded_token
            return decoded_token
        except ExpiredSignatureError:
            logger.warning("Token has expired")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired")
        except InvalidTokenError as e:
            logger.error(f"Invalid token: {str(e)}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {str(e)}")

    def validate_api_key(self, bearer_token: str = Security(bearer_token_header)):
        """
        Validate the API key.
        """
        ttoken = self.config_env.common_configuration.api_key
        token = bearer_token

        try:
            if token == ttoken:
                return True
            raise ValueError("Unauthorized")
        except Exception as e:
            logger.error(f"Failed to validate API key: {str(e)}")
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired API key")
