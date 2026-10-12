from .models import Cart, CartItem
from .views import _cart_id


def counter(request):
    cart_count = 0

    # Skip cart counter for admin panel pages
    if 'admin' in request.path:
        return {}

    try:
        # If the user is authenticated, filter cart items directly by user
        if request.user.is_authenticated:
            cart_items = CartItem.objects.filter(user=request.user)
        else:
            # If the user is not authenticated, get cart using session id
            cart = Cart.objects.get(cart_id=_cart_id(request))
            cart_items = CartItem.objects.filter(cart=cart)

        # Calculate total quantity of items in the cart
        for cart_item in cart_items:
            cart_count += cart_item.quantity

    except (Cart.DoesNotExist, Exception):
        cart_count = 0

    return dict(cart_count=cart_count)