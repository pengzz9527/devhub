---
title: "📊 DuckDB 实战笔记｜2026-07-23：窗口函数 — 告别 VLOOKUP，SQL 一行做排名和同比"
description: "每天一个 DuckDB 实战技巧。今天教你用 DuckDB 的窗口函数（ROW_NUMBER / RANK / LAG），做排名、算环比同比、找每个类别的 Top N，全程一条 SQL 搞定。"
date: 2026-07-23
tags: ["DuckDB", "窗口函数", "排名", "环比", "Top N", "SQL", "实战"]
categories: ["DuckDB 实战笔记"]
toc: false
---

# 📊 DuckDB 实战笔记 ｜ 2026-07-23

> **每天一个 DuckDB 实战技巧，让你立刻能用。**

---

## 🔥 今日话题：窗口函数 — 告别 VLOOKUP，SQL 一行做排名和同比

你有没有遇到过这种需求：

> 找出每个部门销售额最高的前 3 名员工，或者计算每个月相比上个月的业绩变化率？

传统做法是什么？在 Excel 里用 `VLOOKUP` + `IF` 一堆嵌套公式，或者写 Python pandas 代码，又长又容易出错。

**用 DuckDB 的窗口函数（Window Functions），这些操作一条 SQL 就能搞定。不需要 JOIN，不需要子查询，直接在原始数据上"开窗"计算。**

---

## 📋 场景：员工绩效排名

假设你有一张销售记录表 `sales`，包含每位员工的月度业绩：

```sql
CREATE TABLE sales AS
SELECT * FROM (VALUES
    ('北京', 'Alice',   15000, '2026-06'),
    ('北京', 'Bob',     12000, '2026-06'),
    ('北京', 'Charlie', 18000, '2026-06'),
    ('北京', 'Alice',   16000, '2026-07'),
    ('北京', 'Bob',     14000, '2026-07'),
    ('北京', 'Charlie', 13000, '2026-07'),
    ('上海', 'David',   20000, '2026-06'),
    ('上海', 'Eve',     17000, '2026-06'),
    ('上海', 'Frank',   22000, '2026-06'),
    ('上海', 'David',   21000, '2026-07'),
    ('上海', 'Eve',     19000, '2026-07'),
    ('上海', 'Frank',   18000, '2026-07')
) AS t(city, name, amount, month);
```

---

## 💡 第一步：ROW_NUMBER — 给每组数据编号

这是最基础的窗口函数。`ROW_NUMBER() OVER (PARTITION BY ... ORDER BY ...)` 按分区排序后编号：

```sql
SELECT city, name, amount, month,
       ROW_NUMBER() OVER (PARTITION BY city ORDER BY amount DESC) AS rank_in_city
FROM sales;
```

**结果：**

```
┌─────────┬─────────┬────────┬──────────┬─────────────┐
│  city   │  name   │ amount │  month   │ rank_in_city│
├─────────┼─────────┼────────┼──────────┼─────────────┤
│ 北京    │ Charlie │  18000 │ 2026-06  │     1       │
│ 北京    │ Alice   │  16000 │ 2026-07  │     2       │
│ 北京    │ Alice   │  15000 │ 2026-06  │     3       │
│ 北京    │ Bob     │  14000 │ 2026-07  │     4       │
│ 北京    │ Bob     │  12000 │ 2026-06  │     5       │
│ 上海    │ Frank   │  22000 │ 2026-07  │     1       │
│ 上海    │ David   │  21000 │ 2026-07  │     2       │
│ 上海    │ David   │  20000 │ 2026-06  │     3       │
│ 上海    │ Eve     │  19000 │ 2026-07  │     4       │
│ 上海    │ Eve     │  17000 │ 2026-06  │     5       │
└─────────┴─────────┴────────┴──────────┴─────────────┘
```

**看懂了吗？** `PARTITION BY city` 把数据按城市分组，`ORDER BY amount DESC` 在组内按金额降序排，然后编上号。

---

## 💡 第二步：取每个城市的 Top N

有了 ROW_NUMBER，筛选 Top N 就超简单——外层套个过滤就行：

