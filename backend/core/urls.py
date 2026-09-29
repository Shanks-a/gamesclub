from django.urls import path
from . import views
from . import management_api as management
from django.urls import include
management_urls = [
    path('session/', management.session_info),path('login/',management.session_login),path('logout/',management.session_logout),
    path('overview/',management.overview),path('upload/',management.upload),path('orders/',management.orders),path('orders/<int:pk>/',management.orders),path('audit/',management.audit),
    path('<str:resource>/',management.catalog),path('<str:resource>/<int:pk>/',management.catalog),
]
urlpatterns = [path('auth/dev-login/', views.dev_login), path('auth/wechat-login/', views.wechat_login), path('me/', views.me), path('games/', views.games), path('games/<int:pk>/categories/', views.game_categories), path('products/', views.products), path('products/<int:pk>/', views.product_detail), path('me/favorites/', views.favorites), path('me/favorites/<int:product_id>/', views.favorite_detail), path('me/orders/', views.orders), path('me/orders/<int:pk>/', views.order_detail), path('me/orders/<int:pk>/cancel/', views.cancel_order), path('me/orders/<int:pk>/mock-pay/', views.mock_pay), path('management/products/', views.management_products), path('management/products/<int:pk>/', views.management_product_detail), path('management/categories/', views.management_categories), path('management/categories/<int:pk>/', views.management_category_detail), path('management/products/<int:pk>/publish/', views.publish_product), path('management/products/<int:pk>/unpublish/', views.unpublish_product)]
urlpatterns = [path('auth/logout/',views.logout),path('home/',management.public_home),path('management/',include(management_urls))] + [p for p in urlpatterns if not str(p.pattern).startswith('management/')]
