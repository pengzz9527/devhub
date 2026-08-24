---
title: "📊 DuckDB 实战笔记｜2026-08-20：聚合函数进阶 — STRING_AGG、ARRAY_AGG、MAP_AGG 一行搞定复杂聚合"
description: "每天一个 DuckDB 实战技巧。今天教你用 DuckDB 的聚合函数 STRING_AGG、ARRAY_AGG、MAP_AGG，把多行数据合并成字符串、数组或 Map，告别繁琐的循环和拼接。"
date: 2026-08-20
tags: ["DuckDB", "聚合函数", "STRING_AGG", "ARRAY_AGG", "MAP_AGG", "SQL", "实战"]
categories: ["DuckDB 实战笔记"]
toc: false
---

# 📊 DuckDB 实战笔记 ｜ 2026-08-20

> **每天一个 DuckDB 实战技巧，让你立刻能用。**

---

## 🔥 今日话题：聚合函数进阶 — STRING_AGG、ARRAY_AGG、MAP_AGG 一行搞定复杂聚合

你有没有遇到过这种场景：

> 一份订单表，每个订单有多条商品记录。老板要一份「每个客户的订单商品列表」——一行一个客户，商品用逗号分隔。

传统做法是什么？写 Python 循环，按客户分组，拼接字符串，再合并回主表。代码十几行，性能还差。

或者更复杂的：你要统计每个用户的「访问过的所有页面」，不是逗号分隔，而是要去重、排序、保留为数组。

**用 DuckDB 的进阶聚合函数，这些操作一条 SQL 就能搞定。**

---

## 📋 场景：订单商品汇总

假设你有一张订单明细表 `order_items`：

```sql
CREATE TABLE order_items AS
SELECT * FROM (VALUES
    (1, 101, 'iPhone', 7999),
    (2, 101, '保护壳', 99),
    (3, 101, '屏幕膜', 49),
    (4, 102, 'MacBook', 12999),
    (5, 102, '鼠标', 299),
    (6, 103, 'iPad', 3799),
    (7, 103, 'Apple Pencil', 899),
    (8, 103, '保护壳', 99),
    (9, 104, 'AirPods', 1599)
) AS t(order_id, customer_id, product, price);
```

**需求：每个客户买了哪些商品？**

### 方案一：STRING_AGG — 合并成逗号分隔字符串

```sql
SELECT
    customer_id,
    STRING_AGG(product, ', ') AS products
FROM order_items
GROUP BY customer_id;
```

**结果：**

```
┌─────────────┬────────────────────────────────────┐
│ customer_id │             products               │
├─────────────┼────────────────────────────────────┤
│ 101         │ iPhone, 保护壳, 屏幕膜              │
│ 102         │ MacBook, 鼠标                       │
│ 103         │ iPad, Apple Pencil, 保护壳          │
│ 104         │ AirPods                            │
└─────────────┴────────────────────────────────────┘
```

**更高级的用法：** 按价格排序后拼接

```sql
SELECT
    customer_id,
    STRING_AGG(product, ', ' ORDER BY price DESC) AS top_products
FROM order_items
GROUP BY customer_id;
```

---

## 💡 核心技巧一：STRING_AGG 进阶用法

### 1. 自定义分隔符

```sql
-- 用分号分隔
SELECT STRING_AGG(product, '; ') FROM order_items;

-- 用换行符分隔（适合生成报告）
SELECT STRING_AGG(product, E'\n') FROM order_items;
```

### 2. 去重后拼接

```sql
SELECT
    customer_id,
    STRING_AGG(DISTINCT product, ', ') AS unique_products
FROM order_items
GROUP BY customer_id;
```

### 3. 拼接带格式的字符串

```sql
SELECT
    customer_id,
    STRING_AGG(product || '(' || price || '元)', ', ') AS products_detail
FROM order_items
GROUP BY customer_id;
```

**结果：**

```
┌─────────────┬──────────────────────────────────────────────┐
│ customer_id │                products_detail               │
├─────────────┼──────────────────────────────────────────────┤
│ 101         │ iPhone(7999元), 保护壳(99元), 屏幕膜(49元)    │
│ 102         │ MacBook(12999元), 鼠标(299元)                 │
│ 103         │ iPad(3799元), Apple Pencil(899元), 保护壳(99元)│
│ 104         │ AirPods(1599元)                               │
└─────────────┴──────────────────────────────────────────────┘
```

