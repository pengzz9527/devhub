---
title: "📊 DuckDB 实战笔记｜2026-06-29：PIVOT & UNPIVOT — 行列互转的终极方案"
description: "每天一个 DuckDB 实战技巧。今天教你用 PIVOT 和 UNPIVOT 轻松实现行列互转，告别繁琐的 CASE WHEN 和 Python 循环。"
date: 2026-06-29
tags: ["DuckDB", "PIVOT", "UNPIVOT", "行列转换", "SQL", "实战"]
categories: ["DuckDB 实战笔记"]
toc: false
---

# 📊 DuckDB 实战笔记 ｜ 2026-06-29

> **每天一个 DuckDB 实战技巧，让你立刻能用。**

---

## 🔥 今日话题：PIVOT & UNPIVOT — 行列互转不再头疼

做报表的人一定遇到过这个经典难题：

> "我需要一张表，横着是客户，竖着是产品，格子是销售额。"

或者反过来：

> "数据库给的是宽表，我需要拆成长表才能做透视分析。"

以前怎么做？一堆 `CASE WHEN` 拼来拼去，或者拉到 Python 里用 `pivot()` / `melt()` 折腾。

**今天教你用 DuckDB 的 PIVOT 和 UNPIVOT，一行 SQL 搞定行列互转。**

---

## 📋 场景：电商销售数据

假设你有一张订单表，每条记录是"客户买了什么产品花了多少钱"：

```sql
CREATE TABLE orders(customer VARCHAR, product VARCHAR, amount DOUBLE);
INSERT INTO orders VALUES
  ('Alice', 'Apple', 10.5),
  ('Alice', 'Banana', 5.0),
  ('Bob',   'Apple', 8.0),
  ('Bob',   'Cherry', 12.0),
  ('Carol', 'Banana', 6.5),
  ('Carol', 'Cherry', 15.0),
  ('Carol', 'Apple', 9.0);
```

现在老板要一份**按客户汇总各产品销售额**的报表——也就是要把 `product` 列变成横向的列名。

---

## 💡 PIVOT：长表 → 宽表

```sql
SELECT * FROM (
  SELECT customer, product, amount FROM orders
) PIVOT(
  SUM(amount)
  FOR product IN ('Apple', 'Banana', 'Cherry')
)
ORDER BY customer;
```

**结果：**

| customer | Apple | Banana | Cherry |
|----------|-------|--------|--------|
| Alice | 10.5 | 5.0 | NULL |
| Bob | 8.0 | NULL | 12.0 |
| Carol | 9.0 | 6.5 | 15.0 |

**就这么简单。** 不需要 `CASE WHEN`，不需要 `GROUP BY` 套子查询。

### PIVOT 语法拆解

```
PIVOT(
  聚合函数          ← 怎么合并重复行？SUM / COUNT / AVG / MAX...
  FOR 列名           ← 哪一列的值要变成列头？
  IN (具体值列表)    ← 这些值各自成为一列
)
```

几个关键点：
- **聚合函数**决定了同一行多个值怎么合并。`SUM` 求和、`COUNT` 计数、`AVG` 平均，随你选。
- **IN 列表**里的值就是最终的列名。如果数据里有列表之外的值，会被忽略（如果想保留，可以用 `USING MAP` 模式）。
- **没有匹配数据的格子**自动填 NULL。

### 进阶：不用写死列名

如果产品种类太多，手写 `IN (...)` 很痛苦。DuckDB 支持动态列：

```sql
-- 用子查询动态获取所有产品
SELECT * FROM (
  SELECT customer, product, amount FROM orders
) PIVOT(
  SUM(amount)
  FOR product IN (SELECT DISTINCT product FROM orders)
)
ORDER BY customer;
```

这样不管新增多少产品，SQL 都不用改。

### 进阶：用 MAP 模式保留所有列

当 `IN` 列表无法穷举所有值时，可以用 MAP 把所有未指定的列打包成一个 JSON：

```sql
SELECT * FROM (
  SELECT customer, product, amount FROM orders
) PIVOT(
  SUM(amount)
  FOR product IN ('Apple', 'Banana')
  USING MAP
)
ORDER BY customer;
```

结果会多出一列 `_other`，包含 `{'Cherry': 12.0}` 这样的映射。

---

## 💡 UNPIVOT：宽表 → 长表

反过来也很常见。比如有张月度报表：

| month | jan | feb | mar | apr |
|-------|-----|-----|-----|-----|
| sales | 100 | 150 | 120 | 200 |

你需要把它变成每行一个月的长表，方便后续分析。

```sql
CREATE TABLE monthly_sales(month VARCHAR, jan DOUBLE, feb DOUBLE, mar DOUBLE, apr DOUBLE);
INSERT INTO monthly_sales VALUES
  ('sales', 100, 150, 120, 200);
```

```sql
SELECT * FROM monthly_sales
UNPIVOT(amount FOR month IN (jan, feb, mar, apr));
```

**结果：**

| month | jan | amount |
|-------|-----|--------|
| sales | jan | 100 |
| sales | feb | 150 |
| sales | mar | 120 |
| sales | apr | 200 |

### UNPIVOT 语法拆解

