import os
import json
from fastmcp import FastMCP
from implementation.db import SQLiteAdapter, ValidationError

# Create the server object.
mcp = FastMCP("SQLite Lab MCP Server")

# Configure database path relative to this script
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "students.db")
adapter = SQLiteAdapter(DB_PATH)

@mcp.tool(name="search")
def search(
    table: str,
    filters: dict = None,
    columns: list[str] = None,
    limit: int = 20,
    offset: int = 0,
    order_by: str = None,
    descending: bool = False
) -> str:
    """
    Search records in the specified table with options for filtering, sorting, and pagination.
    
    Args:
        table: Name of the table to query.
        filters: Optional dict of query filters, e.g. {"cohort": "A1"} or {"score": {"operator": ">=", "value": 80}}.
        columns: Optional list of columns to return. Returns all columns if omitted.
        limit: Maximum number of rows to return (default: 20).
        offset: Number of rows to skip (default: 0).
        order_by: Optional column name to sort by.
        descending: Set to True to sort in descending order (default: False).
    """
    try:
        results = adapter.search(
            table=table,
            columns=columns,
            filters=filters,
            limit=limit,
            offset=offset,
            order_by=order_by,
            descending=descending
        )
        return json.dumps(results, indent=2)
    except ValidationError as e:
        return f"Validation Error: {str(e)}"
    except Exception as e:
        return f"Unexpected Error: {str(e)}"

@mcp.tool(name="insert")
def insert(table: str, values: dict) -> str:
    """
    Insert a new row into the specified table and return the inserted record.
    
    Args:
        table: Name of the table to insert into.
        values: Dictionary of column-value pairs representing the new record.
    """
    try:
        inserted = adapter.insert(table=table, values=values)
        return json.dumps(inserted, indent=2)
    except ValidationError as e:
        return f"Validation Error: {str(e)}"
    except Exception as e:
        return f"Unexpected Error: {str(e)}"

@mcp.tool(name="aggregate")
def aggregate(
    table: str,
    metric: str,
    column: str = None,
    filters: dict = None,
    group_by: str = None
) -> str:
    """
    Perform aggregate operations (COUNT, AVG, SUM, MIN, MAX) on the database.
    
    Args:
        table: Name of the table to aggregate from.
        metric: The aggregate function to use (count, avg, sum, min, max).
        column: The column to aggregate. Required for all metrics except count.
        filters: Optional dict of filters to apply before aggregating.
        group_by: Optional column name to group the aggregated results by.
    """
    try:
        results = adapter.aggregate(
            table=table,
            metric=metric,
            column=column,
            filters=filters,
            group_by=group_by
        )
        return json.dumps(results, indent=2)
    except ValidationError as e:
        return f"Validation Error: {str(e)}"
    except Exception as e:
        return f"Unexpected Error: {str(e)}"

@mcp.resource("schema://database")
def database_schema() -> str:
    """
    Retrieve the complete schema of the database, listing all tables and column details.
    """
    try:
        schema = {}
        tables = adapter.list_tables()
        for table in tables:
            schema[table] = adapter.get_table_schema(table)
        return json.dumps(schema, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)}, indent=2)

@mcp.resource("schema://table/{table_name}")
def table_schema(table_name: str) -> str:
    """
    Retrieve the detailed column schema for a specific table.
    
    Args:
        table_name: Name of the table to inspect.
    """
    try:
        schema = adapter.get_table_schema(table_name)
        return json.dumps(schema, indent=2)
    except ValidationError as e:
        return json.dumps({"error": f"Validation Error: {str(e)}"}, indent=2)
    except Exception as e:
        return json.dumps({"error": f"Unexpected Error: {str(e)}"}, indent=2)

if __name__ == "__main__":
    # Runs the MCP server in stdio mode by default.
    mcp.run()
