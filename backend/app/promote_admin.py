"""
Promote an existing user to admin from the command line.

The very first registered account is promoted automatically on
startup (see app/migrations.py), so this script is only needed to add
a *second* admin without going through the admin panel itself (e.g.
bootstrapping a fresh deployment with a known ops email before anyone
has logged in yet).

Usage:
    python -m app.promote_admin someone@example.com
"""
import sys

from app.database import SessionLocal
from app import models


def main():
    if len(sys.argv) != 2:
        print("Usage: python -m app.promote_admin <email>")
        raise SystemExit(1)

    email = sys.argv[1].strip().lower()
    db = SessionLocal()
    try:
        user = db.query(models.User).filter(models.User.email == email).first()
        if not user:
            print(f"No user found with email {email!r}.")
            raise SystemExit(1)
        user.role = "admin"
        db.add(user)
        db.commit()
        print(f"{email} is now an admin.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
