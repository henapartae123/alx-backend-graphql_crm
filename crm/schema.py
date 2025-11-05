import graphene
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from decimal import Decimal
import re
from .models import Customer, Order
from .filters import CustomerFilter, ProductFilter, OrderFilter
from crm.models import Product


# Object Types with Node interface for filtering
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


# Input Types
class CustomerInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    email = graphene.String(required=True)
    phone = graphene.String()


class ProductInput(graphene.InputObjectType):
    name = graphene.String(required=True)
    price = graphene.Decimal(required=True)
    stock = graphene.Int(default_value=0)


class OrderInput(graphene.InputObjectType):
    customer_id = graphene.ID(required=True)
    product_ids = graphene.List(graphene.ID, required=True)
    order_date = graphene.DateTime()


# Helper function for phone validation
def validate_phone(phone):
    if phone:
        pattern = r'^\+?\d{1,4}[-.\s]?\(?\d{1,3}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,4}[-.\s]?\d{1,9}$'
        if not re.match(pattern, phone):
            raise ValidationError("Invalid phone format")
    return phone


# Mutations
class CreateCustomer(graphene.Mutation):
    class Arguments:
        input = CustomerInput(required=True)

    customer = graphene.Field(CustomerType)
    message = graphene.String()

    def mutate(self, info, input):
        try:
            validate_email(input.email)
            if Customer.objects.filter(email=input.email).exists():
                raise ValidationError("Email already exists")
            validate_phone(input.phone)

            customer = Customer(
                name=input.name,
                email=input.email,
                phone=input.phone or ''
            )
            customer.save()

            return CreateCustomer(customer=customer, message="Customer created successfully")
        except ValidationError as e:
            raise Exception(str(e))


class BulkCreateCustomers(graphene.Mutation):
    class Arguments:
        input = graphene.List(CustomerInput, required=True)

    customers = graphene.List(CustomerType)
    errors = graphene.List(graphene.String)

    def mutate(self, info, input):
        created_customers = []
        errors = []

        with transaction.atomic():
            for idx, customer_data in enumerate(input):
                try:
                    validate_email(customer_data.email)
                    if Customer.objects.filter(email=customer_data.email).exists():
                        errors.append(f"Customer {idx}: Email already exists - {customer_data.email}")
                        continue
                    validate_phone(customer_data.phone)

                    customer = Customer(
                        name=customer_data.name,
                        email=customer_data.email,
                        phone=customer_data.phone or ''
                    )
                    customer.save()
                    created_customers.append(customer)
                except ValidationError as e:
                    errors.append(f"Customer {idx}: {str(e)}")
                except Exception as e:
                    errors.append(f"Customer {idx}: {str(e)}")

        return BulkCreateCustomers(customers=created_customers, errors=errors)


class CreateProduct(graphene.Mutation):
    class Arguments:
        input = ProductInput(required=True)

    product = graphene.Field(ProductType)

    def mutate(self, info, input):
        try:
            if input.price <= 0:
                raise ValidationError("Price must be positive")
            if input.stock < 0:
                raise ValidationError("Stock cannot be negative")

            product = Product(
                name=input.name,
                price=input.price,
                stock=input.stock
            )
            product.save()

            return CreateProduct(product=product)
        except ValidationError as e:
            raise Exception(str(e))


class CreateOrder(graphene.Mutation):
    class Arguments:
        input = OrderInput(required=True)

    order = graphene.Field(OrderType)

    def mutate(self, info, input):
        try:
            try:
                customer = Customer.objects.get(pk=input.customer_id)
            except Customer.DoesNotExist:
                raise ValidationError("Invalid customer ID")

            if not input.product_ids:
                raise ValidationError("At least one product is required")

            products = []
            total_amount = Decimal('0.00')

            for product_id in input.product_ids:
                try:
                    product = Product.objects.get(pk=product_id)
                    products.append(product)
                    total_amount += product.price
                except Product.DoesNotExist:
                    raise ValidationError(f"Invalid product ID: {product_id}")

            order = Order(
                customer=customer,
                order_date=input.order_date,
                total_amount=total_amount
            )
            order.save()
            order.products.set(products)

            return CreateOrder(order=order)
        except ValidationError as e:
            raise Exception(str(e))


class UpdateLowStockProducts(graphene.Mutation):
    products = graphene.List(ProductType)
    message = graphene.String()

    @transaction.atomic
    def mutate(self, info):
        # 1. Find products with stock < 10
        low_stock_ids = list(Product.objects.filter(stock__lt=10).values_list('id', flat=True))

        if not low_stock_ids:
            return UpdateLowStockProducts(products=[], message="No products required restocking.")

        # 2. Atomically increment stock by 10 using F() expression
        Product.objects.filter(id__in=low_stock_ids).update(stock=F('stock') + 10)

        # 3. Fetch the newly updated products to return them
        updated_products = Product.objects.filter(id__in=low_stock_ids)
        message = f"Successfully restocked {len(updated_products)} product(s)."

        return UpdateLowStockProducts(products=updated_products, message=message)

# Query with filtering support
class Query(graphene.ObjectType):
    all_customers = DjangoFilterConnectionField(CustomerType, order_by=graphene.String())
    all_products = DjangoFilterConnectionField(ProductType, order_by=graphene.String())
    all_orders = DjangoFilterConnectionField(OrderType, order_by=graphene.String())

    def resolve_all_customers(self, info, order_by=None, **kwargs):
        qs = Customer.objects.all()
        if order_by:
            qs = qs.order_by(order_by)
        return qs

    def resolve_all_products(self, info, order_by=None, **kwargs):
        qs = Product.objects.all()
        if order_by:
            qs = qs.order_by(order_by)
        return qs

    def resolve_all_orders(self, info, order_by=None, **kwargs):
        qs = Order.objects.all()
        if order_by:
            qs = qs.order_by(order_by)
        return qs


# Mutation
class Mutation(graphene.ObjectType):
    create_customer = CreateCustomer.Field()
    bulk_create_customers = BulkCreateCustomers.Field()
    create_product = CreateProduct.Field()
    create_order = CreateOrder.Field()
    update_low_stock_products = UpdateLowStockProducts.Field()