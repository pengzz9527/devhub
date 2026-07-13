---
title: "📊 DuckDB 实战笔记｜2026-07-07：用 DuckDB 优雅地吃透 JSON 数据"
description: "每天一个 DuckDB 实战技巧。今天教你用 DuckDB 的 JSON 函数库，把嵌套 JSON 拍平、查询、聚合，全程 SQL 搞定。"
date: 2026-07-07
tags: ["DuckDB", "JSON", "数据解析", "SQL", "实战"]
categories: ["DuckDB 实战笔记"]
toc: false
---

# 📊 DuckDB 实战笔记 ｜ 2026-07-07

> **每天一个 DuckDB 实战技巧，让你立刻能用。**

---

## 🔥 今日话题：用 DuckDB 优雅地吃透 JSON 数据

你是否经历过这样的痛苦：

> API 返回了一堆嵌套 JSON，你要从中提取 `user.address.city` 和 `orders[].total`，然后在 Python 里写三层 `for` 循环遍历？

或者更惨——日志文件全是 JSON 格式，你要统计某个字段的分布，结果发现 `json.loads()` 之后数据结构参差不齐，有的有字段有的没有，程序直接崩掉。

**用 DuckDB，你不需要写任何 Python 解析逻辑。一条 SQL，直接对 JSON 文件做查询、聚合、关联。**

---

## 📋 场景：电商订单日志

假设你有一组订单日志文件 `orders.jsonl`（JSON Lines 格式，每行一个 JSON 对象）：

```jsonl
{"order_id": 1, "user": {"id": 101, "name": "Alice", "address": {"city": "Beijing", "zip": "100000"}}, "items": [{"product": "Laptop", "qty": 1, "price": 5999}, {"product": "Mouse", "qty": 2, "price": 89}], "total": 6177, "status": "completed"}
{"order_id": 2, "user": {"id": 102, "name": "Bob", "address": {"city": "Shanghai", "zip": "200000"}}, "items": [{"product": "Keyboard", "qty": 1, "price": 399}], "total": 399, "status": "completed"}
{"order_id": 3, "user": {"id": 101, "name": "Alice", "address": {"city": "Beijing", "zip": "100000"}}, "items": [{"product": "Monitor", "qty": 1, "price": 2499}], "total": 2499, "status": "pending"}
{"order_id": 4, "user": {"id": 103, "name": "Charlie", "address": {"city": "Guangzhou", "zip": "510000"}}, "items": [{"product": "Laptop", "qty": 1, "price": 5999}, {"product": "Keyboard", "qty": 1, "price": 399}, {"product": "Mouse", "qty": 3, "price": 89}], "total": 6666, "status": "completed"}
{"order_id": 5, "user": {"id": 104, "name": "Diana"}, "items": [{"product": "USB Cable", "qty": 5, "price": 19}], "total": 95, "status": "cancelled"}
```

注意第 5 条数据——`user` 对象里没有 `address` 字段。这就是真实世界的数据：结构不统一、字段缺失。

---

## 💡 第一步：直接读 JSON 文件

```sql
SELECT * FROM read_json_auto('orders.jsonl');
```

DuckDB 的 `read_json_auto()` 会自动检测文件格式、推断 schema。**不需要提前定义列结构。**

结果是一张关系表，嵌套字段变成了 `STRUCT` 类型，数组字段变成了 `LIST` 类型。

---

## 💡 第二步：提取嵌套字段

### 点号访问（Struct 字段）

```sql
SELECT
    order_id,
    user.name,                          -- 直接点号访问
    user.address.city,                  -- 深层嵌套也没问题
    total,
    status
FROM read_json_auto('orders.jsonl');
```

**结果：**

| order_id | name | city | total | status |
|----------|------|------|-------|--------|
| 1 | Alice | Beijing | 6177 | completed |
| 2 | Bob | Shanghai | 399 | completed |
| 3 | Alice | Beijing | 2499 | pending |
| 4 | Charlie | Guangzhou | 6666 | completed |
| 5 | Diana | NULL | 95 | cancelled |

**注意：** Diana 的地址返回 NULL——因为她的 JSON 里没有 `address` 字段。DuckDB 不会报错，而是优雅地返回 NULL。

### 安全访问：`->>` 运算符

如果你不确定字段是否存在，可以用 `->>` 运算符做安全提取：

