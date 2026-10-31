# MR FASHION – Streamlit clothing shop

## Features
- Public product catalogue with categories, photos, sizes and INR prices
- Shopping cart and checkout
- Home delivery or shop pickup
- WhatsApp order flow
- Razorpay payment-link flow
- Password-protected admin area to add products, upload photos, update prices, hide products and manage orders

## Run on Windows

1. Install Python 3.11 or 3.12 from https://www.python.org/downloads/ and select **Add Python to PATH**.
2. Extract this ZIP and open the `mr_fashion_streamlit` folder.
3. Click the folder address bar in File Explorer, type `cmd`, and press Enter.
4. Run:

```bash
py -3.12 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

5. Create a file named `secrets.toml` inside the `.streamlit` folder by copying `secrets.toml.example`.
6. Edit `.streamlit/secrets.toml`. Set a private admin password and your WhatsApp number with country code, digits only (India example: 91 followed by the 10-digit number).
7. Run:

```bash
streamlit run app.py
```

8. Your browser opens the website. Use **Admin Login** to add products. The storefront is **Home / Shop**.

## Online payments (Razorpay)

1. Create and verify a merchant account with Razorpay.
2. In Razorpay, create API keys for testing first.
3. Add the Key ID and Key Secret to `.streamlit/secrets.toml`.
4. Restart the app and test a small test-mode order.
5. Before accepting real payments, switch to live API keys only after completing Razorpay's account and website checks.

The app creates a Razorpay Payment Link. The admin must verify the payment in the Razorpay dashboard before marking an order as Paid. This starter version does not automatically receive payment webhooks.

## Important deployment and business notes

- Do not upload `.streamlit/secrets.toml` to GitHub. It contains private passwords and API secrets.
- This starter version stores its database and uploaded photos on the app's local disk. Streamlit Community Cloud's local filesystem is not permanent across app restarts/redeployments. Do not use this local-storage version as the permanent live shop database. For a real public store, connect persistent database and image storage (for example, Supabase) before relying on it for customer orders.
- Add your shop address, return/refund policy, shipping charges, delivery estimates, privacy policy and contact details before launch.
- Online payments require your own approved payment-gateway account. Do not collect or store card/UPI PIN details in this app.
