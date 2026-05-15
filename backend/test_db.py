import pandas as pd

from db import engine


query = """

SELECT *

FROM clientes

LIMIT 5

"""


df = pd.read_sql(

    query,

    engine
)

print(df)