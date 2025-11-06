import graphene
from graphql_jwt.decorators import login_required
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from django.db import transaction
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from decimal import Decimal
from crm.models import Product
import re
from .models import Customer, Product, Order
from .filters import CustomerFilter, ProductFilter, OrderFilter


# Define Object Types with relay support for filtering
class CustomerType(DjangoObjectType):
    class Meta:
        model = Customer
        fields = '__all__'
        filterset_class = CustomerFilter
        interfaces = (graphene.relay.Node,)


class ProductType(DjangoObjectType):
    class Meta:
        model = Product
        fields = '__all__'
        filterset_class = ProductFilter
        interfaces = (graphene.relay.Node,)


class OrderType(DjangoObjectType):
    class Meta:
        model = Order
        fields = '__all__'
        filterset_class = OrderFilter
        interfaces = (graphene.relay.Node,)


# Helper function to validate phone format
def validate_phone(phone):
    """
    Validates phone format: +1234567890 or 123-456-7890
    """
    if not phone:
        return True
    
    pattern = r'^(\+\d{10,15}|\d{3}-\d{3}-\d{4})$'
    return re.match(pattern, phone) is not None


# Error type for bulk operations
class CustomerErrorType(graphene.ObjectType):
    email = graphene.String()
    message = graphene.String()


class CustomerInputType(graphene.InputObjectType):
    name = graphene.String(required=True)
    email = graphene.String(required=True)
    phone = graphene.String()


