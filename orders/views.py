import datetime
import requests

from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode

from django.shortcuts import render, redirect
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.urls import reverse
from django.core.mail import EmailMessage
from django.template.loader import render_to_string

from carts.models import CartItem
from .forms import OrderForm
from .models import Order, Payment, OrderProduct


# =====================================
# 1. PLACE ORDER
# =====================================

def place_order(request):

    current_user = request.user

    cart_items = CartItem.objects.filter(
        user=current_user,
        is_active=True
    )

    if not cart_items.exists():
        return redirect('store')

    total = 0

    for item in cart_items:
        total += item.product.price * item.quantity

    tax = (Decimal(total) * Decimal('2')) / Decimal('100')
    grand_total = Decimal(total) + tax

    if request.method == 'POST':

        form = OrderForm(request.POST)

        if form.is_valid():

            order = Order()

            order.user = current_user
            order.first_name = form.cleaned_data['first_name']
            order.last_name = form.cleaned_data['last_name']
            order.phone = form.cleaned_data['phone']
            order.email = form.cleaned_data['email']
            order.address_line_1 = form.cleaned_data['address_line_1']
            order.address_line_2 = form.cleaned_data['address_line_2']
            order.country = form.cleaned_data['country']
            order.division = form.cleaned_data['division']
            order.city = form.cleaned_data['city']
            order.order_note = form.cleaned_data['order_note']

            order.order_total = grand_total
            order.tax = tax
            order.ip = request.META.get('REMOTE_ADDR')

            order.save()

            current_date = datetime.date.today().strftime('%Y%m%d')
            order.order_number = current_date + str(order.id)

            order.save()

            context = {
                'order': order,
                'cart_items': cart_items,
                'total': total,
                'grand_total': grand_total,
                'tax': tax,
            }

            return render(request, 'orders/payments.html', context)

    return redirect('checkout')


# =====================================
# 2. SSL COMMERZ PAYMENT
# =====================================

def payments(request):

    order = Order.objects.filter(
        user=request.user,
        is_ordered=False
    ).order_by('-created_at').first()

    if not order:
        return redirect('checkout')

    # Sandbox or Live URL
    if settings.SSLCOMMERZ['issandbox']:
        api_url = 'https://sandbox.sslcommerz.com/gwprocess/v4/api.php'
    else:
        api_url = 'https://securepay.sslcommerz.com/gwprocess/v4/api.php'

    # Payment information
    post_data = {
        'store_id': settings.SSLCOMMERZ['store_id'],
        'store_passwd': settings.SSLCOMMERZ['store_pass'],

        'total_amount': str(order.order_total),
        'currency': 'BDT',
        'tran_id': order.order_number,

        'success_url': request.build_absolute_uri('/orders/ssl-success/'),
        'fail_url': request.build_absolute_uri('/orders/ssl-fail/'),
        'cancel_url': request.build_absolute_uri('/orders/ssl-cancel/'),

        'cus_name': order.full_name(),
        'cus_email': order.email,
        'cus_add1': order.address_line_1,
        'cus_add2': order.address_line_2 or 'N/A',
        'cus_city': order.city,
        'cus_state': order.division,
        'cus_postcode': '1200',
        'cus_country': order.country,
        'cus_phone': order.phone,

        'shipping_method': 'NO',
        'product_name': 'General Product',
        'product_category': 'General',
        'product_profile': 'general-physical',
    }

    # Send request to SSLCommerz
    try:

        response = requests.post(
            api_url,
            data=post_data,
            timeout=30
        )

        response.raise_for_status()
        result = response.json()

        if result.get('status') == 'SUCCESS' and result.get('GatewayPageURL'):
            return redirect(result['GatewayPageURL'])

        return render(request, 'orders/payment_fail.html', {
            'error': result.get('failedreason', 'Payment initialization failed.')
        })

    except requests.RequestException as e:

        print('Payment Error:', e)

        return render(request, 'orders/payment_fail.html', {
            'error': 'Could not connect to SSLCommerz.'
        })

    except ValueError:

        return render(request, 'orders/payment_fail.html', {
            'error': 'Invalid SSLCommerz response.'
        })


# =====================================
# 3. SSL COMMERZ SUCCESS
# =====================================

@csrf_exempt

