import pdfplumber
import re  # Import regex for cleaning product names
import warnings
import requests
import os
from datetime import datetime, timedelta
warnings.filterwarnings("ignore", category=UserWarning)

# Telegram Bot Token and Chat ID
TELEGRAM_BOT_TOKEN = "xx"
TELEGRAM_CHAT_ID = "xx"

# URL of the PDF
pdf_url = "https://cem-cms-data.s3.ap-south-1.amazonaws.com/today_price_list.pdf"

# Get yesterday's and today's date in YYYY-MM-DD format
yesterday = (datetime.today() - timedelta(days=1)).strftime('%Y-%m-%d')
# Get today's date in YYYY-MM-DD format
today = datetime.today().strftime('%Y-%m-%d')

# Define file paths
downloaded_pdf = f"{today}.pdf"  # Temporary name
data_folder = "data"
final_pdf_path = os.path.join(data_folder, f"{today}.pdf")  # Final destination

# Ensure the data folder exists
os.makedirs(data_folder, exist_ok=True)

# Step 1: Download the PDF
print("Downloading the PDF...")
response = requests.get(pdf_url, stream=True)
if response.status_code == 200:
    with open(downloaded_pdf, "wb") as file:
        for chunk in response.iter_content(chunk_size=8192):
            file.write(chunk)
    print(f"Downloaded PDF: {downloaded_pdf}")
else:
    print(f"Failed to download PDF. Status Code: {response.status_code}")
    exit(1)

# Step 2: Move and Rename the PDF
os.rename(downloaded_pdf, final_pdf_path)
print(f"PDF moved to: {final_pdf_path}")

pdf_path_1 = data_folder+"/"+yesterday+".pdf"  # First PDF file (older)
pdf_path_2 = data_folder+"/"+today+".pdf"  # Second PDF file (newer)
def extract_table_1_data(pdf_path):
    """Extracts table 1 data and stores it as a list of dictionaries."""
    extracted_data = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_number, page in enumerate(pdf.pages, start=1):
            tables = page.extract_tables()

            if tables:  # Ensure tables exist on the page
                table_1 = tables[0]  # Extract only Table 1
                
                header = table_1[1]  # Assuming the second row is the actual header
                
                # Find column indices dynamically
                try:
                    product_idx = header.index("Product")
                    denom_idx = header.index("Denomination\n(gm)")
                    price_idx = header.index("Price in INR\n(Incl. Taxes)")
                except ValueError:
                    continue  # Skip this table if headers don't match

                for row in table_1[2:]:  # Skip the header row
                    if len(row) < max(product_idx, denom_idx, price_idx) + 1:
                        continue  # Skip incomplete rows
                    
                    product = row[product_idx].strip()
                    denomination = row[denom_idx].strip()
                    price = row[price_idx].strip().replace(",", "")  # Remove commas

                    # Remove leading integers from the product name
                    product = re.sub(r'^\d+\s*', '', product)

                    # **New Regex: Remove text inside parentheses and brackets**
                    product = re.sub(r'\s*[\(\[].*?[\)\]]', '', product).strip()

                    # Convert price to float for comparison
                    try:
                        price = float(price)
                        denomination = float(denomination)  # Convert denomination to float
                    except ValueError:
                        continue  # Skip rows with invalid data

                    extracted_data.append({
                        "product": product,
                        "denomination": denomination,
                        "price": price
                    })

    return extracted_data

def compare_gold_prices(data_1, data_2):
    """Compares two sets of gold price data and sends a formatted Telegram notification."""
    price_changes = []
    data_2_dict = {(item["product"], item["denomination"]): item["price"] for item in data_2}

    message = "<b>📢 Gold Price Update 📢</b>\n\n"
    message += f"<b>Date:</b> {today}\n"

    for item in data_1:
        key = (item["product"], item["denomination"])
        old_price = item["price"]
        new_price = data_2_dict.get(key)

        if new_price and old_price != new_price:
            percentage_change = ((new_price - old_price) / old_price) * 100
            
            if percentage_change > 0:
                indicator = "🟢"  # Green circle for price increase
            else:
                indicator = "🔴"  # Red circle for price decrease

            price_changes.append((item["product"], item["denomination"], new_price, percentage_change, indicator))

    if not price_changes:
        message += "<b>✅ No price changes detected.</b>"
    else:
        message += "<b>📌 Gold Price Changes:</b>\n"

        for product, denomination, new_price, percentage_change, indicator in price_changes:
            message += f"{indicator} <b>{product}</b> ({denomination}g): ₹{new_price:,.2f} <b>({percentage_change:+.2f}%)</b>\n"

    send_telegram_notification(message, parse_mode="HTML")





def send_telegram_notification(message, parse_mode="HTML"):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": parse_mode  # Accept and use parse_mode
    }
    requests.post(url, json=payload)



# Extract data from both PDFs
data_1 = extract_table_1_data(pdf_path_1)
data_2 = extract_table_1_data(pdf_path_2)

# Compare the data
compare_gold_prices(data_1, data_2)