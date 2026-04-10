from flask import Flask, jsonify, request
from flask_cors import CORS
from dotenv import load_dotenv
import sys
import os
import jwt
import datetime
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import db, User, Hospital, Surgeon, SurgeryRequest, InventoryItem

# AI services
from services.prophet import predict_patient_flow
from services.scheduling import optimize_schedule
from services.inventory import generate_inventory_insights

# AWS SNS notification service
from services.notifications import notify_high_priority_surgery, notify_low_inventory

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": ["http://localhost:5173", "https://hellfire-pulseops.vercel.app"]}})

# ================================
# AWS RDS (PostgreSQL) Configuration
# ================================
RDS_USER     = os.getenv("RDS_USER", "root")
RDS_PASSWORD = os.getenv("RDS_PASSWORD", "")
RDS_HOST     = os.getenv("RDS_HOST", "localhost")
RDS_PORT     = os.getenv("RDS_PORT", "5432")
RDS_DB_NAME  = os.getenv("RDS_DB_NAME", "hellfire_pulseops")

app.config['SQLALCHEMY_DATABASE_URI'] = (
    f"postgresql+psycopg2://{RDS_USER}:{RDS_PASSWORD}@{RDS_HOST}:{RDS_PORT}/{RDS_DB_NAME}"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv("JWT_SECRET_KEY", "fallback_dev_key")

db.init_app(app)

with app.app_context():
    try:
        db.create_all()
        print("✅ Connected to RDS and verified tables.")
    except Exception as e:
        print(f"⚠️  Could not connect to RDS: {e}")

# ================================
# JWT Auth Decorator
# ================================
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            parts = auth_header.split(" ")
            token = parts[1] if len(parts) > 1 else parts[0]

        if not token:
            return jsonify({'message': 'Token is missing!'}), 401

        try:
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = db.session.get(User, data['user_id'])
            if not current_user:
                raise Exception("User not found")
        except Exception as e:
            return jsonify({'message': 'Token is invalid!', 'error': str(e)}), 401

        return f(current_user, *args, **kwargs)
    return decorated

# ================================
# Authentication Endpoints
# ================================
@app.route("/api/auth/register", methods=["POST"])
def auth_register():
    data = request.get_json()
    email    = data.get('email')
    name     = data.get('name')
    password = data.get('password')

    if not email or not name or not password:
        return jsonify({"message": "email, name, and password are required"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"message": "User already exists"}), 400

    hashed = generate_password_hash(password, method='pbkdf2:sha256')
    new_user = User(name=name, email=email, password_hash=hashed)
    db.session.add(new_user)
    db.session.commit()

    return jsonify({"message": "Registered successfully", "user_id": new_user.id}), 201


@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    data     = request.get_json()
    email    = data.get('email')
    password = data.get('password')

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"message": "Invalid credentials"}), 401

    token = jwt.encode({
        'user_id': user.id,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=7)
    }, app.config['SECRET_KEY'], algorithm="HS256")

    return jsonify({
        "token": token,
        "user": {"id": user.id, "email": user.email, "name": user.name}
    }), 200


@app.route("/api/auth/me", methods=["GET"])
@token_required
def auth_me(current_user):
    return jsonify({
        "id": current_user.id,
        "email": current_user.email,
        "name": current_user.name
    }), 200

# ================================
# Hospital / Setup
# ================================
@app.route("/api/hospitals", methods=["GET"])
@token_required
def get_hospital(current_user):
    hospital = Hospital.query.filter_by(admin_id=current_user.id).first()
    if hospital:
        return jsonify({
            "id": hospital.id, "name": hospital.name,
            "address": hospital.address, "phone": hospital.phone
        }), 200
    return jsonify({"message": "No hospital found"}), 404


@app.route("/api/hospitals", methods=["POST"])
@token_required
def create_hospital(current_user):
    data = request.get_json()
    if Hospital.query.filter_by(admin_id=current_user.id).first():
        return jsonify({"message": "Hospital already mapped to user"}), 400

    hospital = Hospital(
        admin_id=current_user.id,
        name=data.get('name'),
        address=data.get('address'),
        phone=data.get('phone')
    )
    db.session.add(hospital)
    db.session.commit()
    return jsonify({"id": hospital.id, "name": hospital.name}), 201

# ================================
# Surgeons
# ================================
@app.route("/api/hospitals/<int:hospital_id>/surgeons", methods=["GET"])
@token_required
def get_surgeons(current_user, hospital_id):
    surgeons = Surgeon.query.filter_by(hospital_id=hospital_id).all()
    return jsonify([{
        "id": s.id, "name": s.name,
        "specialization": s.specialization, "available_days": s.available_days
    } for s in surgeons]), 200


@app.route("/api/hospitals/<int:hospital_id>/surgeons", methods=["POST"])
@token_required
def add_surgeon(current_user, hospital_id):
    data = request.get_json()
    s = Surgeon(
        hospital_id=hospital_id,
        name=data.get('name'),
        specialization=data.get('specialization'),
        available_days=data.get('availableDays', [])
    )
    db.session.add(s)
    db.session.commit()
    return jsonify({"id": s.id, "message": "Surgeon added"}), 201

# ================================
# Surgery Requests  (+ SNS alert for HIGH priority)
# ================================
@app.route("/api/hospitals/<int:hospital_id>/surgery-requests", methods=["GET"])
@token_required
def get_surgery_requests(current_user, hospital_id):
    reqs = SurgeryRequest.query.filter_by(hospital_id=hospital_id).all()
    return jsonify([{
        "id": r.id,
        "patientName": r.patient_name,
        "surgeonId": r.surgeon_id,
        "surgeryType": r.surgery_type,
        "priority": r.priority,
        "preferredDate": r.preferred_date,
        "status": r.status
    } for r in reqs]), 200


