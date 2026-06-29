---
title: "📊 DuckDB 实战笔记｜2026-06-25：用 DuckDB 一行 SQL 补全时间序列"
description: "每天一个 DuckDB 实战技巧。今天教你如何用 generate_series + LAST_VALUE IGNORE NULLS 完美补全缺失的时间序列数据。"
date: 2026-06-25
tags: ["DuckDB", "时间序列", "数据补全", "SQL", "实战"]
categories: ["DuckDB 实战笔记"]
toc: false
---

# 📊 DuckDB 实战笔记 ｜ 2026-06-25

> **每天一个 DuckDB 实战技巧，让你立刻能用。**

---

## 🔥 今日话题：用 DuckDB 补全缺失的时间序列

你有没有遇到过这种报表需求：

> "帮我拉一下上周每天的销售额，没有销售的日子也要显示，填 0。"

你的第一反应是什么？写个 Python 脚本，生成日期列表，然后逐个查数据库？还是手动创建连续日期再 LEFT JOIN？

**用 DuckDB，一条 SQL 就能搞定，而且支持多种补全策略。**

---

## 📋 问题场景

假设你有一张订单表 `sales`，只有有交易的日期才有记录：

```sql
CREATE TABLE sales(day DATE, product VARCHAR, amount DOUBLE);
INSERT INTO sales VALUES
  (DATE '2024-01-01', 'A', 100),
  (DATE '2024-01-03', 'A', 200),
  (DATE '2024-01-05', 'A', 300);
```

| day | product | amount |
|-----|---------|--------|
| 2024-01-01 | A | 100 |
| 2024-01-03 | A | 200 |
| 2024-01-05 | A | 300 |

老板要的是 **1月1日到1月5日每天都有数据**，但中间缺了 1月2日和1月4日。

---

## 💡 方案一：补 0（最常用）

```sql
WITH dates AS (
  SELECT unnest(generate_series(
    DATE '2024-01-01', 
    DATE '2024-01-05', 
    INTERVAL '1' DAY
  )) AS day
)
SELECT 
  d.day,
  COALESCE(s.amount, 0) AS amount
FROM dates d
LEFT JOIN sales s ON d.day = s.day
ORDER BY d.day;
```

**结果：**

| day | amount |
|-----|--------|
| 2024-01-01 | 100 |
| 2024-01-02 | 0 |
| 2024-01-03 | 200 |
| 2024-01-04 | 0 |
| 2024-01-05 | 300 |

**核心思路：** 先生成完整日期序列 → LEFT JOIN 原表 → COALESCE 填补 NULL。

---

## 💡 方案二：前向填充（Last Observation Carried Forward）

很多业务场景下，"没有新数据"意味着"沿用上次的数据"。比如股价、库存量、用户活跃度。

```sql
WITH dates AS (
  SELECT unnest(generate_series(
    DATE '2024-01-01', 
    DATE '2024-01-05', 
    INTERVAL '1' DAY
  )) AS day
)
SELECT 
  d.day,
  LAST_VALUE(s.amount IGNORE NULLS) OVER (
    ORDER BY d.day 
    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
  ) AS forward_filled
FROM dates d
LEFT JOIN sales s ON d.day = s.day
ORDER BY d.day;
```

**结果：**

| day | forward_filled |
|-----|----------------|
| 2024-01-01 | 100 |
| 2024-01-02 | 100 ← 沿用前一天的值 |
| 2024-01-03 | 200 |
| 2024-01-04 | 200 ← 沿用前一天的值 |
| 2024-01-05 | 300 |

**杀手锏是 `IGNORE NULLS`** —— 窗口函数会跳过 NULL 值，取最后一个非空值。

---

## 💡 方案三：自动获取日期范围

上面的例子中，起止日期是硬编码的。实际业务中，你通常希望 **自动取数据的最小/最大日期**：

```sql
WITH dates AS (
  SELECT unnest(generate_series(
    (SELECT MIN(day) FROM sales),
    (SELECT MAX(day) FROM sales),
    INTERVAL '1' DAY
  )) AS day
)
SELECT 
  d.day,
  LAST_VALUE(s.amount IGNORE NULLS) OVER (
    ORDER BY d.day 
    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
  ) AS forward_filled
FROM dates d
LEFT JOIN sales s ON d.day = s.day
ORDER BY d.day;
```

