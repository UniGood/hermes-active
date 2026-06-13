"""
认证路由
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from models.database import get_active_db
from models.active import User
from models.schemas import LoginRequest, ChangePasswordRequest, TokenResponse, UserInfo
from services.auth_service import AuthService
from middleware.auth import get_current_user

router = APIRouter(prefix="/api/auth", tags=["认证管理"])


@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: Session = Depends(get_active_db)):
    """用户登录"""
    user = AuthService.authenticate_user(db, request.username, request.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误"
        )

    access_token = AuthService.create_access_token(
        data={"sub": user.username}
    )

    return TokenResponse(access_token=access_token)


@router.post("/change-password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """修改密码"""
    success = AuthService.change_password(
        db, current_user, request.old_password, request.new_password
    )
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="旧密码错误"
        )

    return {"success": True, "message": "密码修改成功"}


@router.get("/me", response_model=UserInfo)
async def get_me(current_user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return UserInfo(
        id=current_user.id,
        username=current_user.username,
        avatar=current_user.avatar,
        created_at=current_user.created_at
    )


@router.get("/avatar")
async def get_avatar(db: Session = Depends(get_active_db)):
    """获取用户头像（公开接口，用于登录页显示）"""
    user = db.query(User).first()
    if user and user.avatar:
        return {"avatar": user.avatar}
    return {"avatar": None}


@router.post("/avatar")
async def upload_avatar(
    request: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """上传头像（base64）"""
    avatar_data = request.get("avatar", "")
    if not avatar_data:
        raise HTTPException(status_code=400, detail="头像数据不能为空")
    # 限制大小：约 500KB 的 base64
    if len(avatar_data) > 700000:
        raise HTTPException(status_code=400, detail="头像图片过大，请压缩后重试")
    current_user.avatar = avatar_data
    db.commit()
    return {"success": True, "message": "头像上传成功"}


@router.delete("/avatar")
async def delete_avatar(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_active_db)
):
    """删除头像"""
    current_user.avatar = None
    db.commit()
    return {"success": True, "message": "头像已删除"}


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(current_user: User = Depends(get_current_user)):
    """刷新 token"""
    access_token = AuthService.create_access_token(
        data={"sub": current_user.username}
    )
    return TokenResponse(access_token=access_token)
