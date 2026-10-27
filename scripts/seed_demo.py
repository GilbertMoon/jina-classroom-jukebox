from backend.app.database import SessionLocal
from backend.app.seed import seed_demo_data


def main() -> None:
    with SessionLocal() as session:
        seed_demo_data(session)
    print("Demo data is ready.")


if __name__ == "__main__":
    main()
