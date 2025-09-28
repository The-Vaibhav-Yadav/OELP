from fastapi_app.database import engine, Base
from fastapi_app import models

print("Connecting to the database to create tables...")

try:
    # This command inspects all the classes that inherit from Base (your User and Subscription models)
    # and creates the corresponding tables in the database.
    Base.metadata.create_all(bind=engine)
    
    print("\n------------------------------------------------------")
    print("Tables 'users' and 'subscriptions' created successfully.")
    print("You can now start the main application.")
    print("------------------------------------------------------")

except Exception as e:
    print(f"An error occurred while creating tables: {e}")
    print("Please check your database connection details in the .env file and ensure the PostgreSQL server is running.")
