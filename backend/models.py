from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), default='admin')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationship to hospitals they administer
    hospitals = db.relationship('Hospital', backref='admin', lazy=True)


class Hospital(db.Model):
    __tablename__ = 'hospitals'
    id = db.Column(db.Integer, primary_key=True)
    admin_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    address = db.Column(db.String(300))
    phone = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    surgeons = db.relationship('Surgeon', backref='hospital', lazy=True)
    surgery_requests = db.relationship('SurgeryRequest', backref='hospital', lazy=True)
    inventory = db.relationship('InventoryItem', backref='hospital', lazy=True)


class Surgeon(db.Model):
    __tablename__ = 'surgeons'
    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospitals.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    specialization = db.Column(db.String(100))
    available_days = db.Column(db.JSON)  # Store array of days as JSON
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class SurgeryRequest(db.Model):
    __tablename__ = 'surgery_requests'
    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospitals.id'), nullable=False)
    surgeon_id = db.Column(db.Integer, db.ForeignKey('surgeons.id'))
    patient_name = db.Column(db.String(100), nullable=False)
    surgery_type = db.Column(db.String(100))
    priority = db.Column(db.String(50))  # e.g., High, Medium, Low
    preferred_date = db.Column(db.String(100)) # Simple string to match frontend '2024-05-15'
    status = db.Column(db.String(50), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class InventoryItem(db.Model):
    __tablename__ = 'inventory_items'
    id = db.Column(db.Integer, primary_key=True)
    hospital_id = db.Column(db.Integer, db.ForeignKey('hospitals.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(100))
    stock = db.Column(db.Integer, default=0)
    min_stock = db.Column(db.Integer, default=0)
    unit = db.Column(db.String(50))
    expiry_date = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