```sql
SELECT
    order_id,
    user->>'name' AS name,
    user->>'address'->>'city' AS city
FROM read_json_auto('orders.jsonl');
```

`->>` 返回文本类型，如果路径不存在则返回 NULL 而不是报错。

---

## 💡 第三步：展开数组（Array Flattening）

订单中的 `items` 是一个数组。如果你想看**每个商品**的明细：

```sql
SELECT
    order_id,
    item.product,
    item.qty,
    item.price,
    item.qty * item.price AS line_total
FROM read_json_auto('orders.jsonl'),
     UNNEST(items) AS item;
```

**关键：`, UNNEST(items) AS item`** —— 这行代码把数组"炸开"成多行，类似 SQL Server 的 `CROSS APPLY` 或 PostgreSQL 的 `LATERAL`。

**结果：**

| order_id | product | qty | price | line_total |
|----------|---------|-----|-------|------------|
| 1 | Laptop | 1 | 5999 | 5999 |
| 1 | Mouse | 2 | 89 | 178 |
| 2 | Keyboard | 1 | 399 | 399 |
| 3 | Monitor | 1 | 2499 | 2499 |
| 4 | Laptop | 1 | 5999 | 5999 |
| 4 | Keyboard | 1 | 399 | 399 |
| 4 | Mouse | 3 | 89 | 267 |
| 5 | USB Cable | 5 | 19 | 95 |

**就这么一行 `, UNNEST(items)`，数组变多行。** 不需要 Python 的 `for` 循环。

---

## 💡 第四步：JSON 聚合——把行拍回 JSON

刚才我们"炸开"了数组。反过来，如果你想**按城市聚合订单**，并把订单详情打包成 JSON：

```sql
SELECT
    user.address.city AS city,
    COUNT(*) AS order_count,
    SUM(total) AS total_revenue,
    -- 把该城市的订单打包成 JSON 数组
    json_group_array(
        json_object(
            'order_id', order_id,
            'user', user.name,
            'total', total,
            'status', status
        )
    ) AS orders_json
FROM read_json_auto('orders.jsonl')
WHERE user.address.city IS NOT NULL  -- 过滤掉地址缺失的记录
GROUP BY user.address.city
ORDER BY total_revenue DESC;
```

**结果：**

| city | order_count | total_revenue | orders_json |
|------|-------------|---------------|-------------|
| Beijing | 2 | 8676 | `[{"order_id":1,...},{"order_id":3,...}]` |
| Guangzhou | 1 | 6666 | `[{"order_id":4,...}]` |
| Shanghai | 1 | 399 | `[{"order_id":2,...}]` |

`json_group_array()` + `json_object()` 可以把行数据重新组装成 JSON 结构。这在构建 API 响应时非常有用。

---

## 💡 第五步：解析任意 JSON 字符串

有时候 JSON 不是来自文件，而是存在某个表的字段里：

```sql
SELECT
    log_id,
    log_message,
    json_extract_string(log_data, '$.level') AS level,
    json_extract_string(log_data, '$.message') AS msg,
    json_extract(log_data, '$.meta.timestamp') AS ts
FROM (
    SELECT 1 AS log_id, 'System log' AS log_message,
        '{"level":"ERROR","message":"Connection timeout","meta":{"timestamp":"2026-07-07T10:00:00Z"}}' AS log_data
    UNION ALL
    SELECT 2, 'App log',
        '{"level":"INFO","message":"Request processed","meta":{"timestamp":"2026-07-07T10:01:00Z"}}'
);
```

**结果：**

| log_id | level | msg | ts |
|--------|-------|-----|----|
| 1 | ERROR | Connection timeout | 2026-07-07T10:00:00Z |
| 2 | INFO | Request processed | 2026-07-07T10:01:00Z |

关键函数：
- `json_extract_string(json, path)` — 提取字符串值
- `json_extract(json, path)` — 提取任意类型值（保持类型）
- `json_valid(json_string)` — 判断是否为合法 JSON

---

## 💡 第六步：实战——从混合 JSON 中提取结构化数据

真实场景中最头疼的是：同一个字段在不同记录中类型不同。比如 `total` 有时是数字，有时是字符串 `"free"`：

