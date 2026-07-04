from django.shortcuts import render, get_object_or_404, redirect
import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum, Q
import json
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST

from .models import Order, Table, CustomerSession
from .models import BillingRecord

from core.models import (
    CustomerSession, Table, Category, Product,
    Cart, CartItem, Order, OrderItem
)


# ─────────────────────────────────────────────
# START
# ─────────────────────────────────────────────

def start(request):
    return render(request, "StartPage.html")


# ─────────────────────────────────────────────
# TABLE BOOKING
# ─────────────────────────────────────────────

def table_booking(request):
    taken = list(
        CustomerSession.objects.values_list("table__table_number", flat=True)
    )
    return render(request, "table_bk.html", {
        "tables_json": json.dumps(taken)
    })


# ─────────────────────────────────────────────
# USER DATA + SESSION CREATE
# ─────────────────────────────────────────────

def userdata(request):
    taken = list(CustomerSession.objects.values_list("table__table_number", flat=True))

    if request.method == "POST":
        name     = request.POST.get("name")
        table_id = request.POST.get("tbn")

        if not name or not table_id:
            return render(request, "table_bk.html", {
                "error": "Fill all fields",
                "tables_json": json.dumps(taken)
            })

        table = get_object_or_404(Table, table_number=table_id)

        if CustomerSession.objects.filter(table=table).exists():
            return render(request, "table_bk.html", {
                "error": "Table already taken",
                "tables_json": json.dumps(taken)
            })

        session = CustomerSession.objects.create(name=name, table=table)
        request.session["session_id"] = str(session.session_id)

        categories = Category.objects.all()
        return render(request, "categories.html", {"categories": categories})

    return render(request, "table_bk.html", {"tables_json": json.dumps(taken)})


# ─────────────────────────────────────────────
# CATEGORY PRODUCTS
# ─────────────────────────────────────────────

def category_detail(request):
    if request.method == "POST":
        category_id = request.POST.get("category_id")
        category    = get_object_or_404(Category, id=category_id)
        products    = Product.objects.filter(category=category)
        return render(request, "product.html", {
            "category": category,
            "products": products
        })


# ─────────────────────────────────────────────
# SEARCH  (nav bar — searches products across all categories)
# ─────────────────────────────────────────────

def search_view(request):
    """
    GET + AJAX (X-Requested-With header): returns JSON product list matching ?q=
    Plain GET (page load from nav bar): renders the search page shell.
    """
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        query = request.GET.get("q", "").strip()

        products = Product.objects.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        )[:20] if query else Product.objects.none()

        data = [
            {
                "id":          p.id,
                "name":        p.name,
                "price":       str(p.price),
                "image_url":   p.image.url if p.image else "",
                "category_id": p.category_id,
            }
            for p in products
        ]
        return JsonResponse({"products": data})

    return render(request, "search.html", {"active_nav": "search"})


# ─────────────────────────────────────────────
# CART HELPERS
# ─────────────────────────────────────────────

def get_customer_and_cart(request):
    """Return (CustomerSession, Cart) for the current session, or (None, None)."""
    session_id = request.session.get("session_id")
    if not session_id:
        return None, None
    try:
        customer = CustomerSession.objects.select_related("table").get(session_id=session_id)
        cart, _  = Cart.objects.get_or_create(session=customer)
        return customer, cart
    except CustomerSession.DoesNotExist:
        return None, None


# ─────────────────────────────────────────────
# ADD TO CART
# ─────────────────────────────────────────────

def add_to_cart(request):
    if request.method == "POST":
        product_id = request.POST.get("product_id")
        quantity   = int(request.POST.get("quantity", 1))
        product    = get_object_or_404(Product, id=product_id)

        session_id = request.session.get("session_id")
        if not session_id:
            return JsonResponse({"status": "error", "message": "No session found"})

        session = get_object_or_404(CustomerSession, session_id=session_id)
        cart, _ = Cart.objects.get_or_create(session=session)

        item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={"quantity": quantity}
        )
        if not created:
            item.quantity += quantity
            item.save()

        return JsonResponse({"status": "success", "message": "Added to cart"})

    return JsonResponse({"status": "error", "message": "Invalid request"})


# ─────────────────────────────────────────────
# CART VIEW
# ─────────────────────────────────────────────

def cart_view(request):
    customer, cart = get_customer_and_cart(request)
    items = []
    if cart:
        items = CartItem.objects.filter(cart=cart).select_related("product")
    return render(request, "cart.html", {"cart_items": items})


