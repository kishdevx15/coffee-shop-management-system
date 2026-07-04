"""
URL configuration for coffee_self_service project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from core.views import *
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', start),
    path('Table-booking', table_booking),
    path('user_data', userdata, name='user_data'),
    path('category', category_detail, name='category_detail'),
    path('search/', search_view, name='search'),
    path('add-to-cart', add_to_cart, name='add_to_cart'),
    path('cart/', cart_view, name='cart'),
    path('cart/update/<int:item_id>/', update_quantity, name='cart_update'),
    path('cart/remove/<int:item_id>/', remove_item, name='cart_remove'),
    path('cart/place-order/', place_order, name='cart_place_order'),
    path('orders/', order_history, name='order_history'),
    path('orders/<int:order_id>/status/', update_order_status, name='order_status_update'),
    path('order/<int:order_id>/status/', order_status, name='order_status'),
    path('order/status/', order_status_session, name='order_status_session'),
    path("kitchen/", kitchen_dashboard,name="kitchen_dashboard"),
    path("kitchen/orders/",kitchen_orders,name="kitchen_orders"),
    path("kitchen/orders/<int:order_id>/status/",kitchen_update_status, name="kitchen_update_status"),
     path('billing/',billing_dashboard,name='billing_dashboard'),
    path('billing/order/<int:order_id>/',billing_detail,name='billing_detail'),
    path('billing/order/<int:order_id>/finalise/',finalise_bill,   name='finalise_bill'),
    path('billing/history/<int:bill_id>/',billing_history_detail, name='billing_history_detail'),

    # --- staff auth (newly added) ---
    path('staff-login/', staff_login, name='staff_login'),
    path('staff-logout/', staff_logout, name='staff_logout'),
]

urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)