```sql
-- 创建含混合类型的测试数据
CREATE TABLE mixed_orders AS
SELECT * FROM (VALUES
    (1, 'Alice', 5999, 'completed'),
    (2, 'Bob', 'free', 'completed'),       -- total 是字符串
    (3, 'Charlie', 399, 'pending'),
    (4, 'Diana', NULL, 'cancelled')         -- total 是 NULL
) AS t(order_id, name, total, status);

-- 统一处理：转成数值，非数字变 0
SELECT
    order_id,
    name,
    TRY_CAST(total AS BIGINT) AS total_num,
    COALESCE(TRY_CAST(total AS BIGINT), 0) AS total_coalesced,
    status
FROM mixed_orders;
```

**结果：**

| order_id | name | total_num | total_coalesced | status |
|----------|------|-----------|-----------------|--------|
| 1 | Alice | 5999 | 5999 | completed |
| 2 | Bob | NULL | 0 | completed |
| 3 | Charlie | 399 | 399 | pending |
| 4 | Diana | NULL | 0 | cancelled |

`TRY_CAST` + `COALESCE` 的组合再次证明了它的价值。

---

## 🐍 在 Python 中使用

```python
import duckdb

# 方法 1：直接查询 JSON 文件
result = duckdb.sql("""
    SELECT
        order_id,
        user->>'name' AS name,
        user->>'address'->>'city' AS city,
        total,
        status
    FROM read_json_auto('orders.jsonl')
""").df()

# 方法 2：展开数组
items_detail = duckdb.sql("""
    SELECT
        order_id,
        item->>'product' AS product,
        (item->>'qty')::INTEGER AS qty,
        (item->>'price')::FLOAT AS price
    FROM read_json_auto('orders.jsonl'),
         UNNEST(items) AS item
""").df()

# 方法 3：从现有 DataFrame 中查询 JSON 列
import pandas as pd
df = pd.DataFrame({
    'id': [1, 2],
    'payload': ['{"score": 95}', '{"score": 87}']
})
duckdb.register("my_df", df)

result = duckdb.sql("""
    SELECT id,
           json_extract_string(payload, '$.score')::INTEGER AS score
    FROM my_df
""").df()
```

**核心优势：** 数据不需要先加载到 Python 里解析 JSON。DuckDB 直接在 SQL 层面处理，内存占用更低，速度更快。

---

## 🧠 JSON 函数速查表

| 操作 | 函数 | 示例 |
|------|------|------|
| 读取 JSON 文件 | `read_json_auto()` | `FROM read_json_auto('data.jsonl')` |
| 提取字符串值 | `json_extract_string(json, path)` | `json_extract_string(data, '$.name')` |
| 提取任意类型 | `json_extract(json, path)` | `json_extract(data, '$.count')` |
| 安全访问 | `->>` | `data->>'key'` |
| 判断是否合法 JSON | `json_valid()` | `WHERE json_valid(raw_json)` |
| 行转 JSON 对象 | `json_object(k1, v1, k2, v2)` | `json_object('name', col1, 'val', col2)` |
| 行数组转 JSON 数组 | `json_group_array()` | `json_group_array(json_object(...))` |
| 安全类型转换 | `TRY_CAST(val AS type)` | `TRY_CAST(json_col->>'num' AS INTEGER)` |

---

## 📝 小结

| 场景 | 传统做法 | DuckDB 做法 |
|------|---------|-------------|
| 解析 JSON 文件 | Python `json.load()` + 循环 | `read_json_auto()` 一行 |
| 提取嵌套字段 | 多层字典访问 `data['a']['b']` | `user->>'address'->>'city'` |
| 展开数组 | 嵌套 `for` 循环 | `, UNNEST(items) AS item` |
| 聚合为 JSON | 手动 `json.dumps()` | `json_group_array(json_object(...))` |
| 混合类型处理 | `try/except` + 条件判断 | `TRY_CAST()` + `COALESCE()` |

**DuckDB 的 JSON 处理能力让你：不需要写 Python 解析逻辑，直接在 SQL 里完成一切。**

---

## 💬 互动

你工作中最常遇到的 JSON 数据难题是什么？嵌套太深？字段不一致？数组展开？留言告诉我，下期针对性解答！

---

*📌 收藏这条笔记，下次处理 JSON 数据时直接回来参考。*

---

*© 2026 DuckDB 实战笔记 ｜ 每天进步一点点*
