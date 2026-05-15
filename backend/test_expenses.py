from finance_engine import get_expenses


response = get_expenses(
    "USR-00050",
    days=200
)

print(response)