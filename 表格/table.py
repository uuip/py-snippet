from rich.box import ASCII
from rich.console import Console
from rich.table import Table

console = Console(width=200)
table = Table(show_header=True, box=ASCII)
for x in d[0].keys():
    table.add_column(x, min_width=len(x), max_width=16)
for x in d:
    table.add_row(*map(str, x.values()))


from prettytable import PrettyTable

table = PrettyTable()
table.field_names = d[0].keys()
table.add_rows(d.values_list())
table.max_width = 16
table.max_table_width = 200
print(table)