---

## 💡 核心技巧二：ARRAY_AGG — 合并成数组

```sql
SELECT
    customer_id,
    ARRAY_AGG(product) AS products_array,
    ARRAY_AGG(price) AS prices_array
FROM order_items
GROUP BY customer_id;
```

**结果：**

```
┌─────────────┬─────────────────────────────────┬───────────────────┐
│ customer_id │         products_array          │   prices_array    │
├─────────────┼─────────────────────────────────┼───────────────────┤
│ 101         │ [iPhone, 保护壳, 屏幕膜]         │ [7999, 99, 49]    │
│ 102         │ [MacBook, 鼠标]                  │ [12999, 299]      │
│ 103         │ [iPad, Apple Pencil, 保护壳]      │ [3799, 899, 99]   │
│ 104         │ [AirPods]                        │ [1599]            │
└─────────────┴─────────────────────────────────┴───────────────────┘
```

**数组操作：**

```sql
-- 获取数组长度（购买了多少种商品）
SELECT
    customer_id,
    ARRAY_AGG(product) AS products,
    ARRAY_LENGTH(ARRAY_AGG(product)) AS product_count
FROM order_items
GROUP BY customer_id;

-- 排序后聚合
SELECT
    customer_id,
    ARRAY_SORT(ARRAY_AGG(product)) AS sorted_products
FROM order_items
GROUP BY customer_id;

-- 去重后聚合
SELECT
    customer_id,
    ARRAY_DISTINCT(ARRAY_AGG(product)) AS unique_products
FROM order_items
GROUP BY customer_id;
```

---

## 💡 核心技巧三：MAP_AGG — 合并成键值对

```sql
SELECT
    customer_id,
    MAP_AGG(product, price) AS product_prices
FROM order_items
GROUP BY customer_id;
```

**结果：**

```
┌─────────────┬───────────────────────────────────────────────┐
│ customer_id │              product_prices                   │
├─────────────┼───────────────────────────────────────────────┤
│ 101         │ {iPhone -> 7999, 保护壳 -> 99, 屏幕膜 -> 49}   │
│ 102         │ {MacBook -> 12999, 鼠标 -> 299}               │
│ 103         │ {iPad -> 3799, Apple Pencil -> 899,...}       │
│ 104         │ {AirPods -> 1599}                              │
└─────────────┴───────────────────────────────────────────────┘
```

**MAP 的实际用途 — 找出每个客户最贵的商品：**

```sql
SELECT
    customer_id,
    product_prices,
    -- 用 UNNEST 展开 MAP，找出价格最高的
    (SELECT key FROM UNNEST(ARRAY_SORT(
        ARRAY_AGG(STRUCT_CONSTRUCT(key, value)),
        (a, b) -> b.value <=> a.value
    )) LIMIT 1).key AS most_expensive
FROM order_items
GROUP BY customer_id;
```

---

## 🚀 实战场景：生成 JSON 报告

结合 `STRING_AGG` 和 `ROW_TO_JSON`，生成结构化的 JSON 输出：

```sql
SELECT
    customer_id,
    ROW_TO_JSON(STRUCT(
        customer_id,
        STRING_AGG(product, ', ') AS products,
        ARRAY_AGG(price) AS prices,
        SUM(price) AS total_amount,
        COUNT(*) AS item_count
    )) AS report
FROM order_items
GROUP BY customer_id;
```

---

## 📋 场景二：用户标签聚合

```sql
CREATE TABLE user_tags AS
SELECT * FROM (VALUES
    (1, 'Alice', 'VIP'),
    (1, 'Alice', '高消费'),
    (1, 'Alice', '活跃用户'),
    (2, 'Bob', '新用户'),
    (2, 'Bob', '电子产品'),
    (3, 'Charlie', 'VIP'),
    (3, 'Charlie', '服装'),
    (3, 'Charlie', '高消费')
) AS t(user_id, name, tag);

-- 每个用户的标签列表
SELECT
    name,
    STRING_AGG(tag, '、') AS tags
FROM user_tags
GROUP BY name;
```

**结果：**

```
┌─────────┬──────────────────────────┐
│  name   │          tags            │
├─────────┼──────────────────────────┤
│ Alice   │ VIP、高消费、活跃用户       │
│ Bob     │ 新用户、电子产品            │
│ Charlie │ VIP、服装、高消费          │
└─────────┴──────────────────────────┘
```

