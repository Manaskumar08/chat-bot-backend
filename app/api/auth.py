from fastapi import APIRouter

router = APIRouter()


@router.post("/signup")
def signup():

    return {
        "success": True,
        "message": "signup"
    }

@router.post("/login")
def login():

    return {
        "success": True,
        "token": "jwt_token"
    }