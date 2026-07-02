import os
import sqlite3

class ValidationError(Exception):
    """Raised when a request cannot be safely executed due to validation or safety issues."""
    pass

class SQLiteAdapter:
    """
    Adapter để tương tác với cơ sở dữ liệu SQLite:
    - Bật row_factory để trả về kết quả dạng dict/row.
    - Kiểm soát và xác thực nghiêm ngặt tên bảng, cột và toán tử để tránh SQL Injection.
    - Triển khai các phương thức: list_tables, get_table_schema, search, insert, và aggregate.
    """

    def __init__(self, db_path):
        self.db_path = db_path

    def connect(self):
        """Mở kết nối tới cơ sở dữ liệu SQLite với row_factory và bật khóa ngoại."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        # Bật ràng buộc khóa ngoại (Foreign Key Constraints)
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def list_tables(self):
        """Trả về danh sách các bảng người dùng định nghĩa, loại bỏ bảng hệ thống."""
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
            return [row["name"] for row in cursor.fetchall()]

    def get_table_schema(self, table):
        """Truy vấn PRAGMA table_info để lấy schema của một bảng cụ thể."""
        # 1. Xác thực tên bảng (whitelist)
        tables = self.list_tables()
        if table not in tables:
            raise ValidationError(f"Table '{table}' does not exist in the database.")

        # 2. Truy vấn schema (khi bảng đã được xác thực an toàn)
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table});")
            rows = cursor.fetchall()
            return [
                {
                    "name": row["name"],
                    "type": row["type"],
                    "not_null": bool(row["notnull"]),
                    "primary_key": bool(row["pk"])
                }
                for row in rows
            ]

    def _get_table_columns(self, table):
        """Trả về tập hợp tên các cột của một bảng (phục vụ validation)."""
        schema = self.get_table_schema(table)
        return {col["name"] for col in schema}

    def search(self, table, columns=None, filters=None, limit=20, offset=0, order_by=None, descending=False):
        """
        Tìm kiếm dữ liệu trong bảng với các tham số bộ lọc, sắp xếp và phân trang.
        """
        # 1. Xác thực tên bảng
        if table not in self.list_tables():
            raise ValidationError(f"Table '{table}' does not exist.")

        table_cols = self._get_table_columns(table)

        # 2. Xác thực danh sách các cột cần lấy
        if columns:
            for col in columns:
                if col not in table_cols:
                    raise ValidationError(f"Column '{col}' does not exist in table '{table}'.")
            select_cols = ", ".join(columns)
        else:
            select_cols = "*"

        # 3. Xác thực và xây dựng mệnh đề ORDER BY
        order_sql = ""
        if order_by:
            if order_by not in table_cols:
                raise ValidationError(f"Column '{order_by}' is not valid for sorting in table '{table}'.")
            direction = "DESC" if descending else "ASC"
            order_sql = f"ORDER BY {order_by} {direction}"

        # 4. Xác thực và xây dựng mệnh đề WHERE (Filters)
        where_clauses = []
        params = []
        if filters:
            if not isinstance(filters, dict):
                raise ValidationError("Filters must be a dictionary.")

            for col, filter_def in filters.items():
                if col not in table_cols:
                    raise ValidationError(f"Filter column '{col}' does not exist in table '{table}'.")

                # Định dạng filter: {"cohort": "A1"} hoặc {"score": {"operator": ">=", "value": 80}}
                if isinstance(filter_def, dict) and "operator" in filter_def and "value" in filter_def:
                    op = str(filter_def["operator"]).lower()
                    val = filter_def["value"]
                else:
                    op = "="
                    val = filter_def

                allowed_ops = {"=", "!=", "<", "<=", ">", ">=", "like", "in"}
                if op not in allowed_ops:
                    raise ValidationError(f"Unsupported filter operator '{op}'.")

                if op == "in":
                    if not isinstance(val, (list, tuple)):
                        raise ValidationError("Value for 'in' operator must be a list or tuple.")
                    if not val:
                        where_clauses.append("1 = 0") # Danh sách rỗng thì không khớp dòng nào
                    else:
                        placeholders = ", ".join("?" for _ in val)
                        where_clauses.append(f"{col} IN ({placeholders})")
                        params.extend(val)
                else:
                    where_clauses.append(f"{col} {op.upper()} ?")
                    params.append(val)

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        # 5. Xây dựng phân trang (Limit, Offset)
        if not isinstance(limit, int) or limit < 0:
            raise ValidationError("Limit must be a non-negative integer.")
        if not isinstance(offset, int) or offset < 0:
            raise ValidationError("Offset must be a non-negative integer.")

        limit_sql = "LIMIT ?"
        params.append(limit)
        offset_sql = "OFFSET ?"
        params.append(offset)

        # 6. Thực thi truy vấn
        query = f"SELECT {select_cols} FROM {table} {where_sql} {order_sql} {limit_sql} {offset_sql};"
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def insert(self, table, values):
        """
        Chèn một bản ghi mới và trả về bản ghi vừa chèn (bao gồm cả ID tự tăng).
        """
        # 1. Xác thực tên bảng
        if table not in self.list_tables():
            raise ValidationError(f"Table '{table}' does not exist.")

        # 2. Kiểm tra dữ liệu rỗng
        if not values or not isinstance(values, dict):
            raise ValidationError("Values to insert must be a non-empty dictionary.")

        table_cols = self._get_table_columns(table)
        schema = self.get_table_schema(table)

        # 3. Xác thực cột dữ liệu chèn vào
        for col in values.keys():
            if col not in table_cols:
                raise ValidationError(f"Column '{col}' does not exist in table '{table}'.")

        # 4. Xây dựng và thực thi truy vấn INSERT
        cols = list(values.keys())
        placeholders = ", ".join("?" for _ in cols)
        cols_sql = ", ".join(cols)
        query = f"INSERT INTO {table} ({cols_sql}) VALUES ({placeholders});"

        with self.connect() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(query, list(values.values()))
                last_id = cursor.lastrowid
                conn.commit()
            except sqlite3.Error as e:
                conn.rollback()
                raise ValidationError(f"Database error during insert: {e}")

            # 5. Lấy lại bản ghi vừa chèn để trả về đầy đủ thông tin (bao gồm ID tự tăng)
            pk_cols = [c["name"] for c in schema if c["primary_key"]]
            if len(pk_cols) == 1:
                pk_col = pk_cols[0]
                lookup_val = values.get(pk_col, last_id)
                cursor.execute(f"SELECT * FROM {table} WHERE {pk_col} = ?;", (lookup_val,))
                inserted_row = cursor.fetchone()
                if inserted_row:
                    return dict(inserted_row)

            # Trường hợp khóa chính phức hợp hoặc không tìm thấy, trả lại values gốc
            return values

    def aggregate(self, table, metric, column=None, filters=None, group_by=None):
        """
        Thực hiện các thống kê COUNT, AVG, SUM, MIN, MAX trên cơ sở dữ liệu.
        """
        # 1. Xác thực tên bảng
        if table not in self.list_tables():
            raise ValidationError(f"Table '{table}' does not exist.")

        table_cols = self._get_table_columns(table)

        # 2. Xác thực hàm thống kê (metric)
        metric = metric.lower()
        allowed_metrics = {"count", "avg", "sum", "min", "max"}
        if metric not in allowed_metrics:
            raise ValidationError(f"Unsupported aggregate metric '{metric}'. Allowed: {list(allowed_metrics)}")

        # 3. Xác thực cột tham gia thống kê
        if column:
            if column not in table_cols:
                raise ValidationError(f"Column '{column}' does not exist in table '{table}'.")
            metric_expr = f"{metric.upper()}({column})"
        else:
            if metric != "count":
                raise ValidationError(f"Metric '{metric}' requires a column name.")
            metric_expr = "COUNT(*)"

        # 4. Xác thực mệnh đề GROUP BY
        if group_by:
            if group_by not in table_cols:
                raise ValidationError(f"Group by column '{group_by}' does not exist in table '{table}'.")
            select_expr = f"{group_by}, {metric_expr} AS value"
        else:
            select_expr = f"{metric_expr} AS value"

        # 5. Xác thực và xây dựng mệnh đề WHERE (Filters)
        where_clauses = []
        params = []
        if filters:
            if not isinstance(filters, dict):
                raise ValidationError("Filters must be a dictionary.")

            for col, filter_def in filters.items():
                if col not in table_cols:
                    raise ValidationError(f"Filter column '{col}' does not exist in table '{table}'.")

                if isinstance(filter_def, dict) and "operator" in filter_def and "value" in filter_def:
                    op = str(filter_def["operator"]).lower()
                    val = filter_def["value"]
                else:
                    op = "="
                    val = filter_def

                allowed_ops = {"=", "!=", "<", "<=", ">", ">=", "like", "in"}
                if op not in allowed_ops:
                    raise ValidationError(f"Unsupported filter operator '{op}'.")

                if op == "in":
                    if not isinstance(val, (list, tuple)):
                        raise ValidationError("Value for 'in' operator must be a list or tuple.")
                    if not val:
                        where_clauses.append("1 = 0")
                    else:
                        placeholders = ", ".join("?" for _ in val)
                        where_clauses.append(f"{col} IN ({placeholders})")
                        params.extend(val)
                else:
                    where_clauses.append(f"{col} {op.upper()} ?")
                    params.append(val)

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""
        group_sql = f"GROUP BY {group_by}" if group_by else ""

        # 6. Thực thi truy vấn
        query = f"SELECT {select_expr} FROM {table} {where_sql} {group_sql};"
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
