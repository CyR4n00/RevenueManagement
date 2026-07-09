import datetime
from scraper import scraper_service
from database import SessionLocal
import models

def run_test_scrape():
    print("--- Starting Test Scrape ---")
    db = SessionLocal()

    # Ensure tables exist
    models.Base.metadata.create_all(bind=db.get_bind())

    competitors = db.query(models.DBCompetitor).all()
    if not competitors:
        print("No competitors found in the database. Please add some via the UI first.")
        return

    today = datetime.datetime.now().strftime("%Y-%m-%d")

    for comp in competitors:
        print(f"\nScraping {comp.name} ({comp.url}) for {today}...")
        try:
            price, is_booked = scraper_service.extract_price(comp.url, today, comp.id)
            print(f"Result -> Price: {price}, Fully Booked: {is_booked}")
        except Exception as e:
            print(f"Result -> FAILED: {e}")

    db.close()
    print("\n--- Test Scrape Completed ---")

if __name__ == "__main__":
    run_test_scrape()
