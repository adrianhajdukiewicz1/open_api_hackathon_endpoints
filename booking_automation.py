from playwright.sync_api import sync_playwright
import time

def book_hotel(destination, check_in_date, check_out_date, guests=2):
    with sync_playwright() as p:
        # Launch browser
        browser = p.chromium.launch(headless=False)  # Set headless=True for running without UI
        context = browser.new_context()
        page = context.new_page()

        try:
            # Navigate to Booking.com
            page.goto('https://www.booking.com')
            
            # Accept cookies if the popup appears
            try:
                page.click('button[id="onetrust-accept-btn-handler"]', timeout=5000)
            except:
                print("No cookie popup found or already accepted")

            # Enter destination
            page.fill('input[name="ss"]', destination)
            page.keyboard.press('Enter')
            page.click('button[aria-label="Close"]')


            # Select dates
            page.click(f'[data-date="{check_in_date}"]')
            page.click(f'[data-date="{check_out_date}"]')

            # Set number of guests
            page.click('button[data-testid="occupancy-config"]')
            page.fill('input[name="group_adults"]', str(guests))
            page.click('button[data-testid="occupancy-config"]')  # Close the popup

            # Click search
            page.click('button[type="submit"]')

            # Wait for results to load
            page.wait_for_selector('[data-testid="property-card"]', timeout=10000)

            # Select the first hotel
            first_hotel = page.query_selector('[data-testid="property-card"]')
            if first_hotel:
                first_hotel.click()

            # Wait for hotel page to load
            page.wait_for_selector('button[data-testid="reserve-button"]', timeout=10000)

            # Click reserve button
            page.click('button[data-testid="reserve-button"]')

            # Wait for booking form
            page.wait_for_selector('input[name="firstname"]', timeout=10000)

            # Fill in guest details
            page.fill('input[name="firstname"]', 'John')
            page.fill('input[name="lastname"]', 'Doe')
            page.fill('input[name="email"]', 'john.doe@example.com')
            page.fill('input[name="phone"]', '+1234567890')

            # Note: The actual booking process would require payment details
            # This is just a demonstration and stops before the payment step

            print("Booking process initiated successfully!")
            
        except Exception as e:
            print(f"An error occurred: {str(e)}")
        
        finally:
            # Keep the browser open for inspection
            input("Press Enter to close the browser...")
            browser.close()

if __name__ == "__main__":
    # Example usage
    book_hotel(
        destination="New York",
        check_in_date="2025-05-07",
        check_out_date="2025-05-14",
        guests=2
    ) 