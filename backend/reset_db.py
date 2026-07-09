import os
from database import engine, Base
import models

if os.path.exists("revenue_assistant.db"):
    os.remove("revenue_assistant.db")

Base.metadata.create_all(bind=engine)
print("DB reset.")
