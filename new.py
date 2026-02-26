import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import qrcode
import uuid
import datetime
from PIL import Image
import os
import io

# -------------------------
# PAGE CONFIG
# -------------------------
st.set_page_config(
    page_title="AI Laser QR - Firestore Version",
    page_icon="🚆",
    layout="wide"
)

# -------------------------
# PROFESSIONAL BLUE UI
# -------------------------
st.markdown("""
<style>
body {background-color: #f4f8ff;}
.stButton>button {
    background-color: #0A3D62;
    color: white;
    border-radius: 8px;
    width: 100%;
}
h1,h2,h3 {color: #0A3D62;}
</style>
""", unsafe_allow_html=True)

# -------------------------
# FIREBASE INITIALIZATION
# -------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
cred_path = os.path.join(BASE_DIR, "firebase-key.json")

if not os.path.exists(cred_path):
    st.error(f"❌ Error: 'firebase-key.json' file not found at: {cred_path}")
    st.info("Please download your Firebase Admin Key JSON file and save it as 'firebase-key.json' in the same folder as this script.")
    st.stop()

cred = credentials.Certificate(cred_path)

if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

db = firestore.client()

# -------------------------
# FUNCTIONS
# -------------------------

def generate_qr(unique_id):
    """Generate QR code and return as bytes"""
    qr = qrcode.make(unique_id)
    
    # Convert PIL Image to bytes
    buffer = io.BytesIO()
    qr.save(buffer, format="PNG")
    buffer.seek(0)
    
    return buffer.getvalue()

def store_item(data):
    db.collection("track_fittings").document(data["id"]).set(data)

def fetch_item(qr_id):
    doc = db.collection("track_fittings").document(qr_id).get()
    if doc.exists:
        return doc.to_dict()
    return None

def update_in_service(qr_id, update_data):
    db.collection("track_fittings") \
      .document(qr_id) \
      .collection("in_service_updates") \
      .add(update_data)

# -------------------------
# HEADER
# -------------------------
st.title("🚆 AI-Based Laser QR Tracking System")
st.subheader("Cloud Firestore Backend")

login_type = st.radio("Login As:", ["Manufacturer", "Railway Staff"])

# ======================================================
# MANUFACTURER SECTION
# ======================================================
if login_type == "Manufacturer":

    st.header("🏭 Manufacturer Portal")

    with st.form("manufacturer_form"):

        col1, col2 = st.columns(2)

        with col1:
            vendor_name = st.text_input("Vendor Name")
            lot_number = st.text_input("Lot Number")
            item_type = st.selectbox(
                "Item Type",
                ["Elastic Rail Clip", "Rail Pad", "Liner", "Sleeper"]
            )

        with col2:
            supply_date = st.date_input("Supply Date")
            warranty_months = st.number_input("Warranty (Months)", min_value=1)
            inspection_date = st.date_input("Initial Inspection Date")

        submit = st.form_submit_button("Generate QR & Store")

    if submit:
        unique_id = str(uuid.uuid4())

        data = {
            "id": unique_id,
            "vendor_name": vendor_name,
            "lot_number": lot_number,
            "item_type": item_type,
            "supply_date": str(supply_date),
            "warranty_months": warranty_months,
            "inspection_date": str(inspection_date),
            "created_at": datetime.datetime.utcnow()
        }

        store_item(data)

        # Get QR code as bytes
        qr_bytes = generate_qr(unique_id)

        st.success("✅ Stored in Cloud Firestore Successfully!")
        
        # Display QR code using bytes
        st.image(qr_bytes, caption="Laser QR Code for Marking", width=300)
        
        st.info(f"**Unique System ID:** `{unique_id}`")
        st.caption("Copy this ID to test in Railway Staff section")

# ======================================================
# RAILWAY STAFF SECTION
# ======================================================
if login_type == "Railway Staff":

    st.header("🛠 Railway Staff Portal")

    qr_id = st.text_input("Enter / Scan QR ID (Unique UUID)")

    if st.button("Fetch Item Data"):

        if not qr_id:
            st.warning("Please enter a QR ID.")
        else:
            try:
                item = fetch_item(qr_id)

                if item:
                    st.success("✅ Item Found in Database")
                    
                    st.markdown(f"**Vendor:** {item.get('vendor_name')}")
                    st.markdown(f"**Type:** {item.get('item_type')}")
                    st.markdown(f"**Lot:** {item.get('lot_number')}")
                    st.markdown(f"**Supply Date:** {item.get('supply_date')}")
                    st.markdown(f"**Warranty:** {item.get('warranty_months')} Months")
                    
                    st.divider()
                    
                    st.subheader("Add In-Service Inspection")

                    condition = st.selectbox(
                        "Condition",
                        ["Good", "Minor Wear", "Major Defect", "Replace Required"]
                    )

                    remarks = st.text_area("Inspection Remarks")

                    if st.button("Update Inspection Record"):
                        
                        if not remarks:
                            st.warning("Please add remarks.")
                        else:
                            update_data = {
                                "date": datetime.datetime.utcnow(),
                                "condition": condition,
                                "remarks": remarks
                            }

                            update_in_service(qr_id, update_data)
                            st.success("✅ Inspection Record Saved to Cloud Database!")

                else:
                    st.error("❌ QR ID Not Found in Database.")
            except Exception as e:
                st.error(f"Error connecting to Database: {e}")

# ======================================================
# LIVE INVENTORY METRICS (SIDEBAR)
# ======================================================
st.sidebar.header("📊 Live Inventory Overview")

try:
    docs = db.collection("track_fittings").stream()
    all_docs = list(docs)
    count = len(all_docs)
    
    st.sidebar.metric("Total Registered Items", count)
    st.sidebar.write("Data fetched live from Firestore")
except Exception as e:
    st.sidebar.error("Database connection error")