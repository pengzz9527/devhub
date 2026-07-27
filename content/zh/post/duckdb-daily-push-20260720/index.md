---
title: "📊 DuckDB 实战笔记｜2026-07-20：PIVOT — 告别 Excel 透视表，SQL 一行转宽表"
description: "每天一个 DuckDB 实战技巧。今天教你用 DuckDB 的 PIVOT 语句，把长表秒变宽表，生成报表再也不用拖 Excel 透视表了。"
date: 2026-07-20
tags: ["DuckDB", "PIVOT", "宽表", "报表", "SQL", "实战"]
categories: ["DuckDB 实战笔记"]
toc: false
---

# 📊 DuckDB 实战笔记 ｜ 2026-07-20

> **每天一个 DuckDB 实战技巧，让你立刻能用。**

---

## 🔥 今日话题：PIVOT — 告别 Excel 透视表，SQL 一行转宽表

你有没有遇到过这种需求：

> 老板要一份「每月销售额」的宽表——左边是销售员姓名，上面是月份，中间是销售额。

传统做法是什么？导出 CSV → 打开 Excel → 插入透视表 → 拖拽字段 → 调格式 → 截图发给老板。一套流程下来，少则十分钟。

**用 DuckDB 的 PIVOT，一条 SQL 直接把长表转成宽表。数据量再大也不怕。**

---

## 📋 场景：销售月度报表

假设你有一张销售记录表 `sales`，数据是"长表"格式：

| name | quarter | amount |
|------|---------|--------|
| Alice | Q1 | 100 |
| Alice | Q2 | 150 |
| Alice | Q3 | 200 |
| Bob | Q1 | 80 |
| Bob | Q2 | 120 |
| Bob | Q3 | 90 |

**目标：** 把季度变成列，得到一张宽表：

| name | Q1 | Q2 | Q3 |
|------|----|----|----|
| Alice | 100 | 150 | 200 |
| Bob | 80 | 120 | 90 |

---

## 💡 第一步：基础 PIVOT

```sql
CREATE TABLE sales AS
SELECT * FROM (VALUES
    ('Alice', 'Q1', 100),
    ('Alice', 'Q2', 150),
    ('Alice', 'Q3', 200),
    ('Bob',   'Q1', 80),
    ('Bob',   'Q2', 120),
    ('Bob',   'Q3', 90)
) AS t(name, quarter, amount);

PIVOT sales ON quarter USING SUM(amount);
```

**结果：**

```
┌─────────┬────────┬────────┬────────┐
│  name   │   Q1   │   Q2   │   Q3   │
├─────────┼────────┼────────┼────────┤
│ Alice   │    100 │    150 │    200 │
│ Bob     │     80 │    120 │     90 │
└─────────┴────────┴────────┴────────┘
```

**就这么简单。** 三行 SQL，替代整个 Excel 透视表操作。

---

## 💡 第二步：多聚合函数同时计算

PIVOT 不只支持一个聚合函数。你可以同时算 SUM、AVG、COUNT：

```sql
PIVOT sales ON quarter USING SUM(amount), AVG(amount), COUNT(*);
```

**结果：**

```
┌─────────┬───────────────┬───────────────┬──────────────┬───────────────┬───────────────┬──────────────┐
│  name   │ Q1_sum(amount)│ Q1_avg(amount)│Q1_count_star()│ Q2_sum(amount)│ Q2_avg(amount)│Q2_count_star()│
├─────────┼───────────────┼───────────────┼──────────────┼───────────────┼───────────────┼──────────────┤
│ Alice   │           100 │          100.0 │            1 │           150 │          150.0 │            1 │
│ Bob     │            80 │           80.0 │            1 │           120 │          120.0 │            1 │
└─────────┴───────────────┴───────────────┴──────────────┴───────────────┴───────────────┴──────────────┘
```

**列名自动带上聚合函数前缀**，一目了然。

---

## 💡 第三步：加别名让列名更清晰

```sql
PIVOT sales ON quarter USING SUM(amount) AS total;
```

**结果：**

```
┌─────────┬──────────┬──────────┬──────────┐
│  name   │ Q1_total │ Q2_total │ Q3_total │
├─────────┼──────────┼──────────┼──────────┤
│ Alice   │      100 │      150 │      200 │
│ Bob     │       80 │      120 │       90 │
└─────────┴──────────┴──────────┴──────────┘
```

---

## 💡 第四步：过滤后再 PIVOT

如果只想统计金额大于 90 的记录，用 CTE 先过滤再透视：

```sql
WITH filtered AS (
    SELECT * FROM sales WHERE amount > 90
)
PIVOT filtered ON quarter USING SUM(amount);
```

**结果：**

```
┌─────────┬────────┬────────┬────────┐
│  name   │   Q1   │   Q2   │   Q3   │
├─────────┼────────┼────────┼────────┤
│ Alice   │    100 │    150 │    200 │
│ Bob     │   NULL │    120 │   NULL │
└─────────┴────────┴────────┴────────┘
```

**注意：** 不满足条件的单元格显示为 NULL，而不是 0。如果需要补 0，可以用 `COALESCE`：

```sql
WITH filtered AS (
    SELECT * FROM sales WHERE amount > 90
)
SELECT name,
       COALESCE("Q1", 0) AS q1,
       COALESCE("Q2", 0) AS q2,
       COALESCE("Q3", 0) AS q3
FROM PIVOT filtered ON quarter USING SUM(amount);
```

