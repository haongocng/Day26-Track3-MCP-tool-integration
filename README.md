**Họ tên: Nguyễn Ngọc Hảo**
**Mã học viên: 2A202600903**

# SQLite Database MCP Server with FastMCP

This project implements a fully-featured, production-ready Model Context Protocol (MCP) server that exposes a SQLite database to LLM clients (such as Claude Code, Gemini CLI, etc.). 

The server provides tools for searching, inserting, and aggregating data, alongside resources exposing the database schema, all protected by a robust whitelist-based validation layer to prevent SQL Injection.

---

## 📂 Project Structure

```text
Day26-Track3-MCP-tool-integration/
├── .mcp.json                       # Local Claude Code integration configuration
├── README.md                       # Setup and API documentation (this file)
├── REPORT.md                       # Comprehensive lab report and design summary
├── implementation/
│   ├── db.py                       # SQLiteAdapter with SQL injection defense
│   ├── init_db.py                  # Database initialization and seeding script
│   ├── mcp_server.py               # FastMCP server wrapping the database adapter
│   ├── verify_server.py            # Automated unit tests for all tools & resources
│   └── students.db                 # Initialized SQLite database file (generated)
└── venv/                           # Python virtual environment (local dependencies)
```

---

## 🚀 Setup & Installation Instructions

Follow these steps to set up the environment and run the MCP server locally:

### 1. Initialize Virtual Environment & Activate
Create and activate a virtual environment if not already done:
```bash
# Windows PowerShell
python -m venv venv
venv\Scripts\Activate.ps1

# Linux / macOS
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies
Install the required FastMCP framework:
```bash
pip install fastmcp
```

### 3. Initialize the Database
Run the database initialization script to create the tables (`students`, `courses`, `enrollments`) and populate them with seed data:
```bash
python implementation/init_db.py
```
This generates the SQLite database file at `implementation/students.db`.

---

## 🛠️ API & Tool Descriptions

The MCP Server exposes the following tools to the LLM client:

### 1. `search`
Search records in a specific table with support for projected columns, complex filtering, ordering, and pagination.
* **Arguments**:
  * `table` (`str`, Required): The table name (e.g., `"students"`).
  * `filters` (`dict`, Optional): Dictionary of conditions, e.g., `{"cohort": "A1"}` or `{"score": {"operator": ">=", "value": 80}}`.
  * `columns` (`list[str]`, Optional): List of specific columns to retrieve.
  * `limit` (`int`, Optional, Default: `20`): Maximum number of rows to return.
  * `offset` (`int`, Optional, Default: `0`): Pagination offset.
  * `order_by` (`str`, Optional): Column to sort results by.
  * `descending` (`bool`, Optional, Default: `False`): Sort descending.

### 2. `insert`
Insert a new record into a table and return the fully populated record including auto-generated primary key.
* **Arguments**:
  * `table` (`str`, Required): The table name (e.g., `"courses"`).
  * `values` (`dict`, Required): Column-value pairs to insert (e.g., `{"title": "Chemistry"}`).

### 3. `aggregate`
Perform statistical aggregation queries on a table.
* **Arguments**:
  * `table` (`str`, Required): The table name (e.g., `"enrollments"`).
  * `metric` (`str`, Required): The function to use (`"count"`, `"avg"`, `"sum"`, `"min"`, `"max"`).
  * `column` (`str`, Optional): Column name to run the metric on (required for all except `"count"`).
  * `filters` (`dict`, Optional): Filtering constraints.
  * `group_by` (`str`, Optional): Column to group results by (e.g., `"cohort"`).

---

## 📄 Database Resources

LLM clients can read these resources to understand the schema structure before executing queries:

### 1. Full Database Schema (Static)
* **URI**: `schema://database`
* **Response**: A JSON structure detailing all tables and their column definitions.

### 2. Single Table Schema (Dynamic Template)
* **URI**: `schema://table/{table_name}`
* **Response**: Schema details for only the specified table.

---

## 🔒 Security & Validation Details

The server features a **Zero SQL Injection Policy** by validating all dynamic components:
* **Table names, column names, sort variables, and grouping parameters** are checked against a runtime whitelist fetched from SQLite metadata (`sqlite_master` and `PRAGMA table_info`).
* **Comparison operators** in filters are restricted to: `=`, `!=`, `<`, `<=`, `>`, `>=`, `LIKE`, and `IN`.
* **Parameterization** (`?` placeholders) is used for all filter values, pagination limits, offsets, and insert payloads.
* Any schema mismatch or empty insertion payload immediately triggers a custom `ValidationError`, which is gracefully returned to the LLM client.

---

## 🧪 Verification & Testing Steps

### 1. Run Automated Unit Tests
To verify all operations (normal execution, parameter filtering, aggregates, and resource reads) execute the unit test script:
```bash
python implementation/verify_server.py
```
Output should indicate `OK` with all 8 tests passing.

### 2. Run Security Tests
To verify the SQL Injection defense mechanism:
```bash
# Executing the security verification scratch script
python -c "from implementation.db import SQLiteAdapter; adapter = SQLiteAdapter('implementation/students.db'); print(adapter.list_tables())"
```
Or run the dedicated `test_security.py` script:
```bash
python C:\Users\haong\.gemini\antigravity\brain\a1dc7455-345d-47e8-894a-ce3dc1458663\scratch\test_security.py
```

### 3. Test with MCP Inspector
Start the official MCP Inspector to interact with the server visually:
```bash
npx -y @modelcontextprotocol/inspector venv/Scripts/python.exe implementation/mcp_server.py
```
Open the URL printed in the console (usually `http://localhost:5173` or similar) to view tools and resources.

---

## 🔌 LLM Client Integration Examples

### 1. Claude Code
Create a `.mcp.json` file in the root of your project directory:
```json
{
  "mcpServers": {
    "sqlite-lab": {
      "type": "stdio",
      "command": "D:\\Vin\\Day26-Track3-MCP-tool-integration\\venv\\Scripts\\python.exe",
      "args": [
        "D:\\Vin\\Day26-Track3-MCP-tool-integration\\implementation\\mcp_server.py"
      ],
      "env": {}
    }
  }
}
```
Run `claude` from the root directory to automatically load the server. You can ask queries like:
> "Use the sqlite-lab MCP server to list all students in cohort A1"

### 2. Gemini CLI
Add the server using the `gemini mcp` utility:
```bash
gemini mcp add sqlite-lab D:\Vin\Day26-Track3-MCP-tool-integration\venv\Scripts\python.exe D:\Vin\Day26-Track3-MCP-tool-integration\implementation\mcp_server.py --description "SQLite lab FastMCP server" --timeout 10000
```
Verify status:
```bash
gemini mcp list
```
Run queries:
```bash
gemini --allowed-mcp-server-names sqlite-lab --yolo -p "Show the database schema and find the top 2 students by score."
```