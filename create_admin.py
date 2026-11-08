from database.db import get_db_connection, create_tables
from werkzeug.security import generate_password_hash

create_tables()

username = input("Enter Admin Username: ")
email = input("Enter Admin Email: ")
password = input("Enter Admin Password: ")

hashed_password = generate_password_hash(password)

connection = get_db_connection()

try:
    connection.execute(
        """INSERT INTO users (username, email, password, role)
           VALUES (?, ?, ?, ?)""",
        (username, email, hashed_password, "admin")
    )

    connection.commit()
    print("Admin account created successfully!")

except Exception as error:
    print("Error:", error)

finally:
    connection.close()