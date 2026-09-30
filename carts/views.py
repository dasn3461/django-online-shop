from django.shortcuts import render, redirect,get_object_or_404
from store.models import Product,Variation
from .models import Cart, CartItem
from django.http import HttpResponse

# Create your views here.
def _cart_id(request):
    cart = request.session.session_key
    if not cart:
        request.session.create()
        cart = request.session.session_key
    return cart




def add_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product_variation = []

    # 1. Fetch requested variations from POST data
    if request.method == "POST":
        for item in request.POST:
            key = item
            value = request.POST[key]

            try:
                variation = Variation.objects.get(
                    product=product,
                    variation_category__iexact=key,
                    variation_value__iexact=value
                )
                product_variation.append(variation)
            except Variation.DoesNotExist:
                pass

    # Sort product variations so list comparison is reliable
    product_variation = sorted(product_variation, key=lambda x: x.id)

    # 2. Get or Create Cart
    try:
        cart = Cart.objects.get(cart_id=_cart_id(request))
    except Cart.DoesNotExist:
        cart = Cart.objects.create(cart_id=_cart_id(request))
    cart.save()

    # 3. Check existing Cart Items
    cart_items = CartItem.objects.filter(product=product, cart=cart)

    if cart_items.exists():
        ex_var_list = []
        item_ids = []

        for item in cart_items:
            # Sort existing variations by ID for accurate comparison
            existing_variation = list(item.variation.all().order_by('id'))
            ex_var_list.append(existing_variation)
            item_ids.append(item.id)

        # 4. Update quantity if variation matches
        if product_variation in ex_var_list:
            index = ex_var_list.index(product_variation)
            item_id = item_ids[index]
            
            cart_item = CartItem.objects.get(product=product, id=item_id)
            cart_item.quantity += 1
            cart_item.save()
        else:
            # Create new cart item for different variation
            cart_item = CartItem.objects.create(
                product=product,
                cart=cart,
                quantity=1
            )
            if product_variation:
                cart_item.variation.add(*product_variation)
            cart_item.save()

    else:
        # Create brand new cart item
        cart_item = CartItem.objects.create(
            product=product,
            cart=cart,
            quantity=1
        )
        if product_variation:
            cart_item.variation.add(*product_variation)
        cart_item.save()

    return redirect('cart')





def cart(request, total=0, quantity=0, cart_item=None):
    cart_items = CartItem.objects.none()
    tax = 0
    grand_total = 0

    try:
        cart = Cart.objects.get(cart_id=_cart_id(request))

        cart_items = CartItem.objects.filter(
            cart=cart,
            is_active=True
        )

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
        'grand_total': grand_total
    }

    return render(request, 'store/cart.html', context)



def remove_cart(request, product_id, cart_item_id):
    cart = Cart.objects.get(cart_id=_cart_id(request))
    product = get_object_or_404(Product, id=product_id)
    try:
        cart_item = CartItem.objects.get(product=product, cart=cart, id=cart_item_id)
        if cart_item.quantity > 1:
            cart_item.quantity -=1
            cart_item.save()
        else:
            cart_item.delete()
    except:
        pass
    return redirect('cart')



def remove_cart_item(request, product_id, cart_item_id):
    cart = Cart.objects.get(cart_id=_cart_id(request))
    product = get_object_or_404(Product, id=product_id)
    cart_item = CartItem.objects.get(product=product, cart=cart, id=cart_item_id)
    cart_item.delete()
    return redirect('cart')