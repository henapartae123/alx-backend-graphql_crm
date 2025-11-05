#!/bin/bash
# Script to delete inactive customers (no orders in the past year)

# Define log file
LOG_FILE="/tmp/customer_cleanup_log.txt"

# Run Django shell command to delete inactive customers
DELETED_COUNT=$(python manage.py shell -c "
from django.utils import timezone
from datetime import timedelta
from crm.models import Customer

cutoff_date = timezone.now() - timedelta(days=365)
inactive_customers = Customer.objects.filter(orders__isnull=True) | Customer.objects.filter(last_order_date__lt=cutoff_date)
count = inactive_customers.count()
inactive_customers.delete()
print(count)
")

# Log result with timestamp
echo \"\$(date '+%Y-%m-%d %H:%M:%S') - Deleted \$DELETED_COUNT inactive customers\" >> \$LOG_FILE