@csrf_exempt
def ssl_success(request):

    if request.method != 'POST':
        return redirect('home')

    val_id = request.POST.get('val_id')
    tran_id = request.POST.get('tran_id')

    if not val_id or not tran_id:
        return redirect('home')

    try:
        order = Order.objects.get(
            order_number=tran_id,
            is_ordered=False
        )
    except Order.DoesNotExist:
        return redirect('home')

    # SSLCommerz validation URL
    if settings.SSLCOMMERZ['issandbox']:
        validation_url = 'https://sandbox.sslcommerz.com/validator/api/validationserverAPI.php'
    else:
        validation_url = 'https://securepay.sslcommerz.com/validator/api/validationserverAPI.php'

    data = {
        'val_id': val_id,
        'store_id': settings.SSLCOMMERZ['store_id'],
        'store_passwd': settings.SSLCOMMERZ['store_pass'],
        'format': 'json',
    }

    try:
        response = requests.get(validation_url, params=data, timeout=30)
        response.raise_for_status()
        result = response.json()

    except (requests.RequestException, ValueError):
        return redirect('home')

    # Payment verification
    if result.get('status') not in ['VALID', 'VALIDATED']:
        return redirect('home')

    if result.get('tran_id') != order.order_number:
        return redirect('home')

    try:
        paid_amount = Decimal(str(result.get('amount')))
        order_amount = Decimal(str(order.order_total))

        if paid_amount.quantize(Decimal('0.01')) != order_amount.quantize(Decimal('0.01')):
            return redirect('home')

    except (InvalidOperation, TypeError, ValueError):
        return redirect('home')

    if result.get('currency') != 'BDT':
        return redirect('home')

    try:
        with transaction.atomic():

            order = Order.objects.select_for_update().get(id=order.id)

            if order.is_ordered:
                return redirect('home')

            cart_items = CartItem.objects.filter(
                user=order.user,
                is_active=True
            ).select_related('product')

            if not cart_items.exists():
                raise ValueError('Cart is empty')

            # Check stock
            for item in cart_items:
                if item.product.stock < item.quantity:
                    raise ValueError('Product stock is not available')

            # Save payment
            payment = Payment.objects.create(
                user=order.user,
                payment_id=val_id,
                payment_method='SSLCommerz',
                amount_paid=str(paid_amount),
                status='COMPLETED'
            )

            # Save order products
            for item in cart_items:

                orderproduct = OrderProduct.objects.create(
                    order=order,
                    payment=payment,
                    user=order.user,
                    product=item.product,
                    quantity=item.quantity,
                    product_price=item.product.price,
                    ordered=True
                )

                orderproduct.variation.set(item.variation.all())

                item.product.stock -= item.quantity
                item.product.save(update_fields=['stock'])

            order.payment = payment
            order.is_ordered = True
            order.save()

            cart_items.delete()

    except (Order.DoesNotExist, ValueError) as e:
        return render(request, 'orders/payment_fail.html', {
            'error': str(e)
        })

    # Send email
    try:
        message = render_to_string(
            'orders/order_recieved_email.html',
            {'user': order.user, 'order': order}
        )

        email = EmailMessage(
            'Thank you for your order',
            message,
            settings.EMAIL_HOST_USER,
            [order.email]
        )

        email.content_subtype = 'html'
        email.send()

    except Exception as e:
        print('Email Error:', e)

    # Redirect to order complete
    query_string = urlencode({
        'order_number': order.order_number,
        'payment_id': payment.payment_id,
    })

    return redirect(f"{reverse('order_complete')}?{query_string}")



# =====================================
# 4. PAYMENT FAILED
# =====================================

@csrf_exempt
def ssl_fail(request):

    return render(request, 'orders/payment_fail.html')


# =====================================
# 5. PAYMENT CANCELLED
# =====================================

@csrf_exempt
def ssl_cancel(request):

    return render(request, 'orders/payment_cancel.html')


# =====================================
# 6. ORDER COMPLETE
# =====================================

def order_complete(request):

    order_number = request.GET.get('order_number')
    transID = request.GET.get('payment_id')

    try:

        order = Order.objects.get(
            order_number=order_number,
            is_ordered=True
        )

        payment = Payment.objects.get(
            payment_id=transID,
            user=order.user
        )

        order_products = OrderProduct.objects.filter(order=order)

        subtotal = sum(
            item.product_price * item.quantity
            for item in order_products
        )

        context = {
            'order': order,
            'payment': payment,
            'order_products': order_products,
            'transID': payment.payment_id,
            'subtotal': subtotal,
        }

        return render(request, 'orders/order_complete.html', context)

    except (Order.DoesNotExist, Payment.DoesNotExist):

        return redirect('home')
