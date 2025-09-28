# from fastapi import FastAPI, Depends, HTTPException, status
# from sqlalchemy.orm import Session
# import asyncio

# # Import all the necessary modules from your application structure
# from . import crud, models, schema, security, payments, database
# from .rag_service import RAGService

# # Create the database tables if they don't exist
# # This is a good practice for the first run
# try:
#     models.Base.metadata.create_all(bind=database.engine)
#     print("Database tables checked/created successfully.")
# except Exception as e:
#     print(f"Error creating database tables: {e}")

# # --- FastAPI App Initialization ---
# app = FastAPI(
#     title="CAT/GATE Mock Test Platform API",
#     description="An AI-powered platform to generate mock exams with a secure payment and user system.",
#     version="1.0.0"
# )

# # --- Initialize the RAG Service ---
# # This creates a single instance of the RAGService that will be shared across all requests.
# # This is efficient as the models are loaded into memory only once.
# rag_service = RAGService()

# # --- Include Routers from other files ---
# # This keeps the main file clean by organizing endpoints into logical groups.
# app.include_router(payments.router, prefix="/payments", tags=["Payments"])

# # --- Authentication Endpoints ---

# @app.post("/register", response_model=schema.User, status_code=status.HTTP_201_CREATED, tags=["Authentication"])
# def register_user(user: schema.UserCreate, db: Session = Depends(database.get_db)):
#     """
#     Register a new user.
#     Checks if a user with the same email already exists.
#     """
#     db_user = crud.get_user_by_email(db, email=user.email)
#     if db_user:
#         raise HTTPException(status_code=400, detail="Email already registered")
#     return crud.create_user(db=db, user=user)

# @app.post("/token", response_model=schema.Token, tags=["Authentication"])
# def login_for_access_token(form_data: schema.OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
#     """
#     Login a user and return a JWT access token.
#     Uses OAuth2 password flow for compatibility with FastAPI's docs.
#     """
#     user = crud.get_user_by_email(db, email=form_data.username)
#     if not user or not security.verify_password(form_data.password, user.hashed_password):
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Incorrect email or password",
#             headers={"WWW-Authenticate": "Bearer"},
#         )
    
#     access_token = security.create_access_token(
#         data={"sub": user.email, "user_id": user.id}
#     )
#     return {"access_token": access_token, "token_type": "bearer"}

# # --- Core Application Endpoint ---

# @app.post("/generate-exam", tags=["Exam Generation"])
# async def generate_new_exam(current_user: models.User = Depends(security.get_current_active_subscriber)):
#     """
#     Generate a full, new CAT mock exam.
    
#     This is a protected endpoint. The user must provide a valid JWT access token
#     and have an active subscription to use it.
#     """
#     try:
#         print(f"Generating new exam for user: {current_user.email}")
#         # Call the asynchronous exam generation function from the RAG service
#         generated_exam = await rag_service.generate_full_exam()
#         return generated_exam
#     except Exception as e:
#         print(f"An error occurred during exam generation: {e}")
#         raise HTTPException(status_code=500, detail="An internal error occurred while generating the exam.")






from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
import asyncio

# Import all the necessary modules from your application structure
from fastapi_app import crud, models, schema, security, payments, database
from .rag_service import RAGService

# Create the database tables if they don't exist
# This is a good practice for the first run
try:
    models.Base.metadata.create_all(bind=database.engine)
    print("Database tables checked/created successfully.")
except Exception as e:
    print(f"Error creating database tables: {e}")

# --- FastAPI App Initialization ---
app = FastAPI(
    title="CAT/GATE Mock Test Platform API",
    description="An AI-powered platform to generate mock exams with a secure payment and user system.",
    version="1.0.0"
)

# --- Initialize the RAG Service ---
# This creates a single instance of the RAGService that will be shared across all requests.
# This is efficient as the models are loaded into memory only once.
rag_service = RAGService()

# --- Include Routers from other files ---
# This keeps the main file clean by organizing endpoints into logical groups.
# Temporarily commented out to disable the payment system
# app.include_router(payments.router, prefix="/payments", tags=["Payments"])

# --- Authentication Endpoints ---

@app.post("/register", response_model=schema.User, status_code=status.HTTP_201_CREATED, tags=["Authentication"])
def register_user(user: schema.UserCreate, db: Session = Depends(database.get_db)):
    """
    Register a new user.
    Checks if a user with the same email already exists.
    """
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db=db, user=user)

@app.post("/token", response_model=schema.Token, tags=["Authentication"])
def login_for_access_token(form_data: schema.OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    """
    Login a user and return a JWT access token.
    Uses OAuth2 password flow for compatibility with FastAPI's docs.
    """
    user = crud.get_user_by_email(db, email=form_data.username)
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = security.create_access_token(
        data={"sub": user.email, "user_id": user.id}
    )
    return {"access_token": access_token, "token_type": "bearer"}

# --- Core Application Endpoint ---

@app.post("/generate-exam", tags=["Exam Generation"])
async def generate_new_exam(current_user: models.User = Depends(security.get_current_user)):
    """
    Generate a full, new CAT mock exam.
    
    This is a protected endpoint. The user must provide a valid JWT access token
    to use it. (Subscription check is temporarily disabled).
    """
    try:
        print(f"Generating new exam for user: {current_user.email}")
        # Call the asynchronous exam generation function from the RAG service
        generated_exam = await rag_service.generate_full_exam()
        return generated_exam
    except Exception as e:
        print(f"An error occurred during exam generation: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred while generating the exam.")

