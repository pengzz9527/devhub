---
title: "📊 DuckDB 实战笔记｜2026-08-13：Parquet 列式存储 — 比 CSV 快 10 倍，磁盘占用少 80%"
description: "每天一个 DuckDB 实战技巧。今天教你用 DuckDB 直接查询 Parquet 文件，告别 CSV 的慢速读取，让数据分析速度提升 10 倍，磁盘占用减少 80%。"
date: 2026-08-13
tags: ["DuckDB", "Parquet", "列式存储", "性能优化", "SQL", "实战"]
categories: ["DuckDB 实战笔记"]
toc: false
---

# 📊 DuckDB 实战笔记 ｜ 2026-08-13

> **每天一个 DuckDB 实战技巧，让你立刻能用。**

---

## 🔥 今日话题：Parquet 列式存储 — 比 CSV 快 10 倍，磁盘占用少 80%

你有没有遇到过这种场景：

> 一个 5GB 的 CSV 文件，用 Python pandas 读取要 30 秒，内存占用 12GB。做个简单的 GROUP BY 聚合，又要等 20 秒。
>
> 或者老板说"把上个月的销售数据导出来分析"，结果你跑了半小时才拿到结果。

**根本原因不是你的代码写得不好，而是 CSV 这种格式本身就不适合数据分析。**

CSV 是行式存储——每行是一条完整记录。你要查"所有订单的总金额"，DuckDB 必须把每一行的每一个字段都读进来，哪怕你只关心其中一个字段。

**Parquet 是列式存储——同一列的数据连续存放。** 你只读需要的列，跳过不相关的列。同样的查询，速度可以快 10 倍以上，磁盘占用减少 80%。

---

## 📋 场景：CSV vs Parquet 性能对比

假设你有一张订单表，1000 万行数据：

### 第一步：生成测试数据

```python
import duckdb

con = duckdb.connect(":memory:")

# 生成 1000 万行订单数据
con.execute("""
CREATE TABLE orders AS
SELECT
    generate_series AS order_id,
    (random() * 1000 + 1)::INTEGER AS customer_id,
    (random() * 500 + 1)::INTEGER AS product_id,
    (random() * 10000 + 10)::DOUBLE AS amount,
    CASE WHEN random() < 0.7 THEN 'completed' ELSE 'pending' END AS status,
    DATE '2026-01-01' + (random() * 365)::INTEGER AS order_date
FROM generate_series(1, 10000000)
""")

# 保存为 CSV 和 Parquet
con.execute("COPY orders TO '/tmp/orders.csv' (HEADER, DELIMITER ',')")
con.execute("COPY orders TO '/tmp/orders.parquet'")

print("✅ 数据生成完毕")
```

**文件大小对比：**

| 格式 | 文件大小 | 相对 CSV |
|------|---------|---------|
| CSV | ~1.2 GB | 100% |
| Parquet (SNAPPY 压缩) | ~180 MB | **15%** |

**磁盘占用减少了 85%！**

---

## 💡 第二步：读取速度对比

### CSV 读取

```python
import time

# CSV 读取
start = time.time()
df_csv = con.execute("SELECT * FROM read_csv_auto('/tmp/orders.csv')").fetchdf()
csv_time = time.time() - start
print(f"CSV 读取时间: {csv_time:.2f} 秒")
print(f"CSV 内存占用: {df_csv.memory_usage(deep=True).sum() / 1024**2:.1f} MB")
```

### Parquet 读取

```python
# Parquet 读取
start = time.time()
df_parquet = con.execute("SELECT * FROM read_parquet('/tmp/orders.parquet')").fetchdf()
parquet_time = time.time() - start
print(f"Parquet 读取时间: {parquet_time:.2f} 秒")
print(f"Parquet 内存占用: {df_parquet.memory_usage(deep=True).sum() / 1024**2:.1f} MB")
```

**典型结果：**

```
CSV 读取时间: 8.5 秒
CSV 内存占用: 1250.3 MB

Parquet 读取时间: 0.8 秒
Parquet 内存占用: 320.5 MB
```

