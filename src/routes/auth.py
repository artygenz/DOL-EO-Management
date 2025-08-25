from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from src.workflow.dto import UserLogin, UserLoginResponse
from src.db.user_operations import authenticate_user
from src.core.auth import create_access_token, blacklist_token
from src.core.dependencies import get_current_active_user, security
from src.db.session import SessionLocal

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post("/login", status_code=status.HTTP_200_OK)
def login(user_credentials: UserLogin):
    """User login endpoint"""
    db = SessionLocal()
    
    user = authenticate_user(db, user_credentials.email, user_credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    access_token = create_access_token(data={"sub": str(user.id)})
    
    return UserLoginResponse(
        access_token=access_token,
        token_type="bearer",
        user={
            "id": str(user.id),
            "name": user.name,
            "email": user.email,
            "role": user.role,
            "org_role": user.org_role,
            "is_active": user.is_active
        }
    )

@router.get("/me", status_code=status.HTTP_200_OK)
def get_current_user_info(current_user = Depends(get_current_active_user)):
    """Get current authenticated user info"""
    return {
        "success": True,
        "message": "Current user info",
        "data": {
            "id": str(current_user.id),
            "name": current_user.name,
            "email": current_user.email,
            "role": current_user.role,
            "org_role": current_user.org_role,
            "is_active": current_user.is_active
        }
    }

@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(
    current_user = Depends(get_current_active_user),
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Logout endpoint - blacklists the current token"""
    token = credentials.credentials
    
    # Blacklist the token
    success = blacklist_token(token, str(current_user.id))
    
    if success:
        return {
            "success": True,
            "message": "Successfully logged out - token revoked",
            "data": {
                "user_id": str(current_user.id),
                "email": current_user.email,
                "token_revoked": True
            }
        }
    else:
        return {
            "success": True,
            "message": "Successfully logged out",
            "data": {
                "user_id": str(current_user.id),
                "email": current_user.email,
                "token_revoked": False
            }
        }