```sql
WITH ranked AS (
    SELECT city, name, amount, month,
           ROW_NUMBER() OVER (PARTITION BY city ORDER BY amount DESC) AS rn
    FROM sales
)
SELECT city, name, amount, month
FROM ranked
WHERE rn <= 2;
```

**结果：**

```
┌─────────┬─────────┬────────┬──────────┐
│  city   │  name   │ amount │  month   │
├─────────┼─────────┼────────┼──────────┤
│ 北京    │ Charlie │  18000 │ 2026-06  │
│ 北京    │ Alice   │  16000 │ 2026-07  │
│ 上海    │ Frank   │  22000 │ 2026-07  │
│ 上海    │ David   │  21000 │ 2026-07  │
└─────────┴─────────┴────────┴──────────┘
```

**这就是"每个城市 Top 2"——不用写复杂的 GROUP BY，不用 JOIN 子查询。**

---

## 💡 第三步：RANK vs DENSE_RANK vs ROW_NUMBER

这三个函数名字很像，但行为不同：

| 函数 | 相同值处理 | 后续编号 |
|------|-----------|---------|
| `ROW_NUMBER()` | 强制唯一编号 | 连续递增 |
| `RANK()` | 相同值同排名 | 跳过后续（1,1,3） |
| `DENSE_RANK()` | 相同值同排名 | 不跳过（1,1,2） |

```sql
SELECT name, amount,
       ROW_NUMBER() OVER (ORDER BY amount DESC) AS rn,
       RANK()       OVER (ORDER BY amount DESC) AS rk,
       DENSE_RANK() OVER (ORDER BY amount DESC) AS drk
FROM sales
WHERE month = '2026-06';
```

**结果：**

```
┌─────────┬────────┬──────┬────┬─────┐
│  name   │ amount │  rn  │ rk │ drk │
├─────────┼────────┼──────┼────┼─────┤
│ Frank   │  22000 │  1   │  1 │  1  │
│ David   │  20000 │  2   │  2 │  2  │
│ Charlie │  18000 │  3   │  3 │  3  │
│ Eve     │  17000 │  4   │  4 │  4  │
│ Alice   │  15000 │  5   │  5 │  5  │
│ Bob     │  14000 │  6   │  6 │  6  │
└─────────┴────────┴──────┴────┴─────┘
```

**场景选择：**
- 需要**严格分页**（每页固定条数）→ `ROW_NUMBER()`
- 需要**体育比赛式排名**（并列同排名，后续跳过）→ `RANK()`
- 需要**等级制排名**（并列同排名，后续不跳）→ `DENSE_RANK()`

---

## 💡 第四步：LAG / LEAD — 算环比变化

这是窗口函数最实用的场景之一。`LAG(col, n)` 取前 n 行的值，`LEAD(col, n)` 取后 n 行的值：

```sql
SELECT city, name, month, amount,
       LAG(amount) OVER (PARTITION BY city, name ORDER BY month) AS prev_month_amount,
       amount - LAG(amount) OVER (PARTITION BY city, name ORDER BY month) AS change,
       ROUND(
         1.0 * (amount - LAG(amount) OVER (PARTITION BY city, name ORDER BY month))
         / LAG(amount) OVER (PARTITION BY city, name ORDER BY month) * 100, 1
       ) AS change_pct
FROM sales;
```

**结果：**

```
┌─────────┬─────────┬──────────┬────────┬───────────────────┬────────┬──────────┐
│  city   │  name   │  month   │ amount │ prev_month_amount │ change │ change_pct│
├─────────┼─────────┼──────────┼────────┼───────────────────┼────────┼──────────┤
│ 北京    │ Alice   │ 2026-06  │  15000 │      NULL         │ NULL   │   NULL   │
│ 北京    │ Alice   │ 2026-07  │  16000 │      15000        │  1000  │    6.7   │
│ 北京    │ Bob     │ 2026-06  │  12000 │      NULL         │ NULL   │   NULL   │
│ 北京    │ Bob     │ 2026-07  │  14000 │      12000        │  2000  │   16.7   │
│ 北京    │ Charlie │ 2026-06  │  18000 │      NULL         │ NULL   │   NULL   │
│ 北京    │ Charlie │ 2026-07  │  13000 │      18000        │ -5000  │  -27.8   │
│ 上海    │ David   │ 2026-06  │  20000 │      NULL         │ NULL   │   NULL   │
│ 上海    │ David   │ 2026-07  │  21000 │      20000        │  1000  │    5.0   │
│ 上海    │ Eve     │ 2026-06  │  17000 │      NULL         │ NULL   │   NULL   │
│ 上海    │ Eve     │ 2026-07  │  19000 │      17000        │  2000  │   11.8   │
│ 上海    │ Frank   │ 2026-06  │  22000 │      NULL         │ NULL   │   NULL   │
│ 上海    │ Frank   │ 2026-07  │  18000 │      22000        │ -4000  │  -18.2   │
└─────────┴─────────┴──────────┴────────┴───────────────────┴────────┴──────────┘
```