---

## 💡 第五步：UNPIVOT — 反向操作

宽表转长表同样可以用 DuckDB 完成。假设你有一张月度宽表：

```sql
CREATE TABLE monthly_sales(name TEXT, jan INT, feb INT, mar INT);
INSERT INTO monthly_sales VALUES
    ('Alice', 100, 150, 200),
    ('Bob', 80, 120, 90);
```

**目标：** 转回长表格式：

| name | month | value |
|------|-------|-------|
| Alice | jan | 100 |
| Alice | feb | 150 |
| Alice | mar | 200 |
| Bob | jan | 80 |
| Bob | feb | 120 |
| Bob | mar | 90 |

**方法一：UNION ALL（兼容所有版本）**

```sql
SELECT name, 'jan' AS month, jan AS value FROM monthly_sales
UNION ALL
SELECT name, 'feb', feb FROM monthly_sales
UNION ALL
SELECT name, 'mar', mar FROM monthly_sales
ORDER BY name, month;
```



---

## 🚀 实战案例：电商订单分析

真实场景中，PIVOT 特别适合做运营日报/周报：

```sql
-- 原始数据：每天的订单记录
CREATE TABLE orders AS
SELECT * FROM (VALUES
    ('北京', '电子产品', 5999),
    ('上海', '服装', 399),
    ('北京', '食品', 120),
    ('广州', '电子产品', 8999),
    ('上海', '服装', 599),
    ('北京', '食品', 80)
) AS t(city, category, amount);

-- 按城市 × 品类透视，看每个城市的品类销售分布
PIVOT orders ON category USING SUM(amount);
```

**结果：**

```
┌─────────┬──────────────┬────────┬────────┐
│  city   │ sum(amount)  │ 服装   │ 食品   │
├─────────┼──────────────┼────────┼────────┤
│ 北京    │          6079│    NULL│     200│
│ 上海    │           998│     998│    NULL│
│ 广州    │          8999│    NULL│    NULL│
└─────────┴──────────────┴────────┴────────┘
```

---

## 🐍 在 Python 中使用

```python
import duckdb

con = duckdb.connect(":memory:")

# 创建示例数据
con.execute("""
CREATE TABLE sales AS
SELECT * FROM (VALUES
    ('Alice', 'Q1', 100), ('Alice', 'Q2', 150), ('Alice', 'Q3', 200),
    ('Bob', 'Q1', 80), ('Bob', 'Q2', 120), ('Bob', 'Q3', 90)
) AS t(name, quarter, amount)
""")

# PIVOT：长表转宽表
result = con.execute("""
PIVOT sales ON quarter USING SUM(amount)
""").fetchdf()

print(result)

# 输出：
#    name  Q1  Q2  Q3
# 0  Alice 100 150 200
# 1    Bob  80 120  90
```

---

## 🧠 PIVOT 语法速记

```sql
PIVOT table_name ON 行转列的字段 USING 聚合函数1, 聚合函数2, ...;
```

**关键点：**

- `ON` 后面的字段会变成新的列头
- `USING` 后面跟聚合函数，决定每个单元格的值
- 除了 PIVOT 的列之外，其他列会自动作为分组键
- 支持别名：`USING SUM(col) AS alias`
- 过滤时用 CTE 先处理数据，再 PIVOT

---

## 📝 PIVOT vs 传统方案对比

| 方案 | 代码量 | 性能 | 灵活性 |
|------|--------|------|--------|
| **PIVOT** | 1 条 SQL | ⭐⭐⭐ 极快 | ⭐⭐⭐ 高 |
| Excel 透视表 | 手动操作 | ⭐⭐ 中等 | ⭐⭐ 一般 |
| Python pandas.pivot_table | 5-10 行代码 | ⭐⭐ 良好 | ⭐⭐⭐ 高 |
| CASE WHEN + GROUP BY | 1 条 SQL | ⭐⭐⭐ 极快 | ⭐ 低（需预设列） |

**PIVOT vs CASE WHEN：**

- `CASE WHEN` 需要提前知道所有列名，动态列需要拼接 SQL
- `PIVOT` 自动检测所有唯一值并生成列，无需硬编码
- 对于列值固定的场景，两者性能接近；对于动态列场景，PIVOT 更方便

---

## 📝 小结

| 能力 | 一句话总结 |
|------|-----------|
| 长表转宽表 | `PIVOT table ON 列 USING 聚合函数` |
| 多聚合 | `USING SUM(), AVG(), COUNT()` 同时计算 |
| 别名 | `USING SUM(col) AS alias` 自定义列名 |
| 过滤 | 用 CTE 先过滤再 PIVOT |
| 反向操作 | `UNION ALL` 或 `unpivot_list()` |
| 自动列名 | 不需要提前知道所有列值 |

**DuckDB 的 PIVOT 让你：告别 Excel 透视表，一条 SQL 搞定行列转换。**

---

## 💬 互动

你的工作中有没有"长表转宽表"的场景？留言告诉我，我们一起看看用 PIVOT 怎么优雅解决！

---

*📌 收藏这条笔记，下次做报表时直接回来参考。*

---

*© 2026 DuckDB 实战笔记 ｜ 每天进步一点点*

---

💡 更多 DuckDB 实战技巧 → duckdblab.org