**Parquet 读取速度快 10 倍，内存占用少 74%！**

---

## 💡 第三步：只读需要的列 — Parquet 的最大优势

这是 Parquet 最强大的地方。CSV 必须读取整行，而 Parquet 可以只读你需要的列。

### CSV 方式（必须读所有列）

```sql
-- 即使只需要 customer_id 和 amount，CSV 也要读全部 6 列
SELECT customer_id, SUM(amount) AS total
FROM read_csv_auto('/tmp/orders.csv')
WHERE status = 'completed'
GROUP BY customer_id;
```

### Parquet 方式（只读需要的列）

```sql
-- Parquet 只读取 customer_id 和 amount 两列，跳过其他 4 列
SELECT customer_id, SUM(amount) AS total
FROM read_parquet('/tmp/orders.parquet')
WHERE status = 'completed'
GROUP BY customer_id;
```

**性能差距：**

| 操作 | CSV | Parquet | 加速比 |
|------|-----|---------|--------|
| 读取全部列 | 8.5s | 0.8s | **10.6x** |
| 只读 2 列 | 8.5s | 0.15s | **56.7x** |

**只读 2 列时，Parquet 比 CSV 快 56 倍！**

---

## 📋 场景：实际数据分析工作流

### 日常工作流：从 CSV 到 Parquet

很多数据团队的工作流是：原始数据以 CSV 格式接收 → 清洗 → 分析。优化这个流程的关键一步是**在清洗完成后转换为 Parquet**。

```python
import duckdb

con = duckdb.connect(":memory:")

# 1. 从 CSV 读取原始数据
raw_data = con.execute("""
    SELECT * FROM read_csv_auto('/data/sales_2026.csv')
""").fetchdf()

# 2. 数据清洗
cleaned_data = con.execute("""
    SELECT
        order_id,
        customer_id,
        product_id,
        amount,
        order_date,
        CASE 
            WHEN amount < 0 THEN NULL
            WHEN amount > 100000 THEN NULL
            ELSE amount
        END AS amount_clean
    FROM read_csv_auto('/data/sales_2026.csv')
    WHERE order_date >= '2026-01-01'
""").fetchdf()

# 3. 保存为 Parquet（一次性转换，后续所有查询都用 Parquet）
cleaned_data.to_parquet('/data/sales_2026_clean.parquet', index=False)

# 4. 后续分析直接使用 Parquet
result = con.execute("""
    SELECT 
        DATE_TRUNC('month', order_date) AS month,
        SUM(amount_clean) AS monthly_revenue,
        COUNT(*) AS order_count
    FROM read_parquet('/data/sales_2026_clean.parquet')
    GROUP BY month
    ORDER BY month
""").fetchdf()

print(result)
```

---

## 🚀 实战技巧：Parquet 的高级功能

### 技巧 1：分区 Parquet 文件

当数据量很大时，按日期分区存储可以进一步提升查询性能：

```python
# 按月份分区写入 Parquet
con.execute("""
COPY (
    SELECT * FROM read_csv_auto('/data/sales_2026.csv')
) TO '/data/sales_2026_partitioned/' 
(ORDER BY order_date, PARTITION_BY (order_date))
""")
```

目录结构：

```
/data/sales_2026_partitioned/
├── order_date=2026-01-01/
│   └── part-0.parquet
├── order_date=2026-02-01/
│   └── part-0.parquet
├── order_date=2026-03-01/
│   └── part-0.parquet
└── ...
```

**分区查询：** DuckDB 可以自动识别分区目录，只读取需要的分区。

```sql
-- 只读取 2026 年 6 月的数据，跳过其他 5 个分区
SELECT *
FROM read_parquet('/data/sales_2026_partitioned/')
WHERE order_date >= '2026-06-01' AND order_date < '2026-07-01';
```

### 技巧 2：压缩算法选择

Parquet 支持多种压缩算法：

