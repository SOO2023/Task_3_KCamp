import pandas as pd

# database for task 3
product_db = pd.read_csv("products_db_csv.csv")

# stock database for task 5
stock_db = {
    1: {"item": "product1", "quantity": 12, "available": "yes"},
    2: {"item": "product2", "quantity": 3, "available": "no"},
    3: {"item": "product3", "quantity": 42, "available": "yes"},
    4: {"item": "product4", "quantity": 1, "available": "yes"},
    5: {"item": "product5", "quantity": 5, "available": "yes"},
    6: {"item": "product6", "quantity": 6, "available": "yes"},
    7: {"item": "product7", "quantity": 8, "available": "yes"},
    8: {"item": "product8", "quantity": 19, "available": "no"},
    9: {"item": "product9", "quantity": 20, "available": "yes"},
    10: {"item": "product10", "quantity": 10, "available": "yes"},
}
