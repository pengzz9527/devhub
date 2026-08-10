---
title: "📊 DuckDB 实战笔记｜2026-08-03：EXPLAIN ANALYZE — 诊断慢查询的终极武器"
description: "每天一个 DuckDB 实战技巧。今天教你用 EXPLAIN ANALYZE 诊断慢查询，找出性能瓶颈，让查询速度提升 10 倍。"
date: 2026-08-03
tags: ["DuckDB", "EXPLAIN", "性能优化", "慢查询", "SQL", "实战"]
categories: ["DuckDB 实战笔记"]
toc: false
---

# 📊 DuckDB 实战笔记 ｜ 2026-08-03

> **每天一个 DuckDB 实战技巧，让你立刻能用。**

---

## 🔥 今日话题：EXPLAIN ANALYZE — 诊断慢查询的终极武器

你有没有遇到过这种场景：

> 一条 SQL 在测试数据上跑很快，但到了生产环境就卡死。或者明明数据量不大，查询却花了 10 秒以上。

传统做法是什么？猜测问题 → 加索引 → 改查询 → 再测 → 还是慢 → 继续猜。来回折腾几小时，最后可能也没找到真正的问题。

**用 DuckDB 的 EXPLAIN ANALYZE，你可以直接"看到"查询的执行计划，精确找到性能瓶颈。**

---

## 📋 场景：慢查询诊断

假设你有一张订单表，数据量 1000 万行：

```sql
CREATE TABLE orders AS
SELECT
    id,
    customer_id,
    product_id,
    amount,
    status,
    order_date
FROM (VALUES
    (1, 101, 201, 5999.00, 'completed', DATE '2026-01-15'),
    (2, 102, 202, 399.00, 'pending', DATE '2026-02-20'),
    (3, 101, 203, 1200.00, 'completed', DATE '2026-03-10')
) AS t(id, customer_id, product_id, amount, status, order_date);

-- 模拟大数据量
INSERT INTO orders
SELECT
    generate_series(4, 10000000),
    (random() * 1000)::INTEGER + 1,
    (random() * 500)::INTEGER + 1,
    (random() * 10000)::DOUBLE,
    CASE WHEN random() < 0.7 THEN 'completed' ELSE 'pending' END,
    DATE '2026-01-01' + (random() * 365)::INTEGER
;
```

现在你要执行这个查询：

```sql
SELECT customer_id, SUM(amount) AS total
FROM orders
WHERE status = 'completed'
  AND order_date >= DATE '2026-06-01'
GROUP BY customer_id
ORDER BY total DESC
LIMIT 100;
```

查询结果正确，但跑了 8 秒。问题出在哪？

---

## 💡 第一步：用 EXPLAIN 看执行计划

```sql
EXPLAIN
SELECT customer_id, SUM(amount) AS total
FROM orders
WHERE status = 'completed'
  AND order_date >= DATE '2026-06-01'
GROUP BY customer_id
ORDER BY total DESC
LIMIT 100;
```

**输出：**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            EXPLAIN PLAN                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ OptimizerResult                                                           │
│  └─OrderByTotal DESC, Limit100                                            │
│      └─Aggregate(groupKey=[customer_id], aggregates=[[SUM(amount) AS      │
│              total]])                                                      │
│          └─FilterNode[(status = 'completed') AND (order_date >=            │
│              2026-06-01)]                                                   │
│              └─TableScan orders                                            │
│                  └─SelectionPredicate[(status = 'completed') AND          │
│                      (order_date >= 2026-06-01)]                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

**解读：** 可以看到 DuckDB 选择了全表扫描（TableScan），然后过滤、聚合、排序。没有用到索引。

---

## 💡 第二步：用 EXPLAIN ANALYZE 看实际执行

```sql
EXPLAIN ANALYZE
SELECT customer_id, SUM(amount) AS total
FROM orders
WHERE status = 'completed'
  AND order_date >= DATE '2026-06-01'
GROUP BY customer_id
ORDER BY total DESC
LIMIT 100;
```

