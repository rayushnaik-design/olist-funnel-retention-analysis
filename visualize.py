import mysql.connector
import pandas as pd
import matplotlib.pyplot as plt
from config import DB_PASSWORD

conn = mysql.connector.connect(
    host="localhost",
    user="root",
    password=DB_PASSWORD,
    database="olist_ecommerce"
)

# --- Query 1: Funnel by order status ---
query1 = """
SELECT order_status, COUNT(*) AS num_orders
FROM orders
GROUP BY order_status
ORDER BY num_orders DESC;
"""
df_funnel = pd.read_sql(query1, conn)

# --- Query 2: Delivery experience vs repeat rate ---
query2 = """
SELECT 
    delivery_experience,
    COUNT(*) AS num_customers,
    SUM(repeat_flag) AS repeat_customers,
    ROUND(SUM(repeat_flag) * 100.0 / COUNT(*), 2) AS repeat_rate_pct
FROM (
    SELECT 
        c.customer_unique_id,
        CASE 
            WHEN o.order_delivered_customer_date <= o.order_estimated_delivery_date THEN 'On time or early'
            ELSE 'Late'
        END AS delivery_experience,
        ROW_NUMBER() OVER (PARTITION BY c.customer_unique_id ORDER BY o.order_purchase_timestamp ASC) AS order_rank
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    WHERE o.order_status = 'delivered' 
        AND o.order_delivered_customer_date IS NOT NULL
) first_orders
JOIN (
    SELECT 
        c.customer_unique_id,
        CASE WHEN COUNT(o.order_id) > 1 THEN 1 ELSE 0 END AS repeat_flag
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    GROUP BY c.customer_unique_id
) repeat_lookup ON first_orders.customer_unique_id = repeat_lookup.customer_unique_id
WHERE first_orders.order_rank = 1
GROUP BY delivery_experience;
"""
df_delivery = pd.read_sql(query2, conn)

# --- Query 3: Category vs repeat rate ---
query3 = """
SELECT 
    p.product_category_name,
    COUNT(DISTINCT first_orders.customer_unique_id) AS num_customers,
    SUM(repeat_lookup.repeat_flag) AS repeat_customers,
    ROUND(SUM(repeat_lookup.repeat_flag) * 100.0 / COUNT(DISTINCT first_orders.customer_unique_id), 2) AS repeat_rate_pct
FROM (
    SELECT 
        c.customer_unique_id,
        o.order_id,
        ROW_NUMBER() OVER (PARTITION BY c.customer_unique_id ORDER BY o.order_purchase_timestamp ASC) AS order_rank
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    WHERE o.order_status = 'delivered'
) first_orders
JOIN order_items oi ON first_orders.order_id = oi.order_id
JOIN (
    SELECT 
        c.customer_unique_id,
        CASE WHEN COUNT(o.order_id) > 1 THEN 1 ELSE 0 END AS repeat_flag
    FROM orders o
    JOIN customers c ON o.customer_id = c.customer_id
    GROUP BY c.customer_unique_id
) repeat_lookup ON first_orders.customer_unique_id = repeat_lookup.customer_unique_id
JOIN products p ON oi.product_id = p.product_id
WHERE first_orders.order_rank = 1
GROUP BY p.product_category_name
HAVING num_customers >= 100
ORDER BY repeat_rate_pct DESC
LIMIT 15;
"""
df_category = pd.read_sql(query3, conn)

conn.close()

# --- Chart 1: Funnel ---
plt.figure(figsize=(8,5))
plt.bar(df_funnel['order_status'], df_funnel['num_orders'], color='steelblue')
plt.title('Order Status Funnel')
plt.xlabel('Order Status')
plt.ylabel('Number of Orders')
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('funnel_chart.png')

# --- Chart 2: Delivery experience vs repeat rate ---
plt.figure(figsize=(6,5))
plt.bar(df_delivery['delivery_experience'], df_delivery['repeat_rate_pct'], color=['seagreen', 'indianred'])
plt.title('Repeat Purchase Rate by First-Order Delivery Experience')
plt.xlabel('Delivery Experience')
plt.ylabel('Repeat Rate (%)')
plt.tight_layout()
plt.savefig('delivery_repeat_chart.png')

# --- Chart 3: Category vs repeat rate ---
plt.figure(figsize=(10,6))
plt.barh(df_category['product_category_name'], df_category['repeat_rate_pct'], color='darkorange')
plt.title('Repeat Purchase Rate by Product Category (Top 15)')
plt.xlabel('Repeat Rate (%)')
plt.ylabel('Product Category')
plt.gca().invert_yaxis()
plt.tight_layout()
plt.savefig('category_repeat_chart.png')

plt.show()
print("Charts saved as funnel_chart.png, delivery_repeat_chart.png, and category_repeat_chart.png")