@require_POST
def update_quantity(request, item_id):
    _, cart = get_customer_and_cart(request)
    if not cart:
        return JsonResponse({"error": "No cart"}, status=400)

    try:
        data = json.loads(request.body)
        qty  = int(data.get("quantity", 1))
    except (ValueError, json.JSONDecodeError):
        return JsonResponse({"error": "Invalid data"}, status=400)

    item = get_object_or_404(CartItem, id=item_id, cart=cart)

    if qty <= 0:
        item.delete()
    else:
        item.quantity = qty
        item.save()

    remaining   = CartItem.objects.filter(cart=cart).select_related("product")
    grand_total = sum(i.product.price * i.quantity for i in remaining)
    line_total  = float(item.product.price * qty) if qty > 0 else 0

    return JsonResponse({
        "ok":          True,
        "line_total":  round(line_total, 2),
        "grand_total": round(float(grand_total), 2),
        "removed":     qty <= 0,
    })


@require_POST
def remove_item(request, item_id):
    _, cart = get_customer_and_cart(request)
    if not cart:
        return JsonResponse({"error": "No cart"}, status=400)

    CartItem.objects.filter(id=item_id, cart=cart).delete()

    remaining   = CartItem.objects.filter(cart=cart).select_related("product")
    grand_total = sum(i.product.price * i.quantity for i in remaining)

    return JsonResponse({"ok": True, "grand_total": round(float(grand_total), 2)})


# ─────────────────────────────────────────────
# PLACE ORDER
# ─────────────────────────────────────────────

@require_POST
def place_order(request):
    customer, cart = get_customer_and_cart(request)
    if not cart:
        return JsonResponse({"error": "No cart"}, status=400)

    items = CartItem.objects.filter(cart=cart).select_related("product")
    if not items.exists():
        return JsonResponse({"error": "Cart is empty"}, status=400)

    order = Order.objects.create(
        customer_name=customer.name or "Guest",
        table_number=customer.table.table_number,
    )

    for item in items:
        OrderItem.objects.create(
            order=order,
            product_name=item.product.name,
            quantity=item.quantity,
            price=item.product.price,
        )

    cart.cartitem_set.all().delete()

    return JsonResponse({"ok": True, "order_id": order.id})


# ─────────────────────────────────────────────
# ORDER STATUS (customer-facing)
# ─────────────────────────────────────────────

def order_history(request):
    orders = Order.objects.prefetch_related("items").order_by("-placed_at")
    return render(request, "order_history.html", {"orders": orders})


def order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, "order_status.html", {"order": order})


def order_status_session(request):
    session_id = request.session.get("session_id")
    if not session_id:
        return redirect("/")

    try:
        customer = CustomerSession.objects.select_related("table").get(session_id=session_id)
    except CustomerSession.DoesNotExist:
        return redirect("/")

    order = Order.objects.filter(
        customer_name=customer.name,
        table_number=customer.table.table_number
    ).last()

    # No order placed yet — show the page with an empty state instead of
    # bouncing the user back to the start page.
    return render(request, "orders_status.html", {"order": order, "active_nav": "orders"})