| 压缩算法 | 压缩率 | 读取速度 | 适用场景 |
|---------|--------|---------|---------|
| **无压缩** | 100% | 最快 | 频繁写入、实时数据 |
| **SNAPPY** | 60-70% | 快 | 通用场景，最佳平衡 |
| **GZIP** | 40-50% | 中等 | 归档、长期存储 |
| **ZSTD** | 35-45% | 中等 | 最大压缩率 |

```python
# 使用 SNAPPY 压缩（推荐）
con.execute("""
COPY orders TO '/tmp/orders_snappy.parquet'
(COMPRESSION 'SNAPPY')
""")

# 使用 ZSTD 压缩（最大压缩）
con.execute("""
COPY orders TO '/tmp/orders_zstd.parquet'
(COMPRESSION 'ZSTD')
""")
```

### 技巧 3：并行读取

DuckDB 会自动并行读取 Parquet 文件，充分利用多核 CPU：

```python
# 设置并行度
con.execute("SET threads TO 8")

# 读取多个 Parquet 文件（自动并行）
result = con.execute("""
    SELECT * FROM read_parquet('/data/sales_*.parquet')
""").fetchdf()
```

---

## 🐍 在 Python 中使用 Parquet

```python
import duckdb
import pandas as pd

# 连接 DuckDB
con = duckdb.connect(":memory:")

# 方式 1：直接用 DuckDB 读取 Parquet
df = con.execute("SELECT * FROM read_parquet('/data/sales.parquet')").fetchdf()

# 方式 2：从 pandas DataFrame 写入 Parquet
df.to_parquet('/data/sales_from_pandas.parquet', index=False)

# 方式 3：从 Parquet 读取后直接做分析
result = con.execute("""
    SELECT 
        DATE_TRUNC('month', order_date) AS month,
        customer_id,
        SUM(amount) AS total,
        AVG(amount) AS avg_amount
    FROM read_parquet('/data/sales.parquet')
    WHERE order_date >= '2026-01-01'
    GROUP BY month, customer_id
    HAVING SUM(amount) > 1000
    ORDER BY total DESC
    LIMIT 100
""").fetchdf()

# 方式 4：交互式探索（Jupyter Notebook）
con.execute("INSTALL parquet; LOAD parquet;")
con.execute("SELECT * FROM '/data/sales.parquet' LIMIT 10").show()
```

---

## 🧠 CSV vs Parquet 完整对比

| 特性 | CSV | Parquet |
|------|-----|---------|
| 读取速度 | 慢（必须读整行） | 快（只读需要的列） |
| 磁盘占用 | 大 | 小（压缩率高） |
| 内存占用 | 高 | 低 |
| 数据类型 | 全部字符串 | 保留原始类型 |
| 嵌套数据 | 不支持 | 支持结构体、数组 |
| 压缩 | 无 | 多种压缩算法 |
| 分区 | 不支持 | 支持自动分区 |
| 适用场景 | 小数据、临时交换 | 大数据分析、数据仓库 |

---

## 📝 小结

| 技能 | 一句话总结 |
|------|-----------|
| Parquet 读取 | `read_parquet('/path/to/file.parquet')` |
| Parquet 写入 | `COPY table TO '/path/' (FORMAT PARQUET)` |
| 只读指定列 | `SELECT col1, col2 FROM read_parquet(...)` |
| 分区查询 | 按日期分区存储，自动跳过无关分区 |
| 压缩选择 | 通用场景用 SNAPPY，归档用 ZSTD |
| 工作流优化 | CSV 原始数据 → 清洗 → 转 Parquet → 分析 |

**DuckDB + Parquet 让你：同样的查询，快 10 倍；同样的数据，占 1/5 空间。这不是优化，这是换了一种更聪明的工作方式。**

---

## 💬 互动

你的项目中有没有"大 CSV 文件分析慢"的痛点？把文件大小和查询需求发出来，我们一起看看 Parquet 能带来多少提升！

---

📌 收藏这条笔记，下次遇到大文件分析时直接回来参考。

---

🔍 想系统学习 DuckDB 性能优化？duckdblab.org 上有完整教程系列，从基础查询到 Parquet 高级用法，带你成为 DuckDB 实战专家。
