import sys
import os
 
# Ensure backend directory is in python path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_dir)
sys.path.append(backend_dir)
 
from app.db.repositories.user_repo import UserRepository
from app.db.session import SessionLocal
from app.db.models.user import User
 
def create_first_user():
    print("--- Creating First User ---")
   
    email = input("Enter email [admin@example.com]: ") or "admin@example.com"
    password = input("Enter password [admin123]: ") or "admin123"
   
    repo = UserRepository()
    db = SessionLocal()
   
    try:
        user = repo.get_user_by_email(email)
        if user:
            print(f"User {email} already exists.")
            # Check if superuser, if not make it so
            if not user.is_superuser:
                print("Upgrading to superuser...")
                user.is_superuser = True
                db.add(user) # Re-add to session to be safe, though repo used its own session usually.
                # Wait, repo.get_user_by_email closes logic.
                # Let's use our own session for updates to be safe
                u = db.query(User).filter(User.email == email).first()
                u.is_superuser = True
                db.commit()
                print("User upgraded to superuser.")
            return
 
        print(f"Creating user {email}...")
        # Create normal user
        user = repo.create_user(email=email, password=password, full_name="Admin User")
       
        # Upgrade to superuser manually since repo method doesn't support it directly anymore
        # Re-fetch with our session to update
        u = db.query(User).filter(User.id == user.id).first()
        u.is_superuser = True
        db.commit()
       
        print(f"✅ Superuser {email} created successfully.")
       
    except Exception as e:
        print(f"❌ Error creating user: {e}")
    finally:
        db.close()
 
if __name__ == "__main__":
    create_first_user()
 