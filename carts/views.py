from django.shortcuts import render, redirect, get_object_or_404
from store.models import Product, Variation
from .models import Cart, CartItem
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

# Create your views here.
def _cart_id(request):
    cart = request.session.session_key
    if not cart:
        request.session.create()
        cart = request.session.session_key
    return cart


def add_cart(request, product_id):
    current_user = request.user
    product = Product.objects.get(id=product_id)
    
    # Get selected variations from POST data
    product_variation = []
    if request.method == 'POST':
        for key, value in request.POST.items():
            if key == 'csrfmiddlewaretoken':
                continue
            try:
                variation = Variation.objects.get(
                    product=product,
                    variation_category__iexact=key,
                    variation_value__iexact=value
                )
                product_variation.append(variation)
            except Variation.DoesNotExist:
                pass

    # Handle Cart (Get or Create)
    try:
        cart = Cart.objects.get(cart_id=_cart_id(request))
    except Cart.DoesNotExist:
        cart = Cart.objects.create(cart_id=_cart_id(request))

    # Determine filter query based on authentication status
    if current_user.is_authenticated:
        cart.user = current_user
        cart.save()
        cart_item_filter = {'product': product, 'user': current_user}
    else:
        cart_item_filter = {'product': product, 'cart': cart}

    # Check whether product already exists in cart
    is_cart_item_exists = CartItem.objects.filter(**cart_item_filter).exists()

    if is_cart_item_exists:
        cart_items = CartItem.objects.filter(**cart_item_filter)

        existing_variations_list = []
        item_ids = []

        for item in cart_items:
            existing_variations = item.variation.all()
            existing_variations_list.append(list(existing_variations))
            item_ids.append(item.id)

        # Check whether selected variations already exist
        if product_variation in existing_variations_list:
            index = existing_variations_list.index(product_variation)
            item_id = item_ids[index]

            get_kwargs = {'product': product, 'id': item_id}
            if current_user.is_authenticated:
                get_kwargs['user'] = current_user
            else:
                get_kwargs['cart'] = cart

            cart_item = CartItem.objects.get(**get_kwargs)
            cart_item.quantity += 1
            cart_item.save()
        else:
            create_kwargs = {'product': product, 'quantity': 1}
            if current_user.is_authenticated:
                create_kwargs['user'] = current_user
            else:
                create_kwargs['cart'] = cart

            cart_item = CartItem.objects.create(**create_kwargs)
            if product_variation:
                cart_item.variation.add(*product_variation)
            cart_item.save()
    else:
        create_kwargs = {'product': product, 'quantity': 1}
        if current_user.is_authenticated:
            create_kwargs['user'] = current_user
        else:
            create_kwargs['cart'] = cart

        cart_item = CartItem.objects.create(**create_kwargs)
        if product_variation:
            cart_item.variation.add(*product_variation)
        cart_item.save()

    return redirect('cart')


def cart(request, total=0, quantity=0, cart_item=None):
    tax = 0
    grand_total = 0
    cart_items = CartItem.objects.none()
    
    try:
        if request.user.is_authenticated:
            cart_items = CartItem.objects.filter(user=request.user, is_active=True)
        else:
            cart = Cart.objects.get(cart_id=_cart_id(request))
            cart_items = CartItem.objects.filter(cart=cart, is_active=True)

        for cart_item in cart_items:
            total += cart_item.product.price * cart_item.quantity
            quantity += cart_item.quantity
        
        tax = (2 * total) / 100  
        grand_total = total + tax

    except Cart.DoesNotExist:
        pass

    context = {
        'total': total,
        'quantity': quantity,
        'cart_items': cart_items,
        'tax': tax,
        'grand_total': grand_total,
    }

    return render(request, 'store/cart.html', context)


def remove_cart(request, product_id, cart_item_id):
    product = get_object_or_404(Product, id=product_id)
    try:
        if request.user.is_authenticated:
            cart_item = CartItem.objects.get(product=product, user=request.user, id=cart_item_id)
        else:
            cart = Cart.objects.get(cart_id=_cart_id(request))
            cart_item = CartItem.objects.get(product=product, cart=cart, id=cart_item_id)
            
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
        else:
            cart_item.delete()
    except:
        pass
    return redirect('cart')


def remove_cart_item(request, product_id, cart_item_id):
    product = get_object_or_404(Product, id=product_id)
    try:
        if request.user.is_authenticated:
            cart_item = CartItem.objects.get(product=product, user=request.user, id=cart_item_id)
        else:
            cart = Cart.objects.get(cart_id=_cart_id(request))
            cart_item = CartItem.objects.get(product=product, cart=cart, id=cart_item_id)
        cart_item.delete()
    except:
        pass
    return redirect('cart')


@login_required(login_url='login')
def checkout(request, total=0, quantity=0, cart_item=None):
    tax = 0
    grand_total = 0
    cart_items = CartItem.objects.none()

    try:
        # If the user is authenticated, filter cart items by user
        if request.user.is_authenticated:
            cart_items = CartItem.objects.filter(user=request.user, is_active=True)
        else:
            cart = Cart.objects.get(cart_id=_cart_id(request))
            cart_items = CartItem.objects.filter(cart=cart, is_active=True)

        for cart_item in cart_items:
            total += cart_item.product.price * cart_item.quantity
            quantity += cart_item.quantity

        tax = (1.5 * total) / 100
        grand_total = total + tax

    except Cart.DoesNotExist:
        pass

    context = {
        'total': total,
        'quantity': quantity,
        'cart_items': cart_items,
        'tax': tax,
        'grand_total': grand_total,
    }
    return render(request, 'store/checkout.html', context)