from jose import jwt, JWTError
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
from dotenv import load_dotenv
load_dotenv()

SECRET_KEY = os.getenv("AUTH_SECRET_KEY")
ALGORITHM = os.getenv("AUTH_ALGORITHM")
security = HTTPBearer()


def verify_jwt_token(token: str):
    if not token:
        raise HTTPException(status_code=403, detail='Auth token is missing in headers.')

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=ALGORITHM)
        return payload
    except JWTError as e:
        raise HTTPException(status_code=403, detail=f'Auth token is invalid. {e}')


def get_current_user(credentials: HTTPAuthorizationCredentials = Security(security)):
    return verify_jwt_token(credentials.credentials)
