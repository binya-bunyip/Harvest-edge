import os
import psycopg2
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class Database(Base):
    __tablename__ = 'harvest_edge'
    id = Column(Integer, primary_key=True)
    host = Column(String)
    port = Column(String)
    name = Column(String)
    user = Column(String)
    password = Column(String)
    database = Column(String)

    def get_engine(self):
        return create_engine(f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}")

    def get_session(self):
        engine = self.get_engine()
        Session = sessionmaker(bind=engine)
        return Session()

# Load DB_HOST, DB_PORT, DB_NAME, DB_USER, and DB_PASSWORD from environment variables
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = os.getenv('DB_PORT', '5432')
DB_NAME = os.getenv('DB_NAME', 'harvest_edge')
DB_USER = os.getenv('DB_USER', 'harvest_edge')
DB_PASSWORD = os.getenv('DB_PASSWORD', 'harvest_edge')

# Create the database
engine = create_engine(f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}")
Session = sessionmaker(bind=engine)
db = Database()
db.create_all()

# Test the connection
def test_connection():
    try:
        db.get_session()
        return True
    except Exception as e:
        return False

# Keep the code concise and clean
