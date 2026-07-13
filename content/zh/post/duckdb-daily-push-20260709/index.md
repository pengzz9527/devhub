---
title: "📊 DuckDB 实战笔记｜2026-07-09：ATTACH — 无需 ETL，直接跨文件/数据库关联查询"
description: "每天一个 DuckDB 实战技巧。今天教你用 DuckDB 的 ATTACH 功能，把多个数据源连在一起查，告别繁琐的 ETL 流程。"
date: 2026-07-09
tags: ["DuckDB", "ATTACH", "跨数据库查询", "SQL", "实战"]
categories: ["DuckDB 实战笔记"]
toc: false
---

# 📊 DuckDB 实战笔记 ｜ 2026-07-09

> **每天一个 DuckDB 实战技巧，让你立刻能用。**

---

## 🔥 今日话题：ATTACH — 无需 ETL，直接跨文件/数据库关联查询

你有没有遇到过这种场景：

> 客户数据在 PostgreSQL 里，订单数据在 MySQL 里，用户行为日志是 Parquet 文件。老板要一份「客户 × 订单 × 行为」的综合报表。

传统做法是什么？写 ETL 脚本 → 抽取 → 转换 → 加载到一个中间库 → 再跑分析查询。三四个步骤，代码几十行，维护成本越来越高。

**用 DuckDB 的 ATTACH 功能，你不需要任何 ETL 流程。一条 SQL，直接跨 PostgreSQL、MySQL、Parquet、CSV 做 JOIN。**

---

## 📋 场景：跨数据源综合分析

假设你有三个数据源：

1. **PostgreSQL 数据库** `customers.db` — 客户信息
2. **CSV 文件** `orders.csv` — 订单记录
3. **Parquet 文件** `events.parquet` — 用户行为日志

你想回答这个问题：**"每个城市的活跃客户有多少订单，产生了多少次页面浏览？"**

---

## 💡 第一步：ATTACH 外部数据源

```sql
-- 附加 PostgreSQL 数据库
ATTACH 'postgresql://user:***@localhost:5432/customers_db' AS pg_db;

-- 附加 CSV 文件（自动检测 schema）
ATTACH 'orders.csv' AS csv_orders (TYPE CSV);

-- 附加 Parquet 文件
ATTACH 'events.parquet' AS parquet_events (TYPE PARQUET);
```

**就这么简单。** DuckDB 现在"看到"了这三个数据源，可以像操作本地表一样操作它们。

---

## 💡 第二步：跨数据源 JOIN

```sql
SELECT
    c.city,
    COUNT(DISTINCT c.customer_id) AS active_customers,
    COUNT(o.order_id) AS total_orders,
    SUM(e.page_views) AS total_page_views
FROM pg_db.public.customers c
LEFT JOIN csv_orders o ON c.customer_id = o.customer_id
LEFT JOIN parquet_events e ON c.customer_id = e.customer_id
GROUP BY c.city
ORDER BY total_orders DESC;
```

**核心亮点：**

| 特性 | 说明 |
|------|------|
| `pg_db.public.customers` | 直接引用 PostgreSQL 中的表 |
| `csv_orders` | 直接引用 CSV 文件中的数据 |
| `parquet_events` | 直接引用 Parquet 文件中的数据 |
| **JOIN 在 DuckDB 引擎内完成** | 数据拉取和关联全部由 DuckDB 优化 |

---

## 💡 第三步：ATTACH SQLite 数据库

SQLite 也是常见场景——很多工具链输出 SQLite 文件：

```sql
-- 附加 SQLite 数据库
ATTACH '/data/analytics.db' AS sqlite_analytics;

-- 直接查询 SQLite 中的表
SELECT * FROM sqlite_analytics.sessions
WHERE session_date > DATE('now', '-7 days');
```

---

## 💡 第四步：ATTACH HTTP/HTTPS 远程文件

DuckDB 甚至可以直接从 URL 读取数据：

```sql
-- 附加远程 CSV
ATTACH 'https://example.com/data/sales.csv' AS remote_csv (TYPE CSV);

-- 附加远程 Parquet
ATTACH 'https://example.com/data/events.parquet' AS remote_parquet (TYPE PARQUET);

-- 直接查询远程数据
SELECT * FROM remote_csv WHERE amount > 1000;
```

**不需要下载文件到本地！** DuckDB 直接在内存中流式处理远程数据。

---

## 💡 第五步：ATTACH DuckDB 数据库文件

同一个生态内的互操作性：

```sql
-- 附加另一个 DuckDB 数据库
ATTACH '/data/archive.db' AS archive;

-- 跨 DuckDB 数据库查询
SELECT a.*, b.revenue
FROM main.orders a
JOIN archive.customers b ON a.customer_id = b.id;
```

---

## 🚀 实战案例：完整的跨源分析

让我们看一个更真实的例子。假设你要做一个**电商全链路分析**：