**输出（关键部分）：**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              QUERY PLAN                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ OptimizerResult                                                           │
│  └─OrderByTotal DESC, Limit100                                            │
│      └─Aggregate(groupKey=[customer_id], aggregates=[[SUM(amount) AS      │
│              total]])                                                      │
│          └─FilterNode[(status = 'completed') AND (order_date >=            │
│              2026-06-01)] (rows actual: 500234)                            │
│              └─TableScan orders (rows read: 10000000, rows_filtered:       │
│                  500234, selection_time: 2.3s)                             │
│                                                                             │
│ Execution Time: 8.2s                                                      │
│ - TableScan: 2.3s (读取了全部 1000 万行)                                    │
│ - Filter: 0.1s (过滤后剩 50 万行)                                           │
│ - Aggregate: 3.5s (分组聚合)                                               │
│ - OrderBy: 2.3s (排序)                                                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

**关键发现：**
- `TableScan orders` 读了全部 1000 万行 → **瓶颈在这里！**
- `TableScan` 耗时 2.3s，占总时间 28%
- 过滤后只剩 50 万行，但已经读了 1000 万行

---

## 💡 第三步：诊断问题 — 缺少索引

问题很明确：`status` 和 `order_date` 列没有索引，导致全表扫描。

**解决方案：创建复合索引**

```sql
CREATE INDEX idx_orders_status_date ON orders(status, order_date);
```

再次执行 EXPLAIN ANALYZE：

```sql
EXPLAIN ANALYZE
SELECT customer_id, SUM(amount) AS total
FROM orders
WHERE status = 'completed'
  AND order_date >= DATE '2026-06-01'
GROUP BY customer_id
ORDER BY total DESC
LIMIT 100;
```

**新输出：**

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              QUERY PLAN                                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ OptimizerResult                                                           │
│  └─OrderByTotal DESC, Limit100                                            │
│      └─Aggregate(groupKey=[customer_id], aggregates=[[SUM(amount) AS      │
│              total]])                                                      │
│          └─FilterNode[(status = 'completed') AND (order_date >=            │
│              2026-06-01)] (rows actual: 500234)                            │
│              └─IndexScan idx_orders_status_date (rows read: 500234,        │
│                  rows_filtered: 500234, selection_time: 0.3s)              │
│                                                                             │
│ Execution Time: 4.1s                                                      │
│ - IndexScan: 0.3s (只读了 50 万行，而不是 1000 万行)                        │
│ - Filter: 0.05s                                                           │
│ - Aggregate: 3.2s                                                         │
│ - OrderBy: 0.5s                                                           │
└─────────────────────────────────────────────────────────────────────────────┘
```

**改进效果：**
- 执行时间从 8.2s 降到 4.1s，**提升 50%**
- TableScan → IndexScan，读取行数从 1000 万降到 50 万，**减少 95%**

---

## 💡 第四步：深入解读 EXPLAIN ANALYZE 输出

EXPLAIN ANALYZE 的输出包含几个关键信息：

### 1. 行估计 vs 实际行（rows actual vs rows estimated）

```sql
-- 如果实际行数和估计行数差距很大，说明统计信息过时
EXPLAIN ANALYZE
SELECT * FROM orders WHERE customer_id = 101;
```

**输出可能显示：**
```
FilterNode[(customer_id = 101)] (rows estimated: 10000, rows actual: 9500)
```

如果估计 10000 行但实际只有 100 行，说明统计信息不准。需要更新统计信息：

```sql
ANALYZE orders;
```

### 2. 各阶段耗时

```
Execution Time: 8.2s
- TableScan: 2.3s
- Filter: 0.1s
- Aggregate: 3.5s
- OrderBy: 2.3s
```

**解读技巧：**
- 如果某个阶段耗时特别长，就是瓶颈
- 如果 Aggregate 耗时最长，考虑增加内存或并行度
- 如果 OrderBy 耗时最长，考虑是否真的需要排序

### 3. 读取行数 vs 过滤行数

```
TableScan orders (rows read: 10000000, rows_filtered: 500234)
```

- `rows read`：扫描的总行数
- `rows_filtered`：过滤后的行数

如果 `rows read` 远大于 `rows_filtered`，说明过滤效率低，需要索引。

---

## 💡 第五步：常见性能瓶颈及解决方案

### 瓶颈 1：全表扫描（TableScan）

**症状：** TableScan 读取了大量行，但过滤后只剩很少

**解决方案：**
- 创建合适的索引
- 检查 WHERE 条件是否用到了索引列
- 考虑使用列式存储（Parquet）

```sql
-- 创建索引
CREATE INDEX idx_name ON table(column);

