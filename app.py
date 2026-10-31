import streamlit as st
import sqlite3
import os
import requests
import json
import uuid
from pathlib import Path
from urllib.parse import quote

APP_DIR = Path(__file__).parent
DB_PATH = APP_DIR / "mr_fashion.db"
IMAGE_DIR = APP_DIR / "product_images"
IMAGE_DIR.mkdir(exist_ok=True)

st.set_page_config(page_title="MR FASHION", page_icon="👕", layout="wide")

def get_setting(name, default=""):
    try:
        return st.secrets.get(name, default)
    except Exception:
        return os.getenv(name, default)

ADMIN_PASSWORD = get_setting("ADMIN_PASSWORD", "change-this-password")
WHATSAPP_NUMBER = get_setting("WHATSAPP_NUMBER", "")
RAZORPAY_KEY_ID = get_setting("RAZORPAY_KEY_ID", "")
RAZORPAY_KEY_SECRET = get_setting("RAZORPAY_KEY_SECRET", "")

def connect_db():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def initialize_database():
    with connect_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT,
                price REAL NOT NULL,
                sizes TEXT NOT NULL,
                image_path TEXT,
                active INTEGER DEFAULT 1
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                customer_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                address TEXT,
                fulfillment TEXT NOT NULL,
                payment_method TEXT NOT NULL,
                payment_status TEXT NOT NULL,
                order_status TEXT NOT NULL,
                items_json TEXT NOT NULL,
                total REAL NOT NULL,
                payment_link TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

def get_products(category="All"):
    with connect_db() as conn:
        if category == "All":
            rows = conn.execute(
                "SELECT id, name, category, description, price, sizes, image_path FROM products WHERE active=1 ORDER BY id DESC"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT id, name, category, description, price, sizes, image_path FROM products WHERE active=1 AND category=? ORDER BY id DESC",
                (category,)
            ).fetchall()
    return rows