```
UNPIVOT(
  值列名          ← 哪个列存原始值？
  FOR 新列名       ← 转成什么列名表示"原来的列名"？
  IN (列列表)      ← 哪些列要展开？
)
```

### 处理 NULL 值

默认情况下，UNPIVOT 会**自动排除 NULL 值**的行。如果你需要保留它们（比如区分"没数据"和"零"），可以先用 `COALESCE` 将 NULL 转为 0：

```sql
SELECT * FROM (
  SELECT month, COALESCE(jan, 0) AS jan, COALESCE(feb, 0) AS feb,
         COALESCE(mar, 0) AS mar, COALESCE(apr, 0) AS apr
  FROM monthly_sales
)
UNPIVOT(amount FOR month IN (jan, feb, mar, apr));
```

---

## 🚀 实战案例：客户消费画像

回到最初的订单表，做一个完整的客户消费分析：

```sql
-- Step 1: PIVOT 成宽表
WITH customer_matrix AS (
  SELECT * FROM (
    SELECT customer, product, amount FROM orders
  ) PIVOT(
    SUM(amount)
    FOR product IN ('Apple', 'Banana', 'Cherry')
  )
),
-- Step 2: 加总计算
enriched AS (
  SELECT
    customer,
    COALESCE(Apple, 0) AS apple_total,
    COALESCE(Banana, 0) AS banana_total,
    COALESCE(Cherry, 0) AS cherry_total,
    COALESCE(Apple, 0) + COALESCE(Banana, 0) + COALESCE(Cherry, 0) AS grand_total,
    -- 最爱产品
    CASE
      WHEN COALESCE(Apple, 0) >= COALESCE(Banana, 0)
           AND COALESCE(Apple, 0) >= COALESCE(Cherry, 0) THEN 'Apple'
      WHEN COALESCE(Banana, 0) >= COALESCE(Apple, 0)
           AND COALESCE(Banana, 0) >= COALESCE(Cherry, 0) THEN 'Banana'
      ELSE 'Cherry'
    END AS favorite_product
  FROM customer_matrix
)
SELECT * FROM enriched ORDER BY grand_total DESC;
```

**结果：**

| customer | apple_total | banana_total | cherry_total | grand_total | favorite_product |
|----------|-------------|--------------|--------------|-------------|------------------|
| Carol | 9.0 | 6.5 | 15.0 | 30.5 | Cherry |
| Alice | 10.5 | 5.0 | 0 | 15.5 | Apple |
| Bob | 8.0 | 0 | 12.0 | 20.0 | Cherry |

**一张 SQL，完成了：行列转换 → 汇总 → 特征提取，全部在数据库内完成。**

---

## 🐍 在 Python 中使用

```python
import duckdb

# 连接 DuckDB
con = duckdb.connect()

# 创建示例数据
con.execute("""
CREATE TABLE orders AS SELECT * FROM (VALUES
  ('Alice', 'Apple', 10.5),
  ('Alice', 'Banana', 5.0),
  ('Bob',   'Apple', 8.0),
  ('Bob',   'Cherry', 12.0),
  ('Carol', 'Banana', 6.5),
  ('Carol', 'Cherry', 15.0),
  ('Carol', 'Apple', 9.0)
) AS t(customer, product, amount)
""")

# PIVOT：长表变宽表
pivot_df = con.execute("""
SELECT * FROM (
  SELECT customer, product, amount FROM orders
) PIVOT(SUM(amount) FOR product IN ('Apple', 'Banana', 'Cherry'))
ORDER BY customer
""").df()
print(pivot_df)

# UNPIVOT：宽表变长表
con.execute("""
CREATE TABLE monthly_sales(month VARCHAR, jan DOUBLE, feb DOUBLE, mar DOUBLE, apr DOUBLE);
INSERT INTO monthly_sales VALUES ('sales', 100, 150, 120, 200);
""")

unpivot_df = con.execute("""
SELECT * FROM monthly_sales
UNPIVOT(amount FOR month IN (jan, feb, mar, apr))
""").df()
print(unpivot_df)
```

**注意：** 不需要 `import pandas` 做任何 pivot/melt 操作——全部交给 DuckDB 的 SQL 引擎处理，数据量大了之后性能优势非常明显。

---

## 🧠 PIVOT vs 传统方案对比

| 方案 | PIVOT | CASE WHEN + GROUP BY | Python pivot() |
|------|-------|---------------------|----------------|
| 代码行数 | 1 条 SQL | 10+ 行 SQL | 3-5 行 Python |
| 可读性 | ⭐⭐⭐ | ⭐⭐ | ⭐⭐⭐ |
| 大数据性能 | 优秀（引擎级优化） | 良好 | 受限于内存 |
| 动态列名 | ✅ 支持子查询 | ❌ 需拼接 SQL | ❌ 需 Python 处理 |
| 学习成本 | 低 | 中 | 中 |

---

## 💬 互动

你工作中有没有"行列互转"的痛点场景？欢迎留言分享，说不定下期就写！

---

*📌 收藏这条笔记，下次做数据透视报表时直接回来参考。*

---

*💡 更多 DuckDB 行列转换实战技巧 → duckdblab.org*
