import datetime
from gql import gql, Client
from gql.transport.requests import RequestsHTTPTransport

def log_crm_heartbeat():
    """Logs a heartbeat entry with timestamp to /tmp/crm_heartbeat_log.txt."""
    HEARTBEAT_LOG = "/tmp/crm_heartbeat_log.txt"
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(HEARTBEAT_LOG, "a") as f:
        f.write(f"{now} - CRM heartbeat\n")

def update_low_stock():
    log_path = "/tmp/low_stock_updates_log.txt"
    timestamp = datetime.datetime.now().strftime("%d/%m/%Y-%H:%M:%S")

    transport = RequestsHTTPTransport(
        url="http://localhost:8000/graphql",
        verify=True,
        retries=3,
    )
    client = Client(transport=transport, fetch_schema_from_transport=False)

    mutation = gql("""
        mutation {
            updateLowStockProducts {
                message
                updatedProducts {
                    name
                    stock
                }
            }
        }
    """)

    try:
        result = client.execute(mutation)
        message = result["updateLowStockProducts"]["message"]
        updated = result["updateLowStockProducts"]["updatedProducts"]

        with open(log_path, "a") as f:
            f.write(f"[{timestamp}] {message}\n")
            for p in updated:
                f.write(f"    - {p['name']}: stock={p['stock']}\n")

    except Exception as e:
        with open(log_path, "a") as f:
            f.write(f"[{timestamp}] ERROR running update_low_stock: {e}\n")