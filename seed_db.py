import os
import django
from decimal import Decimal
from django.utils import timezone

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'alx_backend_graphql.settings')
django.setup()

from crm.models import Customer, Product, Order


def clear_database():
    """Clear existing data from the database."""
    print("Clearing existing data...")
    Order.objects.all().delete()
    Customer.objects.all().delete()
    Product.objects.all().delete()
    print("Database cleared successfully.\n")


def create_customers():
    """Create sample customers."""
    print("Creating customers...")
    customers = [
        {"name": "Alice Johnson", "email": "alice@example.com", "phone": "+1234567890"},
        {"name": "Bob Smith", "email": "bob@example.com", "phone": "123-456-7890"},
        {"name": "Carol Williams", "email": "carol@example.com", "phone": ""},
        {"name": "David Brown", "email": "david@example.com", "phone": "+44-20-1234-5678"},
        {"name": "Eve Davis", "email": "eve@example.com", "phone": "555.123.4567"},
    ]

    created_customers = []
    for customer_data in customers:
        customer = Customer.objects.create(**customer_data)
        created_customers.append(customer)
        print(f"Created customer: {customer.name} ({customer.email})")

    print(f"Total customers created: {len(created_customers)}\n")
    return created_customers


def create_products():
    """Create sample products."""
    print("Creating products...")
    products = [
        {"name": "Laptop", "price": Decimal("999.99"), "stock": 10},
        {"name": "Mouse", "price": Decimal("25.50"), "stock": 50},
        {"name": "Keyboard", "price": Decimal("75.00"), "stock": 30},
        {"name": "Monitor", "price": Decimal("299.99"), "stock": 15},
        {"name": "Headphones", "price": Decimal("149.99"), "stock": 25},
        {"name": "Webcam", "price": Decimal("89.99"), "stock": 20},
        {"name": "USB Cable", "price": Decimal("12.99"), "stock": 100},
    ]

    created_products = []
    for product_data in products:
        product = Product.objects.create(**product_data)
        created_products.append(product)
        print(f"Created product: {product.name} - ${product.price} (Stock: {product.stock})")

    print(f"Total products created: {len(created_products)}\n")
    return created_products


def create_orders(customers, products):
    """Create sample orders."""
    print("Creating orders...")
    orders_data = [
        {
            "customer": customers[0],  # Alice
            "products": [products[0], products[1]],  # Laptop, Mouse
        },
        {
            "customer": customers[1],  # Bob
            "products": [products[2], products[3]],  # Keyboard, Monitor
        },
        {
            "customer": customers[2],  # Carol
            "products": [products[4]],  # Headphones
        },
        {
            "customer": customers[3],  # David
            "products": [products[1], products[2], products[6]],  # Mouse, Keyboard, USB Cable
        },
        {
            "customer": customers[0],  # Alice (second order)
            "products": [products[5], products[6]],  # Webcam, USB Cable
        },
    ]

    created_orders = []
    for idx, order_data in enumerate(orders_data, 1):
        # Calculate total amount
        total_amount = sum(product.price for product in order_data["products"])

        # Create order
        order = Order.objects.create(
            customer=order_data["customer"],
            order_date=timezone.now(),
            total_amount=total_amount
        )

        # Add products to order
        order.products.set(order_data["products"])
        created_orders.append(order)

        product_names = ", ".join([p.name for p in order_data["products"]])
        print(f"Created order #{order.id} for {order.customer.name}: {product_names} - Total: ${total_amount}")

    print(f"Total orders created: {len(created_orders)}\n")
    return created_orders


def main():
    """Main function to seed the database."""
    print("=" * 60)
    print("Starting database seeding process...")
    print("=" * 60 + "\n")

    try:
        # Clear existing data
        clear_database()

        # Create sample data
        customers = create_customers()
        products = create_products()
        orders = create_orders(customers, products)

        print("=" * 60)
        print("Database seeding completed successfully!")
        print("=" * 60)
        print(f"\nSummary:")
        print(f"  - Customers: {Customer.objects.count()}")
        print(f"  - Products: {Product.objects.count()}")
        print(f"  - Orders: {Order.objects.count()}")
        print("\nYou can now test GraphQL queries and mutations at /graphql")

    except Exception as e:
        print(f"\nError during seeding: {str(e)}")
        raise


if __name__ == "__main__":
    main()