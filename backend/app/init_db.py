
from .database import Base, engine
from . import models


def main():
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")

    print("Tables:")
    for table_name in Base.metadata.tables:
        print(f"- {table_name}")


if __name__ == "__main__":
    main()
