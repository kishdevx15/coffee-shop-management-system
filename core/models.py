from django.db import models
from django.contrib.auth.models import User
import uuid

# Create your models here.
class Table(models.Model):
    table_number = models.IntegerField(unique=True)
    is_available = models.BooleanField(default=True)


class CustomerSession(models.Model):
    session_id = models.UUIDField(default=uuid.uuid4, unique=True)

    name = models.CharField(max_length=100, blank=True, null=True)
    # 👆 this is the "customer name"

    table = models.ForeignKey("Table", on_delete=models.CASCADE)

    joined_at = models.DateTimeField(auto_now_add=True)
    
class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(upload_to='category_images/', blank=True, null=True)

    def __str__(self):
        return self.name
    


class Product(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=7, decimal_places=2)

    category = models.ForeignKey(
        'Category',
        on_delete=models.CASCADE,
        related_name='products'
    )

    image = models.ImageField(upload_to='products/', blank=True, null=True)
    is_available = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name
    
class Cart(models.Model):
    session = models.ForeignKey(CustomerSession, on_delete=models.CASCADE)

    created_at = models.DateTimeField(auto_now_add=True)

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE)

    product = models.ForeignKey("Product", on_delete=models.CASCADE)

    quantity = models.PositiveIntegerField(default=1)




class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('making',  'Making'),
        ('done',    'Done'),
    ]

    # Store customer name as plain text — no FK to CustomerSession
    customer_name  = models.CharField(max_length=100)
    table_number   = models.IntegerField()
    status         = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    placed_at      = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    def get_total(self):
        return sum(item.subtotal() for item in self.items.all())

    def __str__(self):
        return f"Order #{self.id} — {self.customer_name} (Table {self.table_number})"


class OrderItem(models.Model):
    order         = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product_name  = models.CharField(max_length=100)   # snapshot — no FK to Product
    quantity      = models.PositiveIntegerField()
    price         = models.DecimalField(max_digits=7, decimal_places=2)  # snapshot

    def subtotal(self):
        return self.price * self.quantity

    def __str__(self):
        return f"{self.quantity}x {self.product_name}"
    
    
class BillingRecord(models.Model):
    """
    Saved whenever a bill is finalised and WhatsApp is sent.
    Snapshots everything so history survives even after the Order is deleted.
    """
    order          = models.OneToOneField(
        'Order', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='billing'
    )
    customer_name  = models.CharField(max_length=100)
    table_number   = models.IntegerField()
    phone_number   = models.CharField(max_length=20, blank=True)   # with country code
 
    # Snapshot of items: [{"name": "...", "qty": 2, "price": "60.00", "subtotal": "120.00"}, ...]
    items_snapshot = models.JSONField(default=list)
 
    total_amount   = models.DecimalField(max_digits=10, decimal_places=2)
 
    billed_at      = models.DateTimeField(auto_now_add=True)
 
    class Meta:
        ordering = ['-billed_at']
 
    def __str__(self):
        return f"Bill #{self.id} — {self.customer_name} (Table {self.table_number})"
    
class StaffProfile(models.Model):
    ROLE_CHOICES = [
        ('kitchen', 'Kitchen Staff'),
        ('billing', 'Billing Staff'),
        ('manager', 'Manager'),
        ('admin', 'Admin'),
    ]
 
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='staff_profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='kitchen')
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    is_active_staff = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
 
    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"
 
    class Meta:
        verbose_name = "Staff Profile"
        verbose_name_plural = "Staff Profiles"
        
        
