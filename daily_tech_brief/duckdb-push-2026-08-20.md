# DuckDB 实战笔记 · 每日推送 · 2026-08-20

## 今日主题：聚合函数进阶 — STRING_AGG、ARRAY_AGG、MAP_AGG

**一句话总结：** 把多行数据合并成一行，用聚合函数比写循环优雅 100 倍。

---

### 🔥 核心技巧

**1. STRING_AGG — 合并成逗号分隔字符串**
```sql
SELECT customer_id, STRING_AGG(product, ', ') AS products
FROM order_items GROUP BY customer_id;
```

**2. 排序后拼接（ORDER BY 在 STRING_AGG 里）**
```sql
SELECT customer_id,
       STRING_AGG(product, ', ' ORDER BY price DESC) AS top_products
FROM order_items GROUP BY customer_id;
```

**3. ARRAY_AGG — 合并成数组（适合后续处理）**
```sql
SELECT customer_id,
       ARRAY_AGG(product) AS products,
       ARRAY_LENGTH(ARRAY_AGG(product)) AS count
FROM order_items GROUP BY customer_id;
```

**4. MAP_AGG — 合并成键值对**
```sql
SELECT customer_id,
       MAP_AGG(product, price) AS product_prices
FROM order_items GROUP BY customer_id;
```

---

### 💡 实战场景

**场景 1：用户标签聚合**
```sql
-- 每个用户的标签用顿号分隔
SELECT name, STRING_AGG(tag, '、') AS tags
FROM user_tags GROUP BY name;
-- Alice   → VIP、高消费、活跃用户
-- Bob     → 新用户、电子产品
```

**场景 2：跨表聚合（订单日期 + 金额）**
```sql
SELECT o.customer_id,
       STRING_AGG(DATE_FORMAT(o.order_date, '%m-%d'), ', ') AS order_dates,
       SUM(oi.price) AS total_spent
FROM orders o JOIN order_items oi ON o.order_id = oi.order_id
GROUP BY o.customer_id;
```

**场景 3：生成 JSON 报告**
```sql
SELECT customer_id,
       ROW_TO_JSON(STRUCT(
         customer_id,
         STRING_AGG(product, ', ') AS products,
         SUM(price) AS total_amount,
         COUNT(*) AS item_count
       )) AS report
FROM order_items GROUP BY customer_id;
```

---

### 🧠 函数选择指南

| 需要输出 | 用哪个函数 |
|---------|-----------|
| 逗号分隔的字符串（展示用） | `STRING_AGG` |
| 数组（代码里进一步处理） | `ARRAY_AGG` |
| 键值对映射 | `MAP_AGG` |

---

### 📝 完整示例

```sql
-- 订单商品汇总：每个客户买了什么、花了多少
SELECT
    customer_id,
    STRING_AGG(product, ', ') AS products,           -- 商品列表
    ARRAY_AGG(price) AS prices,                       -- 价格数组
    MAP_AGG(product, price) AS price_map,             -- 价格映射
    SUM(price) AS total,                              -- 总金额
    COUNT(*) AS items                                 -- 商品数
FROM order_items
GROUP BY customer_id
ORDER BY total DESC;
```

---

### 🎯 今天带走的一句话

> **聚合函数不只是 SUM/COUNT。STRING_AGG、ARRAY_AGG、MAP_AGG 让你把多行变一行，告别 Python 循环拼接。**

---

📌 完整文章：/duckdb-实战笔记2026-08-20聚合函数进阶-string_aggarray_aggmap_agg-一行搞定复杂聚合/
