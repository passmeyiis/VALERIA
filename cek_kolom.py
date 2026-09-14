import pandas as pd
from sqlalchemy import create_engine, inspect

db_user = 'postgres'
db_password = 'passwordkamu'  # Sesuaikan password kamu
db_host = 'localhost'
db_port = '5432'
db_name = 'postgres'

engine = create_engine(f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}')
inspector = inspect(engine)

print("Kolom yang ada di tabel 'orders' di database kamu:")
for col in inspector.get_columns('orders'):
    print(f"- {col['name']}")