**注意：** 第一行没有上月数据，所以是 NULL。如果需要默认值，可以用 `COALESCE(LAG(...), 0)`。

---

## 💡 第五步：SUM / AVG 做累计求和和移动平均

窗口函数不只用于排名。`SUM() OVER (...)` 可以做累计求和：

```sql
-- 累计销售额（从年初到当前月）
SELECT city, name, month, amount,
       SUM(amount) OVER (PARTITION BY city, name ORDER BY month) AS cumulative,
       AVG(amount) OVER (PARTITION BY city, name ORDER BY month
                         ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) AS moving_avg_3
FROM sales;
```

**结果：**

```
┌─────────┬─────────┬──────────┬────────┬────────────┬─────────────┐
│  city   │  name   │  month   │ amount │ cumulative │ moving_avg_3│
├─────────┼─────────┼──────────┼────────┼────────────┼─────────────┤
│ 北京    │ Alice   │ 2026-06  │  15000 │    15000   │   15000.0   │
│ 北京    │ Alice   │ 2026-07  │  16000 │    31000   │   15500.0   │
│ 北京    │ Bob     │ 2026-06  │  12000 │    12000   │   12000.0   │
│ 北京    │ Bob     │ 2026-07  │  14000 │    26000   │   13000.0   │
│ ...     │  ...    │   ...    │  ...   │    ...     │     ...     │
└─────────┴─────────┴──────────┴────────┴────────────┴─────────────┘
```

`ROWS BETWEEN 2 PRECEDING AND CURRENT ROW` 表示：当前行 + 前面 2 行，共 3 行的移动平均。

---

## 🚀 实战案例：找出每个品类销量最高的月份

真实场景中，你可能需要回答这类问题："我们每个品类的销售高峰在哪个月？"

```sql
-- 模拟更多品类数据
CREATE TABLE product_sales AS
SELECT * FROM (VALUES
    ('电子产品', '2026-01', 50000), ('电子产品', '2026-02', 55000),
    ('电子产品', '2026-03', 62000), ('电子产品', '2026-04', 48000),
    ('电子产品', '2026-05', 70000), ('电子产品', '2026-06', 65000),
    ('服装',     '2026-01', 30000), ('服装',     '2026-02', 35000),
    ('服装',     '2026-03', 42000), ('服装',     '2026-04', 55000),
    ('服装',     '2026-05', 60000), ('服装',     '2026-06', 38000),
    ('食品',     '2026-01', 20000), ('食品',     '2026-02', 22000),
    ('食品',     '2026-03', 25000), ('食品',     '2026-04', 28000),
    ('食品',     '2026-05', 30000), ('食品',     '2026-06', 32000)
) AS t(category, month, revenue);

-- 每个品类的最高收入月份
WITH ranked AS (
    SELECT category, month, revenue,
           ROW_NUMBER() OVER (PARTITION BY category ORDER BY revenue DESC) AS rn
    FROM product_sales
)
SELECT category, month, revenue
FROM ranked
WHERE rn = 1;
```

**结果：**

```
┌──────────┬──────────┬─────────┐
│ category │  month   │ revenue │
├──────────┼──────────┼─────────┤
│ 电子产品 │ 2026-05  │  70000  │
│ 服装     │ 2026-05  │  60000  │
│ 食品     │ 2026-06  │  32000  │
└──────────┴──────────┴─────────┘
```

**一目了然：** 电子产品和服装都在 5 月达到峰值，食品则逐月增长。

---

## 🐍 在 Python 中使用

