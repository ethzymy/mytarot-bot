"""
MyTarot — Admin API Routes
============================
Blueprint for administrative functions, specifically managing
affiliate settlements, referral trees, and physical card PIN generation.
"""

from flask import Blueprint, request, jsonify
from functools import wraps

from config import ADMIN_SECRET
from referral_manager import (
    get_pending_settlements,
    settle_commission,
    get_referral_tree,
    get_affiliate_balance
)
from pin_manager import generate_pins, get_batch_stats

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def require_admin(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # We check either generic header X-Admin-Secret or an Authorization Bearer token
        secret = request.headers.get("X-Admin-Secret")
        if not secret:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                secret = auth_header.split(" ")[1]
                
        if secret != ADMIN_SECRET:
            return jsonify({"error": "Unauthorized", "message": "Invalid or missing admin secret"}), 403
        return f(*args, **kwargs)
    return decorated_function


# ================= Affiliate Management =================

@admin_bp.route('/affiliates/pending', methods=['GET'])
@require_admin
def pending_settlements():
    """List affiliates with pending commission >= min_amount."""
    min_amount = float(request.args.get('min_amount', 25.0))
    pending_list = get_pending_settlements(min_amount)
    
    return jsonify({
        "status": "success",
        "pending_settlements": pending_list
    })


@admin_bp.route('/affiliates/<phone>/tree', methods=['GET'])
@require_admin
def referral_tree(phone):
    """View the referral downline tree for an affiliate."""
    tree = get_referral_tree(phone)
    balance = get_affiliate_balance(phone)
    
    return jsonify({
        "status": "success",
        "affiliate_phone": phone,
        "balance_summary": balance,
        "referral_tree": tree
    })


@admin_bp.route('/affiliates/settle', methods=['POST'])
@require_admin
def settle_affiliate_commission():
    """Mark all pending commissions for a given referrer as settled."""
    data = request.get_json()
    if not data or 'phone' not in data:
        return jsonify({"error": "Bad Request", "message": "Missing 'phone' in JSON body"}), 400
        
    phone = data['phone']
    settle_up_to = data.get('settle_up_to') # Optional ISO date string
    
    result = settle_commission(phone, settle_up_to)
    
    return jsonify({
        "status": "success",
        "message": f"Settled {result['settled_count']} commissions.",
        "settled_at": result["settled_at"]
    })


# ================= PIN Management =================

@admin_bp.route('/pins/stats', methods=['GET'])
@require_admin
def pin_stats():
    """Get statistics for PIN activations."""
    batch_id = request.args.get('batch_id')
    stats = get_batch_stats(batch_id)
    return jsonify({
        "status": "success",
        "stats": stats
    })


@admin_bp.route('/pins/generate', methods=['POST'])
@require_admin
def generate_new_pins():
    """Generate a new batch of physical card activation PINs."""
    data = request.get_json() or {}
    quantity = int(data.get('quantity', 100))
    batch_id = data.get('batch_id') # Optional
    
    pins = generate_pins(quantity, batch_id)
    
    return jsonify({
        "status": "success",
        "message": f"Generated {len(pins)} new PINs.",
        "sample_pins": pins[:5], 
        "total_generated": len(pins)
    })