@app.route("/api/hospitals/<int:hospital_id>/surgery-requests", methods=["POST"])
@token_required
def add_surgery_request(current_user, hospital_id):
    data = request.get_json()

    priority = data.get('priority', 'Low')
    patient_name  = data.get('patientName')
    surgery_type  = data.get('surgeryType')
    preferred_date = data.get('preferredDate')

    r = SurgeryRequest(
        hospital_id=hospital_id,
        surgeon_id=data.get('surgeonId'),
        patient_name=patient_name,
        surgery_type=surgery_type,
        priority=priority,
        preferred_date=preferred_date,
        status=data.get('status', 'pending')
    )
    db.session.add(r)
    db.session.commit()

    # ── AWS SNS: alert on HIGH priority surgeries ──────────────────────────
    if priority and priority.lower() == 'high':
        hospital = db.session.get(Hospital, hospital_id)
        hospital_name = hospital.name if hospital else f"Hospital #{hospital_id}"
        # hospital.phone used as contact; adapt to E.164 if stored that way
        contact = hospital.phone if hospital else None
        try:
            notify_high_priority_surgery(
                hospital_name=hospital_name,
                patient_name=patient_name,
                surgery_type=surgery_type,
                preferred_date=preferred_date or "TBD",
                contact_phone=contact
            )
        except Exception as sns_err:
            print(f"[SNS] Alert failed (non-critical): {sns_err}")

    return jsonify({"id": r.id, "message": "Surgery request added"}), 201

# ================================
# Pharmacy Inventory  (+ SNS alert when stock < min_stock)
# ================================
@app.route("/api/hospitals/<int:hospital_id>/inventory", methods=["GET"])
@token_required
def get_inventory(current_user, hospital_id):
    items = InventoryItem.query.filter_by(hospital_id=hospital_id).all()
    return jsonify([{
        "id": i.id, "name": i.name, "category": i.category,
        "stock": i.stock, "min_stock": i.min_stock,
        "unit": i.unit, "expiry_date": i.expiry_date
    } for i in items]), 200


@app.route("/api/hospitals/<int:hospital_id>/inventory", methods=["POST"])
@token_required
def add_inventory(current_user, hospital_id):
    data = request.get_json()
    stock     = int(data.get('stock', 0))
    min_stock = int(data.get('min_stock', 0))
    item_name = data.get('name')

    i = InventoryItem(
        hospital_id=hospital_id,
        name=item_name,
        category=data.get('category'),
        stock=stock,
        min_stock=min_stock,
        unit=data.get('unit'),
        expiry_date=data.get('expiry_date')
    )
    db.session.add(i)
    db.session.commit()

    # ── AWS SNS: alert if newly added item is already below min stock ──────
    if stock < min_stock:
        hospital = db.session.get(Hospital, hospital_id)
        hospital_name = hospital.name if hospital else f"Hospital #{hospital_id}"
        contact = hospital.phone if hospital else None
        try:
            notify_low_inventory(
                hospital_name=hospital_name,
                item_name=item_name,
                current_stock=stock,
                min_stock=min_stock,
                contact_phone=contact
            )
        except Exception as sns_err:
            print(f"[SNS] Alert failed (non-critical): {sns_err}")

    return jsonify({"id": i.id, "message": "Inventory added"}), 201


@app.route("/api/hospitals/<int:hospital_id>/inventory/<int:item_id>", methods=["PATCH"])
@token_required
def update_inventory_item(current_user, hospital_id, item_id):
    item = db.session.get(InventoryItem, item_id)
    if not item or item.hospital_id != hospital_id:
        return jsonify({"message": "Item not found"}), 404

    data = request.get_json()
    if 'stock' in data:
        item.stock = int(data['stock'])
    if 'name' in data:
        item.name = data['name']
    if 'min_stock' in data:
        item.min_stock = int(data['min_stock'])
    db.session.commit()

    # ── AWS SNS: alert if updated stock is now below min_stock ────────────
    if item.stock < item.min_stock:
        hospital = db.session.get(Hospital, hospital_id)
        hospital_name = hospital.name if hospital else f"Hospital #{hospital_id}"
        contact = hospital.phone if hospital else None
        try:
            notify_low_inventory(
                hospital_name=hospital_name,
                item_name=item.name,
                current_stock=item.stock,
                min_stock=item.min_stock,
                contact_phone=contact
            )
        except Exception as sns_err:
            print(f"[SNS] Alert failed (non-critical): {sns_err}")

    return jsonify({"message": "Updated"}), 200


@app.route("/api/hospitals/<int:hospital_id>/inventory/<int:item_id>", methods=["DELETE"])
@token_required
def delete_inventory_item(current_user, hospital_id, item_id):
    item = db.session.get(InventoryItem, item_id)
    if not item or item.hospital_id != hospital_id:
        return jsonify({"message": "Item not found"}), 404
    db.session.delete(item)
    db.session.commit()
    return jsonify({"message": "Deleted"}), 200

# ================================
# AI APIs
# ================================
@app.route("/api/predict-patient-flow", methods=["POST"])
def predict_patient_flow_controller():
    return predict_patient_flow(request)


@app.route("/api/optimize-schedule", methods=["POST"])
def optimize_schedule_controller():
    return optimize_schedule(request)


@app.route("/api/inventory-insights", methods=["POST"])
def inventory_insights_controller():
    return generate_inventory_insights(request)


if __name__ == "__main__":
    app.run(debug=True)