def save_order(customer_name, phone, address, fulfillment, payment_method, items, total):
    with connect_db() as conn:
        cur = conn.execute("""
            INSERT INTO orders
            (customer_name, phone, address, fulfillment, payment_method,
             payment_status, order_status, items_json, total)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            customer_name, phone, address, fulfillment, payment_method,
            "Pending" if payment_method == "Online payment" else "Not applicable",
            "New", json.dumps(items), total
        ))
        return cur.lastrowid

def create_razorpay_payment_link(order_id, total, customer_name, phone):
    amount_paise = int(round(total * 100))
    payload = {
        "amount": amount_paise,
        "currency": "INR",
        "accept_partial": False,
        "description": f"MR FASHION order #{order_id}",
        "reference_id": f"MRF-{order_id}",
        "customer": {
            "name": customer_name,
            "contact": phone
        },
        "notify": {
            "sms": False,
            "email": False
        },
        "reminder_enable": False
    }
    response = requests.post(
        "https://api.razorpay.com/v1/payment_links",
        auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET),
        json=payload,
        timeout=25
    )
    response.raise_for_status()
    return response.json()["short_url"]

def update_payment_link(order_id, link):
    with connect_db() as conn:
        conn.execute("UPDATE orders SET payment_link=? WHERE id=?", (link, order_id))

def format_items(items):
    return "\n".join(
        f"- {item['name']} | Size: {item['size']} | Qty: {item['quantity']} | ₹{item['price'] * item['quantity']:.2f}"
        for item in items
    )

initialize_database()

if "cart" not in st.session_state:
    st.session_state.cart = {}
if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

st.markdown("""
<style>
.main {background-color: #fafafa;}
.hero {
    background: linear-gradient(120deg, #171717, #454545);
    padding: 34px 28px;
    border-radius: 16px;
    color: white;
    margin-bottom: 22px;
}
.hero h1 {font-size: 42px; margin-bottom: 5px;}
.hero p {font-size: 17px; color: #eeeeee;}
.product-card {
    border: 1px solid #e5e5e5;
    border-radius: 12px;
    padding: 12px;
    background: white;
}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.title("👕 MR FASHION")
    page = st.radio("Navigation", ["Home / Shop", "My Cart", "Admin Login"])
    st.caption("Fashion for every day")

if page == "Home / Shop":
    st.markdown("""
    <div class="hero">
      <h1>MR FASHION</h1>
      <p>Style that defines you. Discover your next favourite outfit.</p>
    </div>
    """, unsafe_allow_html=True)

    products_all = get_products()
    categories = ["All"] + sorted({p[2] for p in products_all})
    selected_category = st.selectbox("Shop by category", categories)
    products = get_products(selected_category)

    if not products:
        st.info("Our collection is getting ready. Please visit again soon.")
    else:
        cols = st.columns(3)
        for index, product in enumerate(products):
            product_id, name, category, description, price, sizes, image_path = product
            with cols[index % 3]:
                st.markdown('<div class="product-card">', unsafe_allow_html=True)
                if image_path and Path(image_path).exists():
                    st.image(image_path, use_container_width=True)
                else:
                    st.image("https://placehold.co/600x700?text=MR+FASHION", use_container_width=True)
                st.subheader(name)
                st.caption(category)
                st.markdown(f"### ₹{price:,.2f}")
                if description:
                    st.write(description)
                size_options = [s.strip() for s in sizes.split(",") if s.strip()]
                chosen_size = st.selectbox("Choose size", size_options, key=f"size_{product_id}")
                quantity = st.number_input("Quantity", min_value=1, max_value=10, value=1, step=1, key=f"qty_{product_id}")
                if st.button("Add to cart", key=f"add_{product_id}", use_container_width=True):
                    cart_key = f"{product_id}_{chosen_size}"
                    if cart_key in st.session_state.cart:
                        st.session_state.cart[cart_key]["quantity"] += int(quantity)
                    else:
                        st.session_state.cart[cart_key] = {
                            "product_id": product_id,
                            "name": name,
                            "size": chosen_size,
                            "price": float(price),
                            "quantity": int(quantity)
                        }
                    st.success(f"{name} added to your cart.")
                st.markdown("</div>", unsafe_allow_html=True)

elif page == "My Cart":
    st.title("🛒 Your Shopping Cart")
    cart = st.session_state.cart
    if not cart:
        st.info("Your cart is empty. Visit Home / Shop to add products.")
    else:
        items = list(cart.values())
        for key, item in list(cart.items()):
            c1, c2, c3, c4 = st.columns([4, 2, 2, 1])
            c1.write(f"**{item['name']}** — Size: {item['size']}")
            c2.write(f"₹{item['price']:,.2f}")
            new_qty = c3.number_input("Qty", min_value=1, max_value=10, value=item["quantity"], key=f"cartqty_{key}")
            st.session_state.cart[key]["quantity"] = int(new_qty)
            if c4.button("Remove", key=f"remove_{key}"):
                del st.session_state.cart[key]
                st.rerun()

        items = list(st.session_state.cart.values())
        total = sum(item["price"] * item["quantity"] for item in items)
        st.divider()
        st.subheader(f"Total: ₹{total:,.2f}")

        st.subheader("Delivery and customer details")
        with st.form("checkout_form"):
            customer_name = st.text_input("Your full name")
            phone = st.text_input("Mobile number (10 digits)")
            fulfillment = st.radio("How would you like to receive your order?", ["Home delivery", "Shop pickup"])
            address = ""
            if fulfillment == "Home delivery":
                address = st.text_area("Full delivery address")
            payment_method = st.radio(
                "Choose how you want to order",
                ["Online payment", "WhatsApp order"],
                help="Online payment uses a Razorpay payment link. WhatsApp order sends your order details to the shop."
            )
            submit_order = st.form_submit_button("Place order", use_container_width=True)

        if submit_order:
            if not customer_name.strip():
                st.error("Please enter your name.")
            elif len("".join(ch for ch in phone if ch.isdigit())) != 10:
                st.error("Please enter a valid 10-digit mobile number.")
            elif fulfillment == "Home delivery" and not address.strip():
                st.error("Please enter your delivery address.")
            elif payment_method == "Online payment" and not (RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET):
                st.error("Online payment is not configured yet. The shop owner must add Razorpay API keys in Streamlit secrets.")
            else:
                order_id = save_order(
                    customer_name.strip(),
                    phone.strip(),
                    address.strip(),
                    fulfillment,
                    payment_method,
                    items,
                    total
                )
                if payment_method == "Online payment":
                    try:
                        payment_url = create_razorpay_payment_link(order_id, total, customer_name.strip(), phone.strip())
                        update_payment_link(order_id, payment_url)
                        st.session_state.cart = {}
                        st.success(f"Order #{order_id} created. Complete your payment using the link below.")
                        st.link_button("Pay securely with Razorpay", payment_url, use_container_width=True)
                        st.info("Your order will be confirmed after the shop verifies the payment.")
                    except Exception as error:
                        st.error(f"Could not create payment link: {error}")
                        st.warning(f"Your order #{order_id} was saved as pending. Contact the shop owner before trying again.")
                else:
                    order_text = (
                        f"Hello MR FASHION, I want to place order #{order_id}.\n"
                        f"Name: {customer_name}\nPhone: {phone}\n"
                        f"Delivery: {fulfillment}\nAddress: {address or 'Shop pickup'}\n"
                        f"Items:\n{format_items(items)}\nTotal: ₹{total:.2f}"
                    )
                    st.session_state.cart = {}
                    st.success(f"Order #{order_id} details are ready. Send the WhatsApp message to the shop.")
                    if WHATSAPP_NUMBER:
                        wa_url = f"https://wa.me/{WHATSAPP_NUMBER}?text={quote(order_text)}"
                        st.link_button("Send order on WhatsApp", wa_url, use_container_width=True)
                    else:
                        st.warning("The shop owner has not configured the WhatsApp number yet.")
                    st.code(order_text)

elif page == "Admin Login":
    st.title("🔐 MR FASHION Admin")
    if not st.session_state.admin_logged_in:
        with st.form("admin_login"):
            password = st.text_input("Admin password", type="password")
            login = st.form_submit_button("Login")
        if login:
            if password == ADMIN_PASSWORD and ADMIN_PASSWORD != "change-this-password":
                st.session_state.admin_logged_in = True
                st.rerun()
            elif password == ADMIN_PASSWORD:
                st.error("Change the default admin password in secrets.toml before using the admin panel.")
            else:
                st.error("Incorrect password.")
    else:
        st.success("You are logged in as admin.")
        if st.button("Logout"):
            st.session_state.admin_logged_in = False
            st.rerun()

        tab_add, tab_manage, tab_orders = st.tabs(["Add product", "Manage products", "Orders"])

        with tab_add:
            st.subheader("Upload a new clothing product")
            with st.form("add_product_form", clear_on_submit=True):
                product_name = st.text_input("Product name")
                category = st.selectbox("Category", ["Men", "Women", "Kids", "Accessories", "Other"])
                description = st.text_area("Product description")
                price = st.number_input("Price (₹)", min_value=1.0, value=499.0, step=50.0)
                sizes = st.multiselect("Available sizes", ["XS", "S", "M", "L", "XL", "XXL", "Free Size"], default=["M", "L", "XL"])
                image_file = st.file_uploader("Product photo", type=["jpg", "jpeg", "png", "webp"])
                add_product = st.form_submit_button("Save product", use_container_width=True)
            if add_product:
                if not product_name.strip() or not sizes or image_file is None:
                    st.error("Enter a product name, select at least one size, and upload a photo.")
                else:
                    extension = Path(image_file.name).suffix.lower()
                    image_name = f"{uuid.uuid4().hex}{extension}"
                    image_path = IMAGE_DIR / image_name
                    image_path.write_bytes(image_file.getvalue())
                    with connect_db() as conn:
                        conn.execute("""
                            INSERT INTO products (name, category, description, price, sizes, image_path)
                            VALUES (?, ?, ?, ?, ?, ?)
                        """, (
                            product_name.strip(), category, description.strip(),
                            float(price), ",".join(sizes), str(image_path)
                        ))
                    st.success("Product saved successfully.")

        with tab_manage:
            st.subheader("Your products")
            with connect_db() as conn:
                product_rows = conn.execute(
                    "SELECT id, name, category, price, sizes, active FROM products ORDER BY id DESC"
                ).fetchall()
            if not product_rows:
                st.info("No products added yet.")
            for row in product_rows:
                pid, pname, pcat, pprice, psizes, active = row
                with st.expander(f"{pname} — ₹{pprice:,.2f}"):
                    st.write(f"Category: {pcat} | Sizes: {psizes} | Status: {'Visible' if active else 'Hidden'}")
                    new_price = st.number_input("Update price (₹)", min_value=1.0, value=float(pprice), key=f"price_{pid}")
                    c1, c2 = st.columns(2)
                    if c1.button("Update price", key=f"update_{pid}"):
                        with connect_db() as conn:
                            conn.execute("UPDATE products SET price=? WHERE id=?", (float(new_price), pid))
                        st.success("Price updated.")
                        st.rerun()
                    if c2.button("Hide" if active else "Show", key=f"toggle_{pid}"):
                        with connect_db() as conn:
                            conn.execute("UPDATE products SET active=? WHERE id=?", (0 if active else 1, pid))
                        st.rerun()

        with tab_orders:
            st.subheader("Customer orders")
            with connect_db() as conn:
                order_rows = conn.execute("""
                    SELECT id, customer_name, phone, address, fulfillment, payment_method,
                           payment_status, order_status, items_json, total, payment_link, created_at
                    FROM orders ORDER BY id DESC
                """).fetchall()
            if not order_rows:
                st.info("No orders received yet.")
            for order in order_rows:
                (oid, cname, cphone, oaddress, fulfill, method, pay_status,
                 order_status, items_json, amount, payment_link, created_at) = order
                with st.expander(f"Order #{oid} — {cname} — ₹{amount:,.2f} — {created_at}"):
                    st.write(f"Phone: {cphone}")
                    st.write(f"Fulfillment: {fulfill}")
                    st.write(f"Address: {oaddress or 'Shop pickup'}")
                    st.write(f"Payment: {method} | Payment status: {pay_status}")
                    st.write(f"Order status: {order_status}")
                    st.text(format_items(json.loads(items_json)))
                    if payment_link:
                        st.link_button("Open payment link", payment_link)
                    new_order_status = st.selectbox(
                        "Update order status",
                        ["New", "Confirmed", "Packed", "Dispatched", "Ready for pickup", "Delivered", "Cancelled"],
                        index=["New", "Confirmed", "Packed", "Dispatched", "Ready for pickup", "Delivered", "Cancelled"].index(order_status)
                        if order_status in ["New", "Confirmed", "Packed", "Dispatched", "Ready for pickup", "Delivered", "Cancelled"] else 0,
                        key=f"status_{oid}"
                    )
                    c1, c2 = st.columns(2)
                    if c1.button("Save order status", key=f"save_status_{oid}"):
                        with connect_db() as conn:
                            conn.execute("UPDATE orders SET order_status=? WHERE id=?", (new_order_status, oid))
                        st.rerun()
                    if method == "Online payment" and pay_status != "Paid":
                        if c2.button("Mark payment as paid (verify in Razorpay first)", key=f"paid_{oid}"):
                            with connect_db() as conn:
                                conn.execute("UPDATE orders SET payment_status='Paid' WHERE id=?", (oid,))
                            st.rerun()
        st.caption("Important: verify every online payment in your Razorpay dashboard before marking it Paid.")