@require_POST
def update_order_status(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    NEXT  = {"pending": "making", "making": "done"}
    next_status = NEXT.get(order.status)
    if next_status:
        order.status = next_status
        order.save()
    return JsonResponse({"ok": True, "status": order.status})


# ─────────────────────────────────────────────
# KITCHEN DASHBOARD  (staff only)
# ─────────────────────────────────────────────

@staff_member_required
def kitchen_dashboard(request):
    """Dashboard page — stats + top items rendered server-side."""
    orders = Order.objects.prefetch_related("items").all()

    counts = {
        "pending": orders.filter(status="pending").count(),
        "making":  orders.filter(status="making").count(),
        "done":    orders.filter(status="done").count(),
    }

    top_items = (
        OrderItem.objects
        .values("product_name")
        .annotate(total_qty=Sum("quantity"))
        .order_by("-total_qty")[:5]
    )

    return render(request, "kitchen_dashboard.html", {
        "counts":    counts,
        "top_items": top_items,
    })


@staff_member_required
def kitchen_orders(request):
    """AJAX — returns orders as JSON. ?status=all|pending|making|done"""
    status = request.GET.get("status", "all")

    qs = Order.objects.prefetch_related("items").order_by("placed_at")
    if status in ("pending", "making", "done"):
        qs = qs.filter(status=status)

    data = [
        {
            "id":           order.id,
            "table_number": order.table_number,
            "status":       order.status,
            "placed_at":    order.placed_at.isoformat(),
            "total":        float(order.get_total()),
            "items": [
                {
                    "product_name": item.product_name,
                    "quantity":     item.quantity,
                    "price":        float(item.price),
                }
                for item in order.items.all()
            ],
        }
        for order in qs
    ]

    return JsonResponse({"orders": data})


@staff_member_required
@require_POST
def kitchen_update_status(request, order_id):
    """AJAX — POST {"status": "pending"|"making"|"done"}"""
    order = get_object_or_404(Order, id=order_id)

    try:
        body       = json.loads(request.body)
        new_status = body.get("status")
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    allowed = [c[0] for c in Order.STATUS_CHOICES]
    if new_status not in allowed:
        return JsonResponse({"error": f"Invalid status. Choose from {allowed}"}, status=400)

    order.status = new_status
    order.save(update_fields=["status", "updated_at"])

    return JsonResponse({"success": True, "order_id": order.id, "status": order.status})


# ─── Helper ──────────────────────────────────────────────────────────────────

def _build_whatsapp_message(record: BillingRecord) -> str:
    lines = [
        f"🧾 *KishCraft Coffee — Bill*",
        f"Table {record.table_number}  |  {record.customer_name}",
        "─────────────────────",
    ]
    for item in record.items_snapshot:
        lines.append(f"{item['qty']}x {item['name']}  ₹{item['subtotal']}")
    lines += [
        "─────────────────────",
        f"*Total: ₹{record.total_amount}*",
        "",
        "Thank you for visiting KishCraft Coffee! ☕",
    ]
    return "\n".join(lines)


# ─── Billing list (all done orders not yet billed) ───────────────────────────

@login_required
def billing_dashboard(request):
    """Show all 'done' orders that haven't been billed yet, plus billing history."""
    pending_bills = Order.objects.filter(
        status='done'
    ).exclude(
        billing__isnull=False          # exclude already billed
    ).prefetch_related('items').order_by('-placed_at')

    history = BillingRecord.objects.all()[:30]

    return render(request, 'billing.html', {
        'pending_bills': pending_bills,
        'history': history,
    })


# ─── Single order bill detail ─────────────────────────────────────────────────

@login_required
def billing_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, status='done')
    already_billed = hasattr(order, 'billing') and order.billing is not None

    return render(request, 'billing_detail.html', {
        'order': order,
        'already_billed': already_billed,
    })


# ─── Finalise bill (AJAX POST) ────────────────────────────────────────────────

@login_required
@require_POST
def finalise_bill(request, order_id):
    order = get_object_or_404(Order, id=order_id, status='done')

    # Prevent double-billing
    if BillingRecord.objects.filter(order=order).exists():
        return JsonResponse({'error': 'Already billed'}, status=400)

    phone = request.POST.get('phone', '').strip()

    # Build items snapshot
    items_snapshot = [
        {
            'name':     item.product_name,
            'qty':      item.quantity,
            'price':    str(item.price),
            'subtotal': str(item.subtotal()),
        }
        for item in order.items.all()
    ]

    total = order.get_total()

    # Save billing record
    record = BillingRecord.objects.create(
        order=order,
        customer_name=order.customer_name,
        table_number=order.table_number,
        phone_number=phone,
        items_snapshot=items_snapshot,
        total_amount=total,
    )

    # Free up the table
    Table.objects.filter(table_number=order.table_number).update(is_available=True)

    # Delete CustomerSession rows for this table
    try:
        table_obj = Table.objects.get(table_number=order.table_number)
        CustomerSession.objects.filter(table=table_obj).delete()
    except Table.DoesNotExist:
        pass

    # Build WhatsApp URL
    msg = _build_whatsapp_message(record)
    import urllib.parse
    wa_url = ''
    if phone:
        clean_phone = phone.replace(' ', '').replace('-', '').replace('+', '')
        wa_url = f"https://wa.me/{clean_phone}?text={urllib.parse.quote(msg)}"

    return JsonResponse({
        'success': True,
        'bill_id': record.id,
        'wa_url':  wa_url,
        'message': msg,
    })


# ─── Billing history detail ───────────────────────────────────────────────────

@login_required
def billing_history_detail(request, bill_id):
    record = get_object_or_404(BillingRecord, id=bill_id)
    return render(request, 'billing_history_detail.html', {'record': record})


from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

def staff_login(request):
    # If already logged in, send straight to billing dashboard
    if request.user.is_authenticated:
        return redirect('billing_dashboard')

    error = False
    next_url = request.GET.get('next') or request.POST.get('next') or 'billing_dashboard'

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None and user.is_staff:
            # Check StaffProfile.is_active_staff if a profile exists
            profile = getattr(user, 'staff_profile', None)
            if profile is not None and not profile.is_active_staff:
                error = True
            else:
                login(request, user)
                return redirect('billing_dashboard')
        else:
            error = True

    return render(request, 'login.html', {'error': error, 'next': next_url})


def staff_logout(request):
    logout(request)
    return redirect('staff_login')