**一条 SQL，自动适配任何时间范围。**

---

## 🧠 关键函数解析

### `generate_series(start, end, interval)`
生成一个包含起始到结束所有值的序列。支持：
- 日期：`INTERVAL '1' DAY`
- 小时：`INTERVAL '1' HOUR`
- 分钟：`INTERVAL '5' MINUTE`

### `unnest(array)`
把数组展开为多行。因为 `generate_series` 返回的是一个数组，需要用 `unnest` 拆成行。

### `LAST_VALUE(...) IGNORE NULLS`
窗口函数的高级用法。默认情况下窗口函数会把 NULL 当作有效值，加上 `IGNORE NULLS` 后，它会跳过所有 NULL，返回最近的一个非空值。

### `ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW`
定义窗口范围：从第一行到当前行。配合 `IGNORE NULLS` 实现前向填充。

---

## 🚀 在 Python 中使用

```python
import duckdb

# 读取数据
conn = duckdb.connect()
conn.execute("""
    CREATE TABLE sales AS SELECT * FROM read_csv_auto('sales.csv')
""")

# 前向填充时间序列
result = conn.execute("""
    WITH dates AS (
        SELECT unnest(generate_series(
            (SELECT MIN(day) FROM sales),
            (SELECT MAX(day) FROM sales),
            INTERVAL '1' DAY
        )) AS day
    )
    SELECT 
        d.day,
        LAST_VALUE(s.amount IGNORE NULLS) OVER (
            ORDER BY d.day 
            ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
        ) AS forward_filled
    FROM dates d
    LEFT JOIN sales s ON d.day = s.day
    ORDER BY d.day
""").fetchdf()

print(result)
```

**注意：** 不需要先生成日期 DataFrame 再合并，DuckDB 内部完成所有操作，性能远超 Pandas 的 `reindex`。

---

## 📝 三种补全策略对比

| 策略 | 适用场景 | 核心函数 |
|------|---------|---------|
| **补 0** | 销售额、订单数等计数类指标 | `COALESCE(col, 0)` |
| **前向填充** | 股价、库存、用户状态等 | `LAST_VALUE(...) IGNORE NULLS` |
| **线性插值** | 传感器数据、温度等连续物理量 | 需要额外计算（见下方） |

### 进阶：线性插值

如果需要更精确的填充（比如在两个已知点之间线性插值），可以这样：

```sql
WITH dates AS (
  SELECT unnest(generate_series(
    (SELECT MIN(day) FROM sales),
    (SELECT MAX(day) FROM sales),
    INTERVAL '1' DAY
  )) AS day
),
joined AS (
  SELECT 
    d.day,
    LAG(s.amount) OVER (ORDER BY d.day) AS prev_val,
    LAG(s.day) OVER (ORDER BY d.day) AS prev_day,
    LEAD(s.amount) OVER (ORDER BY d.day) AS next_val,
    LEAD(s.day) OVER (ORDER BY d.day) AS next_day
  FROM dates d
  LEFT JOIN sales s ON d.day = s.day
)
SELECT 
  day,
  CASE
    WHEN amount IS NOT NULL THEN amount
    WHEN prev_val IS NOT NULL AND next_val IS NOT NULL THEN
      prev_val + (next_val - prev_val) * (day - prev_day)::DOUBLE / (next_day - prev_day)::DOUBLE
    WHEN prev_val IS NOT NULL THEN prev_val
    WHEN next_val IS NOT NULL THEN next_val
    ELSE 0
  END AS interpolated
FROM joined
ORDER BY day;
```

利用 `LAG` 和 `LEAD` 获取前后值，然后用公式 `(y2-y1)/(x2-x1)` 线性插值。

---

## 💬 互动

你的报表里最常见的缺失数据问题是什么？补 0、前向填充、还是其他策略？留言告诉我！

---

*📌 收藏这条笔记，下次做日报/周报数据补全时直接回来参考。*

---

*© 2026 DuckDB 实战笔记 ｜ 每天进步一点点*