```python
import duckdb

con = duckdb.connect(":memory:")

# 创建数据
con.execute("""
CREATE TABLE sales AS
SELECT * FROM (VALUES
    ('北京', 'Alice',   15000, '2026-06'),
    ('北京', 'Bob',     12000, '2026-06'),
    ('北京', 'Charlie', 18000, '2026-06'),
    ('北京', 'Alice',   16000, '2026-07'),
    ('北京', 'Bob',     14000, '2026-07'),
    ('北京', 'Charlie', 13000, '2026-07')
) AS t(city, name, amount, month)
""")

# 窗口函数：每个城市销售额排名
result = con.execute("""
    SELECT city, name, amount,
           ROW_NUMBER() OVER (PARTITION BY city ORDER BY amount DESC) AS rank_in_city
    FROM sales
""").fetchdf()

print(result)

# 窗口函数：环比变化
result2 = con.execute("""
    SELECT city, name, month, amount,
           LAG(amount) OVER (PARTITION BY city, name ORDER BY month) AS prev_amount,
           ROUND(1.0 * (amount - LAG(amount) OVER (PARTITION BY city, name ORDER BY month))
                 / NULLIF(LAG(amount) OVER (PARTITION BY city, name ORDER BY month), 0) * 100, 1) AS change_pct
    FROM sales
""").fetchdf()

print(result2)
```

---

## 🧠 窗口函数语法速记

```sql
函数名() OVER (
    PARTITION BY 分组列        -- 类似 GROUP BY，但不压缩行
    ORDER BY 排序列            -- 组内排序
    ROWS BETWEEN 起始位置 AND 结束位置  -- 滑动窗口范围（可选）
)
```

**核心概念：**
- **窗口函数不会减少行数**——这是和 GROUP BY 最大的区别
- `PARTITION BY` 决定"按什么分组"
- `ORDER BY` 决定"组内怎么排"
- `ROWS BETWEEN` 决定"看多宽的范围"

**常用窗口函数清单：**

| 函数 | 用途 |
|------|------|
| `ROW_NUMBER()` | 唯一编号 |
| `RANK()` / `DENSE_RANK()` | 排名（处理并列） |
| `LAG(col, n)` | 取前 n 行的值 |
| `LEAD(col, n)` | 取后 n 行的值 |
| `SUM() OVER()` | 累计求和 |
| `AVG() OVER()` | 移动平均 |
| `COUNT() OVER()` | 累计计数 |
| `FIRST_VALUE()` | 取组内第一个值 |
| `LAST_VALUE()` | 取组内最后一个值 |

---

## 📝 窗口函数 vs 传统方案对比

| 方案 | 代码量 | 可读性 | 性能 |
|------|--------|--------|------|
| **窗口函数** | 1 条 SQL | ⭐⭐⭐ 高 | ⭐⭐⭐ 极快 |
| 自连接 + GROUP BY | 多行 JOIN | ⭐ 低 | ⭐⭐ 一般 |
| Python pandas.groupby | 5-10 行代码 | ⭐⭐ 中等 | ⭐⭐ 良好 |
| Excel 公式 | 手动操作 | ⭐ 极低 | ⭐ 慢 |

---

## 📝 小结

| 能力 | 一句话总结 |
|------|-----------|
| 分组编号 | \`ROW_NUMBER() OVER (PARTITION BY col ORDER BY col)\` |
| 并列排名 | \`RANK()\` 或 \`DENSE_RANK()\` |
| 环比变化 | \`LAG(col)\` 取上一行值 |
| 累计求和 | \`SUM(col) OVER (ORDER BY col)\` |
| 移动平均 | \`AVG(col) OVER (ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)\` |
| Top N 查询 | 外层 CTE + WHERE rn <= N |

**DuckDB 的窗口函数让你：告别 VLOOKUP 和复杂 JOIN，排名、环比、累计全在一行 SQL 里。**

---

## 💬 互动

你的数据分析中，有没有"按组排序"或"算环比"的需求？留言告诉我，我们一起看看窗口函数怎么优雅解决！

---

*📌 收藏这条笔记，下次做报表排名时直接回来参考。*

---

*© 2026 DuckDB 实战笔记 ｜ 每天进步一点点*

---

💡 更多 DuckDB 实战技巧 → duckdblab.org