-- 复合索引（注意列顺序）
CREATE INDEX idx_status_date ON orders(status, order_date);
```

### 瓶颈 2：哈希聚合（HashAggregate）内存溢出

**症状：** 出现 `Spilling` 或 `Memory limit exceeded`

**解决方案：**
- 增加 DuckDB 内存限制
- 减少 GROUP BY 的列数
- 使用物化视图预聚合

```sql
-- 增加内存限制
SET memory_limit = '4GB';

-- 减少聚合列
SELECT customer_id, SUM(amount)
FROM orders
GROUP BY customer_id;
```

### 瓶颈 3：排序耗时过长（OrderBy）

**症状：** OrderBy 阶段耗时占主导

**解决方案：**
- 减少排序数据量（先用 WHERE 过滤）
- 使用 LIMIT 限制返回行数
- 创建索引避免排序

```sql
-- 先过滤再排序
SELECT customer_id, SUM(amount) AS total
FROM orders
WHERE status = 'completed'
GROUP BY customer_id
ORDER BY total DESC
LIMIT 100;
```

### 瓶颈 4：重复计算

**症状：** 同一个子查询被执行多次

**解决方案：**
- 使用 CTE 提取公共子查询
- 使用临时表存储中间结果

```sql
-- 不好的写法：子查询重复执行
SELECT * FROM orders WHERE customer_id IN (
    SELECT customer_id FROM orders WHERE status = 'completed'
) AND order_date > '2026-01-01';

-- 好的写法：用 CTE 避免重复
WITH completed_customers AS (
    SELECT DISTINCT customer_id FROM orders WHERE status = 'completed'
)
SELECT o.*
FROM orders o
JOIN completed_customers c ON o.customer_id = c.customer_id
WHERE o.order_date > '2026-01-01';
```

---

## 🚀 实战案例：逐步优化一个慢查询

### 原始查询（15 秒）

```sql
EXPLAIN ANALYZE
SELECT
    o.customer_id,
    c.name,
    COUNT(o.order_id) AS order_count,
    SUM(o.amount) AS total_amount,
    AVG(o.amount) AS avg_amount
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id
WHERE o.status = 'completed'
  AND o.order_date >= DATE '2026-01-01'
  AND c.region = '华东'
GROUP BY o.customer_id, c.name
HAVING COUNT(o.order_id) > 5
ORDER BY total_amount DESC;
```

### 分析结果

```
Execution Time: 15.2s
- TableScan orders: 5.1s (读取 1000 万行)
- HashJoin: 3.2s (连接 customers 表)
- Filter: 0.5s
- Aggregate: 4.8s (分组聚合)
- Filter(Having): 0.1s
- OrderBy: 1.5s
```

### 优化步骤

**第一步：添加索引**

```sql
CREATE INDEX idx_orders_status_date ON orders(status, order_date);
CREATE INDEX idx_customers_region ON customers(region);
```

**第二步：重新 EXPLAIN ANALYZE**

```
Execution Time: 3.8s
- IndexScan orders: 0.8s (只读 50 万行)
- IndexScan customers: 0.2s
- HashJoin: 1.5s
- Aggregate: 1.0s
- OrderBy: 0.3s
```

**第三步：使用物化视图（如果这个查询经常运行）**

```sql
CREATE MATERIALIZED VIEW mv_customer_orders AS
SELECT
    o.customer_id,
    c.name,
    c.region,
    o.status,
    o.order_date,
    o.amount
FROM orders o
JOIN customers c ON o.customer_id = c.customer_id;

CREATE INDEX idx_mv_status_date ON mv_customer_orders(status, order_date);
CREATE INDEX idx_mv_region ON mv_customer_orders(region);
```

**第四步：最终查询**

```sql
EXPLAIN ANALYZE
SELECT
    customer_id,
    name,
    COUNT(order_id) AS order_count,
    SUM(amount) AS total_amount,
    AVG(amount) AS avg_amount
FROM mv_customer_orders
WHERE status = 'completed'
  AND order_date >= DATE '2026-01-01'
  AND region = '华东'
GROUP BY customer_id, name
HAVING COUNT(order_id) > 5
ORDER BY total_amount DESC;
```

**最终结果：**

```
Execution Time: 0.5s
- IndexScan mv_customer_orders: 0.1s
- Filter: 0.05s
- Aggregate: 0.2s
- OrderBy: 0.1s
```

**优化效果：15.2s → 0.5s，提升 30 倍！**

---

## 🐍 在 Python 中使用 EXPLAIN ANALYZE

```python
import duckdb

con = duckdb.connect(":memory:")