```sql
-- 1. 附加所有数据源
ATTACH 'postgresql://analytics:***@db.internal:5432/shop' AS shop;
ATTACH 'warehouse.csv' AS warehouse (TYPE CSV);
ATTACH 'clickstream.parquet' AS clickstream (TYPE PARQUET);

-- 2. 执行全链路分析
WITH customer_orders AS (
    SELECT
        s.customer_id,
        s.name,
        s.city,
        COUNT(o.order_id) AS order_count,
        SUM(o.amount) AS total_spent
    FROM shop.public.customers s
    LEFT JOIN shop.public.orders o ON s.customer_id = o.customer_id
    GROUP BY s.customer_id, s.name, s.city
),
customer_clicks AS (
    SELECT
        customer_id,
        COUNT(*) AS page_views,
        COUNT(DISTINCT session_id) AS sessions
    FROM clickstream
    GROUP BY customer_id
),
product_stock AS (
    SELECT
        product_id,
        SUM(quantity) AS available_stock
    FROM warehouse
    WHERE status = 'in_stock'
    GROUP BY product_id
)
SELECT
    co.city,
    COUNT(co.customer_id) AS customers,
    SUM(co.order_count) AS orders,
    SUM(co.total_spent) AS revenue,
    SUM(cc.page_views) AS total_page_views,
    AVG(cc.page_views) AS avg_page_views_per_customer
FROM customer_orders co
LEFT JOIN customer_clicks cc ON co.customer_id = cc.customer_id
GROUP BY co.city
ORDER BY revenue DESC;
```

**结果：** 一张表汇总了 PostgreSQL 的交易数据 + Parquet 的行为数据 + CSV 的库存数据，**全程零 ETL**。

---

## ⚠️ 注意事项

### 1. 连接字符串格式

不同数据源的 ATTACH 语法略有差异：

| 数据源 | ATTACH 语法 |
|--------|-------------|
| SQLite | `ATTACH 'path/to/db.sqlite' AS alias;` |
| PostgreSQL | `ATTACH 'postgresql://host:***@localhost:5432/dbname' AS alias;` |
| MySQL | `ATTACH 'mysql://host:***@localhost:3306/dbname' AS alias;` |
| CSV | `ATTACH 'file.csv' AS alias (TYPE CSV);` |
| Parquet | `ATTACH 'file.parquet' AS alias (TYPE PARQUET);` |
| JSON | `ATTACH 'file.json' AS alias (TYPE JSON);` |

### 2. READ_ONLY 模式

对于外部数据库，建议加上 `READ_ONLY` 防止意外写入：

```sql
ATTACH 'postgresql://user:***@localhost:5432/shop' AS shop (READ_ONLY);
```

### 3. DETACH 清理

用完之后记得断开连接：

```sql
DETACH shop;
DETACH warehouse;
DETACH clickstream;
```

---

## 🐍 在 Python 中使用

```python
import duckdb

# 创建连接
con = duckdb.connect()

# 附加外部数据源
con.execute("""
    ATTACH 'postgresql://user:***@localhost:5432/shop' AS shop (READ_ONLY);
    ATTACH 'orders.csv' AS orders (TYPE CSV, HEADER true);
    ATTACH 'events.parquet' AS events (TYPE PARQUET);
""")

# 跨源查询
result = con.execute("""
    SELECT
        shop.public.customers.city,
        COUNT(orders.order_id) AS order_count,
        COUNT(events.event_id) AS event_count
    FROM shop.public.customers
    LEFT JOIN orders ON shop.public.customers.id = orders.customer_id
    LEFT JOIN events ON shop.public.customers.id = events.customer_id
    GROUP BY shop.public.customers.city
""").df()

print(result)

# 清理
con.execute("DETACH shop")
con.execute("DETACH orders")
con.execute("DETACH events")
```

---

## 🧠 ATTACH vs 传统 ETL 方案对比

| 维度 | ATTACH 方案 | 传统 ETL 方案 |
|------|-------------|---------------|
| 开发时间 | 几分钟（一条 SQL） | 几小时到几天 |
| 代码量 | 1 条 SQL | ETL 脚本 + 调度 + 监控 |
| 数据延迟 | 实时（直连源库） | 批量/定时同步 |
| 维护成本 | 几乎为零 | 高（管道、错误处理、重试） |
| 适用场景 | 即席分析、临时报表 | 大规模生产数据仓库 |
| 安全性 | 需管理连接凭据 | 可在隔离环境中运行 |

**ATTACH 不是要取代数据仓库，而是让你在需要快速分析时，不必先建一套 ETL 管道。**

---

## 📝 小结

| 能力 | 一句话总结 |
|------|-----------|
| 跨数据库 JOIN | `ATTACH` 后直接用 `alias.table` 引用 |
| 文件直读 | CSV、Parquet、JSON 无需导入 |
| 远程数据 | 直接从 HTTP/HTTPS URL 读取 |
| 按需拉取 | 只拉取需要的数据块，不加载全量 |
| 零 ETL | 一条 SQL 完成多源关联分析 |

**DuckDB 的 ATTACH 功能让你：数据在哪里，就在哪里查。不需要搬移数据。**

---

## 💬 互动

你的工作中有哪些数据分散在不同系统里的场景？留言告诉我，我们一起看看用 ATTACH 怎么优雅解决！

---

*📌 收藏这条笔记，下次面对多数据源分析任务时直接回来参考。*

---

*© 2026 DuckDB 实战笔记 ｜ 每天进步一点点*