# CreateCustomer Mutation
class CreateCustomer(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        email = graphene.String(required=True)
        phone = graphene.String()

    customer = graphene.Field(CustomerType)
    success = graphene.Boolean()
    message = graphene.String()

    def mutate(self, info, name, email, phone=None):
        # Validate email format
        try:
            validate_email(email)
        except ValidationError:
            return CreateCustomer(
                customer=None,
                success=False,
                message="Invalid email format"
            )

        # Check for duplicate email
        if Customer.objects.filter(email=email).exists():
            return CreateCustomer(
                customer=None,
                success=False,
                message="Email already exists"
            )

        # Validate phone format if provided
        if phone and not validate_phone(phone):
            return CreateCustomer(
                customer=None,
                success=False,
                message="Invalid phone format. Use +1234567890 or 123-456-7890"
            )

        # Create customer
        try:
            customer = Customer.objects.create(
                name=name,
                email=email,
                phone=phone
            )
            return CreateCustomer(
                customer=customer,
                success=True,
                message="Customer created successfully"
            )
        except Exception as e:
            return CreateCustomer(
                customer=None,
                success=False,
                message=f"Error creating customer: {str(e)}"
            )


# BulkCreateCustomers Mutation
class BulkCreateCustomers(graphene.Mutation):
    class Arguments:
        customers = graphene.List(CustomerInputType, required=True)

    created_customers = graphene.List(CustomerType)
    errors = graphene.List(CustomerErrorType)
    success_count = graphene.Int()
    error_count = graphene.Int()

    def mutate(self, info, customers):
        created = []
        errors = []

        for customer_data in customers:
            name = customer_data.name
            email = customer_data.email
            phone = customer_data.phone

            # Validate email format
            try:
                validate_email(email)
            except ValidationError:
                errors.append(CustomerErrorType(
                    email=email,
                    message="Invalid email format"
                ))
                continue

            # Check for duplicate email
            if Customer.objects.filter(email=email).exists():
                errors.append(CustomerErrorType(
                    email=email,
                    message="Email already exists"
                ))
                continue

            # Validate phone format if provided
            if phone and not validate_phone(phone):
                errors.append(CustomerErrorType(
                    email=email,
                    message="Invalid phone format"
                ))
                continue

            # Create customer in transaction
            try:
                with transaction.atomic():
                    customer = Customer.objects.create(
                        name=name,
                        email=email,
                        phone=phone
                    )
                    created.append(customer)
            except Exception as e:
                errors.append(CustomerErrorType(
                    email=email,
                    message=f"Error creating customer: {str(e)}"
                ))

        return BulkCreateCustomers(
            created_customers=created,
            errors=errors,
            success_count=len(created),
            error_count=len(errors)
        )


# CreateProduct Mutation
class CreateProduct(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        price = graphene.Decimal(required=True)
        stock = graphene.Int(default_value=0)

    product = graphene.Field(ProductType)
    success = graphene.Boolean()
    message = graphene.String()

    def mutate(self, info, name, price, stock=0):
        # Validate price is positive
        if price <= 0:
            return CreateProduct(
                product=None,
                success=False,
                message="Price must be positive"
            )

        # Validate stock is not negative
        if stock < 0:
            return CreateProduct(
                product=None,
                success=False,
                message="Stock cannot be negative"
            )

        # Create product
        try:
            product = Product.objects.create(
                name=name,
                price=price,
                stock=stock
            )
            return CreateProduct(
                product=product,
                success=True,
                message="Product created successfully"
            )
        except Exception as e:
            return CreateProduct(
                product=None,
                success=False,
                message=f"Error creating product: {str(e)}"
            )

# Update Low Stock Mutation
class UpdateLowStockProducts(graphene.Mutation):
    success_message = graphene.String()
    updated_products = graphene.List(graphene.String)

    class Arguments:
        # No arguments are needed for this mutation; it operates on the stock condition
        pass

    @login_required
    def mutate(self, info):
        # Query products where stock < 10
        low_stock_products = Product.objects.filter(stock__lt=10)
        
        # Create an empty list to store updated product names
        updated_product_names = []

        # Increment the stock of each low-stock product by 10
        for product in low_stock_products:
            product.stock += 10
            product.save()
            updated_product_names.append(product.name)

        return UpdateLowStockProducts(
            success_message="Successfully restocked products.",
            updated_products=updated_product_names
        )             


# CreateOrder Mutation
class CreateOrder(graphene.Mutation):
    class Arguments:
        customer_id = graphene.ID(required=True)
        product_ids = graphene.List(graphene.ID, required=True)
        order_date = graphene.DateTime()

    order = graphene.Field(OrderType)
    success = graphene.Boolean()
    message = graphene.String()

    def mutate(self, info, customer_id, product_ids, order_date=None):
        # Validate at least one product is selected
        if not product_ids or len(product_ids) == 0:
            return CreateOrder(
                order=None,
                success=False,
                message="At least one product must be selected"
            )

        # Validate customer exists
        try:
            customer = Customer.objects.get(pk=customer_id)
        except Customer.DoesNotExist:
            return CreateOrder(
                order=None,
                success=False,
                message=f"Customer with ID {customer_id} does not exist"
            )

        # Validate all products exist and calculate total
        total_amount = Decimal('0.00')
        products = []
        
        for product_id in product_ids:
            try:
                product = Product.objects.get(pk=product_id)
                products.append(product)
                total_amount += product.price
            except Product.DoesNotExist:
                return CreateOrder(
                    order=None,
                    success=False,
                    message=f"Invalid product ID: {product_id}"
                )

        # Create order in transaction
        try:
            with transaction.atomic():
                order = Order.objects.create(
                    customer=customer,
                    total_amount=total_amount,
                    order_date=order_date
                )
                # Associate products with order
                order.products.set(products)
                
            return CreateOrder(
                order=order,
                success=True,
                message="Order created successfully"
            )
        except Exception as e:
            return CreateOrder(
                order=None,
                success=False,
                message=f"Error creating order: {str(e)}"
            )


# Define Mutation class
class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()
    low_stock_update = UpdateLowStockProducts.Field()


# Define Query class with filtering support
class Query(graphene.ObjectType):
    # Use DjangoFilterConnectionField for relay-style filtering
    all_customers = DjangoFilterConnectionField(
        CustomerType,
        orderBy=graphene.List(graphene.String)
    )
    all_products = DjangoFilterConnectionField(
        ProductType,
        orderBy=graphene.List(graphene.String)
    )
    all_orders = DjangoFilterConnectionField(
        OrderType,
        orderBy=graphene.List(graphene.String)
    )
    
    # Single object queries
    customer = graphene.relay.Node.Field(CustomerType)
    product = graphene.relay.Node.Field(ProductType)
    order = graphene.relay.Node.Field(OrderType)

    def resolve_all_customers(self, info, **kwargs):
        """
        Resolve all customers with optional filtering and ordering.
        """
        order_by = kwargs.get('orderBy', None)
        queryset = Customer.objects.all()
        
        if order_by:
            queryset = queryset.order_by(*order_by)
        
        return queryset

    def resolve_all_products(self, info, **kwargs):
        """
        Resolve all products with optional filtering and ordering.
        """
        order_by = kwargs.get('orderBy', None)
        queryset = Product.objects.all()
        
        if order_by:
            queryset = queryset.order_by(*order_by)
        
        return queryset

    def resolve_all_orders(self, info, **kwargs):
        """
        Resolve all orders with optional filtering and ordering.
        """
        order_by = kwargs.get('orderBy', None)
        queryset = Order.objects.all().select_related('customer').prefetch_related('products')
        
        if order_by:
            queryset = queryset.order_by(*order_by)
        
        return queryset


# Create schema
schema = graphene.Schema(query=Query, mutation=Mutation)