from fastapi import FastAPI, Depends, HTTPException, status
from sqlalchemy.orm import Session
import asyncio

# Import all the necessary modules from your application structure
from . import crud, models, schema, security, payments, database
from .rag_service import RAGService

# Create the database tables if they don't exist
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
rag_service = RAGService()

# --- Include Routers from other files ---
# Temporarily commented out to disable the payment system
# app.include_router(payments.router, prefix="/payments", tags=["Payments"])

# --- Authentication Endpoints ---

@app.post("/register", response_model=schema.User, status_code=status.HTTP_201_CREATED, tags=["Authentication"])
def register_user(user: schema.UserCreate, db: Session = Depends(database.get_db)):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db=db, user=user)

@app.post("/token", response_model=schema.Token, tags=["Authentication"])
def login_for_access_token(form_data: schema.OAuth2PasswordRequestForm = Depends(), db: Session = Depends(database.get_db)):
    user = crud.get_user_by_email(db, email=form_data.username)
    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = security.create_access_token(
        data={"sub": user.email, "user_id": user.id, "role": user.role.value}
    )
    return {"access_token": access_token, "token_type": "bearer"}

# --- Core Application Endpoint ---

# --- MODIFIED: The endpoint now accepts a request body with parameters ---
@app.post("/generate-exam", tags=["Exam Generation"])
async def generate_new_exam(
    request: schema.ExamGenerationRequest,
    current_user: models.User = Depends(security.get_current_user)
):
    """
    Generate a full, new mock exam based on the provided parameters.
    
    This is a protected endpoint. The user must provide a valid JWT access token.
    """
    try:
        print(f"Generating new {request.exam_name} exam for user: {current_user.email}")
        
        # Pass the request parameters to the RAG service
        generated_exam = await rag_service.generate_full_exam(
            exam_name=request.exam_name,
            stream=request.stream,
            year=request.year
        )
        return generated_exam
    except Exception as e:
        print(f"An error occurred during exam generation: {e}")
        raise HTTPException(status_code=500, detail="An internal error occurred while generating the exam.")

# --- Admin-Only Endpoint for Demo ---

@app.get("/admin/dashboard", tags=["Admin"])
def get_admin_dashboard(current_admin: models.User = Depends(security.get_current_admin_user)):
    """
    An example of a protected endpoint that is only accessible to users with the 'admin' role.
    """
    return {"message": f"Welcome to the admin dashboard, {current_admin.email}!"}

