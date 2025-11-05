#!/usr/bin/env python3
import datetime
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

LOG_FILE = "/tmp/order_reminders_log.txt"
GRAPHQL_ENDPOINT = "http://localhost:8000/graphql"

def main():
    # Set up GraphQL client
    transport = RequestsHTTPTransport(url=GRAPHQL_ENDPOINT, verify=True, retries=3)
    client = Client(transport=transport, fetch_schema_from_transport=True)

    # Calculate date range (last 7 days)
    today = datetime.date.today()
    last_week = today - datetime.timedelta(days=7)

    # GraphQL query
    query = gql("""
        query GetRecentOrders($startDate: Date!) {
            orders(filter: { order_date_Gte: $startDate }) {
                id
                customer {
                    email
                }
                order_date
            }
        }
    """)

    # Execute query
    params = {"startDate": str(last_week)}
    result = client.execute(query, variable_values=params)

    # Log results
    with open(LOG_FILE, "a") as f:
        timestamp = datetime.datetime.now().isoformat()
        for order in result.get("orders", []):
            order_id = order.get("id")
            customer_email = order.get("customer", {}).get("email")
            f.write(f"[{timestamp}] Order ID: {order_id}, Email: {customer_email}\n")

    print("Order reminders processed!")

if __name__ == "__main__":
    main()
