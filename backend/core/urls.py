from django.urls import path
from . import views
from . import community_api as community
from . import management_api as management
from . import support_chat
from django.urls import include
management_urls = [
    path('support-conversations/', support_chat.staff_threads),
    path('support-conversations/<int:pk>/', support_chat.staff_threads),
    path('support-settings/', management.support_settings),
    path('orders/<int:pk>/start/', management.order_start),
    path('orders/<int:pk>/complete/', management.order_complete),
    path('session/', management.session_info),path('login/',management.session_login),path('logout/',management.session_logout),
    path('overview/',management.overview),path('upload/',management.upload),path('orders/',management.orders),path('orders/create/',management.order_create),path('orders/<int:pk>/',management.orders),path('orders/<int:pk>/edit/',management.order_update),path('orders/<int:pk>/delete/',management.order_delete),path('orders/<int:pk>/assign/',management.order_assign),path('customers/',management.customers),path('audit/',management.audit),
    path('partner-applications/',management.partner_applications),path('partner-applications/<int:pk>/',management.partner_applications),path('partner-applications/<int:pk>/approve/',management.partner_application_approve),path('partner-applications/<int:pk>/reject/',management.partner_application_reject),
    path('partners/',management.partners),path('partners/<int:pk>/',management.partners),path('partners/<int:pk>/edit/',management.partner_detail),path('partners/<int:pk>/delete/',management.partner_delete),
    path('aftersales/',management.aftersales),path('aftersales/<int:pk>/',management.aftersales),path('aftersales/<int:pk>/review/',management.aftersale_review),path('refunds/<int:pk>/',management.refund_execute),path('refunds/<int:pk>/execute/',management.refund_execute),path('orders/<int:pk>/cancel-refund/',management.cancel_refund),path('settings/',management.settings),path('settlements/',management.settlements),path('settlements/<int:pk>/',management.settlements),
    path('<str:resource>/',management.catalog),path('<str:resource>/<int:pk>/',management.catalog),
]
urlpatterns = [path('auth/dev-login/', views.dev_login), path('auth/wechat-login/', views.wechat_login), path('me/', views.me), path('me/avatar/', views.upload_avatar), path('me/partner-application/', views.partner_application), path('me/partner/orders/', views.partner_orders), path('me/partner/orders/<int:pk>/accept/', views.partner_accept), path('me/partner/orders/<int:pk>/reject/', views.partner_reject), path('me/partner/orders/<int:pk>/start/', views.partner_start), path('me/partner/orders/<int:pk>/complete/', views.partner_complete), path('me/orders/<int:pk>/confirm/', views.confirm_order), path('me/orders/<int:pk>/review/', views.review), path('me/orders/<int:pk>/aftersale/', views.aftersale), path('me/aftersale-evidence/', views.upload_evidence), path('me/conversations/', views.conversations), path('me/conversations/<int:pk>/messages/', views.conversation_messages), path('me/conversations/<int:pk>/send/', views.conversation_send), path('games/', views.games), path('games/<int:pk>/categories/', views.game_categories), path('games/<int:pk>/partners/', views.game_partners), path('products/', views.products), path('products/<int:pk>/', views.product_detail), path('me/favorites/', views.favorites), path('me/favorites/<int:product_id>/', views.favorite_detail), path('me/orders/', views.orders), path('me/orders/<int:pk>/', views.order_detail), path('me/orders/<int:pk>/cancel/', views.cancel_order), path('me/orders/<int:pk>/mock-pay/', views.mock_pay), path('management/products/', views.management_products), path('management/products/<int:pk>/', views.management_product_detail), path('management/categories/', views.management_categories), path('management/categories/<int:pk>/', views.management_category_detail), path('management/products/<int:pk>/publish/', views.publish_product), path('management/products/<int:pk>/unpublish/', views.unpublish_product)]
urlpatterns = [path('auth/logout/',views.logout),path('home/',management.public_home),path('management/',include(management_urls))] + [p for p in urlpatterns if not str(p.pattern).startswith('management/')]
urlpatterns += [
    path('me/support-conversations/', support_chat.customer_threads),
    path('me/support-conversations/<int:pk>/', support_chat.customer_threads),
    path('me/conversations/<int:pk>/', views.conversation_detail),
    path('auth/dev-accounts/', views.dev_accounts),
    path('support/', management.public_support),
    path('games/<int:game_id>/posts/', community.game_posts),
    path('games/<int:game_id>/leaderboard/', community.leaderboard),
    path('community/images/', community.upload_image),
    path('community/posts/<int:pk>/', community.delete_post),
    path('community/posts/<int:pk>/like/', community.post_like),
    path('community/posts/<int:pk>/comments/', community.post_comments),
    path('community/comments/<int:pk>/', community.delete_comment),
]
