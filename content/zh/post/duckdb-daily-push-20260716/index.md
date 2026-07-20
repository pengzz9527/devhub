---
title: "📊 DuckDB 实战笔记｜2026-07-16：MERGE INTO — 一行 SQL 实现 UPSERT"
description: "每天一个 DuckDB 实战技巧。今天教你用 DuckDB 的 MERGE INTO 语句，优雅地实现插入或更新（UPSERT），告别繁琐的条件判断。"
date: 2026-07-16
tags: ["DuckDB", "MERGE", "UPSERT", "数据同步", "SQL", "实战"]
categories: ["DuckDB 实战笔记"]
toc: false
---

# 📊 DuckDB 实战笔记 ｜ 2026-07-16

> **每天一个 DuckDB 实战技巧，让你立刻能用。**

---

## 🔥 今日话题：MERGE INTO — 一行 SQL 实现 UPSERT

你有没有遇到过这种场景：

> 每天从 API 拉取一批用户数据，需要更新到本地数据库。如果用户存在就更新，不存在就插入。

传统做法是什么？先 `SELECT` 查一下是否存在 → 如果存在就 `UPDATE` → 如果不存在就 `INSERT`。三步走，代码十几行，还要处理并发冲突。

**用 DuckDB 的 MERGE INTO，你只需要一条 SQL，自动判断是插入还是更新。**

---

## 📋 场景：用户数据增量同步

假设你有一个用户表 `users`，每天从外部系统同步最新数据：

```sql
CREATE TABLE users(
    user_id INTEGER PRIMARY KEY,
    name VARCHAR,
    email VARCHAR,
    last_login DATE,
    updated_at TIMESTAMP
);

-- 现有数据
INSERT INTO users VALUES
    (1, 'Alice', 'alice@example.com', DATE '2026-07-15', NOW()),
    (2, 'Bob', 'bob@example.com', DATE '2026-07-14', NOW()),
    (3, 'Charlie', 'charlie@example.com', DATE '2026-07-13', NOW());
```

今天你收到一批新数据（可能是 CSV 或另一个表 `new_users`）：

| user_id | name | email | last_login |
|---------|------|-------|------------|
| 1 | Alice Updated | alice_new@example.com | 2026-07-16 |
| 2 | Bob | bob@example.com | 2026-07-16 |
| 4 | Dave | dave@example.com | 2026-07-16 |

**需求：** user_id=1 和 2 已存在，需要更新；user_id=4 不存在，需要插入。

---

## 💡 第一步：基础 MERGE INTO

```sql
MERGE INTO users AS target
USING new_users AS source
ON target.user_id = source.user_id
WHEN MATCHED THEN UPDATE SET
    target.name = source.name,
    target.email = source.email,
    target.last_login = source.last_login,
    target.updated_at = NOW()
WHEN NOT MATCHED THEN INSERT VALUES
    (source.user_id, source.name, source.email, source.last_login, NOW());
```

**就这么简单。** 一条 SQL 完成了：
- ✅ 匹配的记录 → 更新字段
- ✅ 不匹配的记录 → 插入新行

---

## 💡 第二步：条件更新（只更新特定字段）

不是所有字段都需要更新。比如你只想在 `last_login` 有更新时才修改：

```sql
MERGE INTO users AS target
USING new_users AS source
ON target.user_id = source.user_id
WHEN MATCHED AND source.last_login > target.last_login THEN UPDATE SET
    target.last_login = source.last_login,
    target.updated_at = NOW()
WHEN NOT MATCHED THEN INSERT VALUES
    (source.user_id, source.name, source.email, source.last_login, NOW());
```

**注意 `AND source.last_login > target.last_login`** —— 这是条件 MERGE，只有满足条件时才执行更新。

---

## 💡 第三步：删除不匹配的记录

有时候你需要同步整个数据集——源数据里不存在的记录，目标表也要删除：

