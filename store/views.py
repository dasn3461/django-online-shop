from django.shortcuts import render, get_object_or_404
from .models import Product, Variation
from category.models import Category
from carts.models import CartItem
from carts.views import _cart_id
from django.core.paginator import EmptyPage,PageNotAnInteger,Paginator
from django.db.models import Q

# Create your views here.
def store(request, category_slug=None):
     categories = None
     products = None

     if category_slug !=None:
          categories = get_object_or_404(Category, slug=category_slug)
          products   = Product.objects.filter(category=categories,is_available=True)
          paginator = Paginator(products,1)
          page = request.GET.get('page')
          paged_products = paginator.get_page(page)
          product_count = products.count()

     else:
          products=Product.objects.all().filter(is_available=True).order_by('id')
          paginator = Paginator(products,3)
          page = request.GET.get('page')
          paged_products = paginator.get_page(page)
          product_count = products.count()   
          

     context = {
        'products': paged_products,
        'product_count': product_count
    }    

     return render(request, 'store/store.html', context)   




def product_detail(request, category_slug, product_slug):

    single_product = Product.objects.get(
        category__slug=category_slug,
        slug=product_slug
    )

    in_cart = CartItem.objects.filter(
        cart__cart_id=_cart_id(request),
        product=single_product
    ).exists()

    context = {
        'single_product': single_product,
        'in_cart': in_cart,
        'colors': single_product.variation_set.colors(),
        'sizes': single_product.variation_set.sizes(),
    }

    return render(request, 'store/product_detail.html', context)



def search(request):
    products = Product.objects.filter(is_available=True).order_by('id')
    if 'keyword' in request.GET:
        keyword = request.GET['keyword']
        if keyword:
                products = products.filter(
                    Q(product_name__icontains=keyword) |
                    Q(description__icontains=keyword)
               )
        product_count = products.count()
        context = {
             'products': products,
             'product_count': product_count
            }
        return render(request,'store/store.html',context)






    
    







