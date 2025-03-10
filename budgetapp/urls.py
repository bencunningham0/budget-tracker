from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('register/', views.register, name='register'),
    path('login/', auth_views.LoginView.as_view(template_name='budgetapp/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('settings/', views.user_settings, name='user_settings'),
    
    # Budget URLs
    path('budget/create/', views.budget_create, name='budget_create'),
    path('budget/<int:pk>/', views.budget_detail, name='budget_detail'),
    path('budget/<int:pk>/edit/', views.budget_edit, name='budget_edit'),
    path('budget/<int:pk>/delete/', views.budget_delete, name='budget_delete'),
    
    # Income URLs
    path('income/create/', views.income_create, name='income_create'),
    path('income/<int:pk>/', views.income_detail, name='income_detail'),
    path('income/<int:pk>/edit/', views.income_edit, name='income_edit'),
    path('income/<int:pk>/delete/', views.income_delete, name='income_delete'),
    
    # Income Transaction URLs
    path('income-transactions/', views.income_transaction_list, name='income_transaction_list'),
    path('income-transaction/create/', views.income_transaction_create, name='income_transaction_create'),
    path('income-transaction/<int:pk>/edit/', views.income_transaction_edit, name='income_transaction_edit'),
    path('income-transaction/<int:pk>/delete/', views.income_transaction_delete, name='income_transaction_delete'),
    path('income/<int:income_pk>/transaction/create/', views.income_transaction_create_for_income, name='income_transaction_create_for_income'),
    
    # Transaction URLs
    path('transaction/create/', views.transaction_create, name='transaction_create'),
    path('transaction/<int:pk>/edit/', views.transaction_edit, name='transaction_edit'),
    path('transaction/<int:pk>/delete/', views.transaction_delete, name='transaction_delete'),
    path('budget/<int:budget_pk>/transaction/create/', views.transaction_create_for_budget, name='transaction_create_for_budget'),
    
    # Recurring Transaction URLs
    path('recurring/', views.recurring_transaction_list, name='recurring_transaction_list'),
    path('recurring/create/', views.recurring_transaction_create, name='recurring_transaction_create'),
    path('recurring/<int:pk>/edit/', views.recurring_transaction_edit, name='recurring_transaction_edit'),
    path('recurring/<int:pk>/delete/', views.recurring_transaction_delete, name='recurring_transaction_delete'),
    path('recurring/<int:pk>/toggle/', views.recurring_transaction_toggle, name='recurring_transaction_toggle'),
]