```sql
MERGE INTO users AS target
USING new_users AS source
ON target.user_id = source.user_id
WHEN MATCHED THEN UPDATE SET
    target.name = source.name,
    target.email = source.email,
    target.last_login = source.last_login,
    target.updated_at = NOW()
WHEN NOT MATCHED THEN INSERT VALUES
    (source.user_id, source.name, source.email, source.last_login, NOW())
WHEN NOT MATCHED BY SOURCE THEN DELETE;  -- ← 新增这一行
```

**`WHEN NOT MATCHED BY SOURCE THEN DELETE`** —— 如果目标表中有记录在源数据中找不到，就删除它。

---

## 💡 第四步：从文件直接 MERGE

实际工作中，新数据通常来自 CSV 或 Parquet 文件。DuckDB 可以直接读取并 MERGE：

```sql
MERGE INTO users AS target
USING read_csv_auto('daily_sync.csv') AS source
ON target.user_id = source.user_id
WHEN MATCHED THEN UPDATE SET
    target.name = source.name,
    target.email = source.email,
    target.last_login = source.last_login,
    target.updated_at = NOW()
WHEN NOT MATCHED THEN INSERT VALUES
    (source.user_id, source.name, source.email, source.last_login, NOW());
```

**不需要先把 CSV 加载到临时表！** DuckDB 直接在内存中流式处理。

---

## 🚀 实战案例：电商订单增量同步

更真实的场景——订单表每天同步，需要处理状态变更：

```sql
-- 创建订单表
CREATE TABLE orders(
    order_id INTEGER PRIMARY KEY,
    customer_id INTEGER,
    status VARCHAR,
    total DOUBLE,
    updated_at TIMESTAMP
);

-- 模拟已有订单
INSERT INTO orders VALUES
    (1001, 1, 'completed', 5999.00, NOW()),
    (1002, 2, 'pending', 399.00, NOW()),
    (1003, 1, 'shipped', 2499.00, NOW());

-- 模拟新同步的数据（CSV 内容）
CREATE TABLE new_orders(order_id INTEGER, customer_id INTEGER, status VARCHAR, total DOUBLE);
INSERT INTO new_orders VALUES
    (1001, 1, 'delivered', 5999.00),   -- 状态变更
    (1002, 2, 'cancelled', 399.00),     -- 状态变更
    (1004, 3, 'pending', 1200.00);       -- 新订单

-- 执行 MERGE
MERGE INTO orders AS target
USING new_orders AS source
ON target.order_id = source.order_id
WHEN MATCHED THEN UPDATE SET
    target.status = source.status,
    target.total = source.total,
    target.updated_at = NOW()
WHEN NOT MATCHED THEN INSERT VALUES
    (source.order_id, source.customer_id, source.status, source.total, NOW());

-- 查看结果
SELECT * FROM orders ORDER BY order_id;
```

**结果：**

| order_id | customer_id | status | total | updated_at |
|----------|-------------|--------|-------|------------|
| 1001 | 1 | delivered | 5999.00 | [更新后的时间] |
| 1002 | 2 | cancelled | 399.00 | [更新后的时间] |
| 1003 | 1 | shipped | 2499.00 | [原始时间] |
| 1004 | 3 | pending | 1200.00 | [新插入的时间] |

**一条 SQL，三个订单更新，一个新订单插入，全部搞定。**

---

## 🐍 在 Python 中使用