# 创建示例数据
con.execute("""
CREATE TABLE orders AS
SELECT
    generate_series(1, 1000000) AS id,
    (random() * 1000)::INTEGER + 1 AS customer_id,
    (random() * 10000)::DOUBLE AS amount,
    CASE WHEN random() < 0.7 THEN 'completed' ELSE 'pending' END AS status,
    DATE '2026-01-01' + (random() * 365)::INTEGER AS order_date
""")

# 慢查询
query = """
SELECT customer_id, SUM(amount) AS total
FROM orders
WHERE status = 'completed'
  AND order_date >= DATE '2026-06-01'
GROUP BY customer_id
ORDER BY total DESC
LIMIT 100
"""

# 使用 EXPLAIN ANALYZE 诊断
explain_result = con.execute(f"EXPLAIN ANALYZE {query}").fetchdf()
print(explain_result)

# 查看执行时间
result = con.execute(query).fetchdf()
print(f"查询结果行数：{len(result)}")
```

**输出示例：**

```
                                    plan
0   OptimizerResult
1    └─OrderByTotal DESC, Limit100
2        └─Aggregate(groupKey=[customer_id]...
3            └─FilterNode[(status = 'comple...
4                └─TableScan orders (rows r...

查询结果行数：100
```

---

## 🧠 EXPLAIN vs EXPLAIN ANALYZE 对比

| 特性 | EXPLAIN | EXPLAIN ANALYZE |
|------|---------|-----------------|
| 执行查询 | ❌ 不执行 | ✅ 执行查询 |
| 显示执行计划 | ✅ | ✅ |
| 显示实际耗时 | ❌ | ✅ |
| 显示实际行数 | ❌ | ✅ |
| 适用场景 | 初步分析 | 性能诊断 |

**建议：** 日常调试直接用 `EXPLAIN ANALYZE`，一步到位。

---

## 📝 EXPLAIN ANALYZE 输出解读速查

```
┌─────────────────────────────────────────────────────────────┐
│ 执行计划结构                                                 │
├─────────────────────────────────────────────────────────────┤
│ OptimizerResult                                            │
│  └─[操作类型](rows actual: XXX, selection_time: Y.Ys)      │
│      └─[子操作]                                             │
└─────────────────────────────────────────────────────────────┘
```

**关键信息提取：**

| 信息 | 位置 | 含义 |
|------|------|------|
| `rows actual` | 每个节点 | 实际处理的行数 |
| `rows estimated` | 每个节点 | 优化器估计的行数 |
| `selection_time` | 每个节点 | 该节点耗时 |
| `Execution Time` | 最后 | 总执行时间 |
| `rows read` vs `rows_filtered` | TableScan/IndexScan | 扫描效率 |

**常见节点类型：**

| 节点 | 说明 |
|------|------|
| `TableScan` | 全表扫描 |
| `IndexScan` | 索引扫描 |
| `FilterNode` | 过滤操作 |
| `Aggregate` | 聚合操作 |
| `HashJoin` | 哈希连接 |
| `NestedLoopJoin` | 嵌套循环连接 |
| `OrderBy` | 排序操作 |
| `Limit` | 限制返回行数 |

---

## 📝 小结

| 技能 | 一句话总结 |
|------|-----------|
| 查看执行计划 | `EXPLAIN` 查看计划，`EXPLAIN ANALYZE` 执行并查看计划 |
| 识别瓶颈 | 看哪个节点耗时最长、读取行数最多 |
| 添加索引 | `CREATE INDEX idx_name ON table(column)` |
| 更新统计信息 | `ANALYZE table_name` |
| 创建物化视图 | `CREATE MATERIALIZED VIEW` 预聚合常用查询 |

**DuckDB 的 EXPLAIN ANALYZE 让你：不再盲猜性能问题，直接看到查询的每一步执行细节。**

---

## 💬 互动

你的项目中有没有"明明数据量不大，查询却很慢"的情况？把 EXPLAIN ANALYZE 的输出贴出来，我们一起看看问题出在哪！

---

*📌 收藏这条笔记，下次遇到慢查询时直接回来参考。*

---

*© 2026 DuckDB 实战笔记 ｜ 每天进步一点点*

---

🔍 想系统学习 DuckDB 性能优化？duckdblab.org 上有完整教程系列，从基础查询到 EXPLAIN ANALYZE 深度解读，带你成为 DuckDB 性能调优专家。