---

## 📋 场景三：跨表聚合

```sql
CREATE TABLE orders AS
SELECT * FROM (VALUES
    (1, 101, DATE '2026-08-01'),
    (2, 101, DATE '2026-08-05'),
    (3, 102, DATE '2026-08-03'),
    (4, 103, DATE '2026-08-07')
) AS t(order_id, customer_id, order_date);

-- 聚合每个客户的订单日期和总金额
SELECT
    o.customer_id,
    STRING_AGG(DATE_FORMAT(o.order_date, '%m-%d'), ', ') AS order_dates,
    ARRAY_AGG(oi.price) AS prices,
    SUM(oi.price) AS total_spent
FROM orders o
JOIN order_items oi ON o.order_id = oi.order_id
GROUP BY o.customer_id;
```

---

## 🐍 在 Python 中使用

```python
import duckdb

con = duckdb.connect(":memory:")

# 创建示例数据
con.execute("""
CREATE TABLE order_items AS
SELECT * FROM (VALUES
    (1, 101, 'iPhone', 7999),
    (2, 101, '保护壳', 99),
    (3, 101, '屏幕膜', 49),
    (4, 102, 'MacBook', 12999),
    (5, 102, '鼠标', 299),
    (6, 103, 'iPad', 3799),
    (7, 103, 'Apple Pencil', 899),
    (8, 103, '保护壳', 99),
    (9, 104, 'AirPods', 1599)
) AS t(order_id, customer_id, product, price)
""")

# STRING_AGG：逗号分隔的商品列表
result = con.execute("""
SELECT
    customer_id,
    STRING_AGG(product, ', ') AS products
FROM order_items
GROUP BY customer_id
""").fetchdf()
print("STRING_AGG 结果:")
print(result)

# ARRAY_AGG：数组形式的商品列表
result2 = con.execute("""
SELECT
    customer_id,
    ARRAY_AGG(product) AS products_array,
    ARRAY_LENGTH(ARRAY_AGG(product)) AS count
FROM order_items
GROUP BY customer_id
""").fetchdf()
print("\nARRAY_AGG 结果:")
print(result2)

# MAP_AGG：商品-价格映射
result3 = con.execute("""
SELECT
    customer_id,
    MAP_AGG(product, price) AS product_prices
FROM order_items
GROUP BY customer_id
""").fetchdf()
print("\nMAP_AGG 结果:")
print(result3)
```

---

## 🧠 三种聚合函数对比

| 函数 | 输出类型 | 适用场景 | 后续处理 |
|------|---------|---------|---------|
| **STRING_AGG** | 字符串 | 生成报告、逗号分隔列表 | 可直接展示 |
| **ARRAY_AGG** | 数组 | 需要进一步数组操作 | UNNEST、数组函数 |
| **MAP_AGG** | Map | 键值对映射、配置聚合 | 键值查询、遍历 |

**选择建议：**
- 需要展示给用户看 → `STRING_AGG`
- 需要在代码里进一步处理 → `ARRAY_AGG`
- 需要键值对映射 → `MAP_AGG`

---

## 📝 小结

| 技能 | 一句话总结 |
|------|-----------|
| STRING_AGG | `STRING_AGG(col, ', ')` 把多行合并成字符串 |
| 排序拼接 | `STRING_AGG(col, ', ' ORDER BY col)` 按顺序拼接 |
| 去重拼接 | `STRING_AGG(DISTINCT col, ', ')` 先去重再拼接 |
| ARRAY_AGG | `ARRAY_AGG(col)` 把多行合并成数组 |
| MAP_AGG | `MAP_AGG(key, value)` 把多行合并成键值对 |
| 数组操作 | `ARRAY_LENGTH()`、`ARRAY_SORT()`、`ARRAY_DISTINCT()` |

**进阶聚合函数让你：一条 SQL 搞定以前需要写几十行循环才能完成的复杂聚合。**

---

## 💬 互动

你的项目里有没有「把多行数据合并成一行」的需求？把场景发出来，我们一起看看用哪种聚合函数最合适！

---

📌 收藏这条笔记，下次做数据汇总时直接回来参考。

---

🔍 想系统学习 DuckDB 实战技巧？duckdblab.org 上有完整教程系列，从基础查询到聚合函数高级用法，带你成为 DuckDB 实战专家。