```python
import duckdb
from datetime import datetime

# 连接 DuckDB
con = duckdb.connect(":memory:")

# 创建示例数据
con.execute("""
CREATE TABLE users(
    user_id INTEGER PRIMARY KEY,
    name VARCHAR,
    email VARCHAR,
    last_login DATE,
    updated_at TIMESTAMP
)
""")

con.execute("""
INSERT INTO users VALUES
    (1, 'Alice', 'alice@example.com', DATE '2026-07-15', ?),
    (2, 'Bob', 'bob@example.com', DATE '2026-07-14', ?)
""", [datetime.now(), datetime.now()])

# 准备新数据
new_users = [
    (1, 'Alice Updated', 'alice_new@example.com', '2026-07-16'),
    (2, 'Bob', 'bob@example.com', '2026-07-16'),
    (4, 'Dave', 'dave@example.com', '2026-07-16'),
]

# 创建临时表并插入
con.execute("CREATE TEMP TABLE new_users(user_id INTEGER, name VARCHAR, email VARCHAR, last_login DATE)")
con.executemany("INSERT INTO new_users VALUES (?, ?, ?, ?)", new_users)

# 执行 MERGE
con.execute("""
MERGE INTO users AS target
USING new_users AS source
ON target.user_id = source.user_id
WHEN MATCHED THEN UPDATE SET
    target.name = source.name,
    target.email = source.email,
    target.last_login = source.last_login,
    target.updated_at = CURRENT_TIMESTAMP
WHEN NOT MATCHED THEN INSERT VALUES
    (source.user_id, source.name, source.email, source.last_login, CURRENT_TIMESTAMP)
""")

# 查看结果
result = con.execute("SELECT * FROM users ORDER BY user_id").fetchdf()
print(result)
```

**核心优势：** 不需要先 `SELECT` 再判断，不需要循环逐条处理。DuckDB 内部优化了 MERGE 的执行计划，大数据量下性能远超 Python 循环。

---

## 🧠 MERGE INTO 语法拆解

```
MERGE INTO target_table AS target
USING source_data AS source
ON target.key = source.key          -- 匹配条件
WHEN MATCHED THEN UPDATE SET        -- 匹配时的操作
    target.col1 = source.col1,
    target.col2 = source.col2
WHEN NOT MATCHED THEN INSERT        -- 不匹配时的操作
    VALUES (source.col1, source.col2)
WHEN NOT MATCHED BY SOURCE THEN DELETE  -- 可选：反向删除
```

**关键点：**

| 子句 | 说明 |
|------|------|
| `ON ...` | 定义匹配条件，通常是主键或唯一键 |
| `WHEN MATCHED THEN UPDATE SET` | 匹配成功时更新哪些字段 |
| `WHEN NOT MATCHED THEN INSERT` | 不匹配时插入新行 |
| `WHEN NOT MATCHED BY SOURCE THEN DELETE` | 可选，反向同步删除 |
| `AND condition` | 可选，给 UPDATE 加条件过滤 |

---

## 📝 三种数据同步方案对比

| 方案 | 代码量 | 性能 | 可读性 | 并发安全 |
|------|--------|------|--------|----------|
| **MERGE INTO** | 1 条 SQL | ⭐⭐⭐ 优秀 | ⭐⭐⭐ 高 | ✅ 原子操作 |
| SELECT + IF ELSE | 10+ 行 Python | ⭐ 低（循环） | ⭐⭐ 中 | ❌ 需锁 |
| INSERT ON CONFLICT | 1 条 SQL | ⭐⭐ 良好 | ⭐⭐⭐ 高 | ✅ 原子操作 |

**MERGE INTO vs INSERT ON CONFLICT：**
- `INSERT ON CONFLICT` 只能处理"存在则更新"的场景
- `MERGE INTO` 更灵活，支持条件更新、反向删除等复杂逻辑
- 如果需要同时处理"更新"和"插入"，MERGE INTO 是更好的选择

---

## 📝 小结

| 能力 | 一句话总结 |
|------|-----------|
| UPSERT | `MERGE INTO` 一行搞定插入或更新 |
| 条件更新 | `WHEN MATCHED AND condition THEN UPDATE` |
| 反向同步 | `WHEN NOT MATCHED BY SOURCE THEN DELETE` |
| 文件直读 | `USING read_csv_auto('file.csv')` 直接 MERGE |
| 原子操作 | 整个 MERGE 是一个事务，要么全成功要么全失败 |

**DuckDB 的 MERGE INTO 让你：数据同步不再需要写复杂的条件判断逻辑，一条 SQL 解决。**

---

## 💬 互动

你的项目中有没有"增量同步"的场景？留言告诉我，我们一起看看用 MERGE INTO 怎么优雅解决！

---

*📌 收藏这条笔记，下次做数据同步任务时直接回来参考。*

---

*© 2026 DuckDB 实战笔记 ｜ 每天进步一点点*
