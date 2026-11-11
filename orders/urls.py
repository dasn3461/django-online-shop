from django.urls import path
from . import views

urlpatterns = [
    path('place_order/', views.place_order, name='place_order'),
    path('payments/', views.payments, name='payments'),

    path('ssl-success/', views.ssl_success, name='ssl_success'),
    path('ssl-fail/', views.ssl_fail, name='ssl_fail'),
    path('ssl-cancel/', views.ssl_cancel, name='ssl_cancel'),

    path('order_complete/', views.order_complete, name='order_complete'),
]
