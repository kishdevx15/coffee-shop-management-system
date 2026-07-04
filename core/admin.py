from django.contrib import admin
from django.contrib import admin
from .models import StaffProfile  # add this import alongside your other model imports



# Register your models here.
from django.contrib import admin
from .models import Table, CustomerSession, Category, Product, Cart, CartItem


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ('table_number', 'is_available')
    list_editable = ('is_available',)


@admin.register(CustomerSession)
class CustomerSessionAdmin(admin.ModelAdmin):
    list_display = ('name', 'table', 'joined_at')
    list_filter = ('table',)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'category', 'is_available')
    list_filter = ('category', 'is_available')
    search_fields = ('name',)


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('session', 'created_at')


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('cart', 'product', 'quantity')
    



@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'phone_number', 'is_active_staff', 'created_at')
    list_filter = ('role', 'is_active_staff')
    search_fields = ('user__username', 'phone_number')