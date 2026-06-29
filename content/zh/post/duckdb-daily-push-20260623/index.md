---
title: "📊 DuckDB 实战笔记｜2026-06-23：用 DuckDB 一行代码清洗脏 CSV 数据"
description: "每天一个 DuckDB 实战技巧。今天教你如何用 SQL 快速清洗脏 CSV 数据，告别繁琐的 Python 数据处理代码。"
date: 2026-06-23
tags: ["DuckDB", "CSV", "数据清洗", "SQL", "实战"]
categories: ["DuckDB 实战笔记"]
toc: false
---

# 📊 DuckDB 实战笔记 ｜ 2026-06-23

> **每天一个 DuckDB 实战技巧，让你立刻能用。**

---

## 🔥 今日话题：用 DuckDB 一行 SQL 清洗脏 CSV 数据

你是不是也遇到过这种场景：

老板甩给你一个 CSV 文件，里面全是脏数据——有空值、格式混乱、列名乱七八糟。你打开 Python，写了 50 行 Pandas 代码，跑了半天，结果还是不对……

**用 DuckDB，一条 SQL 就能搞定。**

---

## 📋 问题场景

假设你有一个员工数据 CSV `employees.csv`：

```csv
name,age,salary,department
"Alice",30,85000.00,Engineering
"Bob",,72000.50,Sales
"Charlie","28",65000,Marketing
"Diana",35,,Engineering
"",42,91000,Sales
"Eve","not_a_number",55000,HR
"Frank",25,abc,Marketing
"Grace",33,78000.00,
```

问题：
- `age` 列有字符串 `"28"` 和 `"not_a_number"`
- `salary` 列有缺失值和 `"abc"` 这样的非法字符串
- `name` 有空字符串
- `department` 有缺失值

**传统做法：** 写一堆 Pandas 清洗代码，调试半天。

**DuckDB 做法：** 一条 SQL，清晰可读，直接出结果。

---

## 💡 解决方案

```sql
SELECT
    CASE
        WHEN TRIM(name) = '' OR name IS NULL THEN 'Unknown'
        ELSE name
    END AS name,

    -- 年龄：尝试转整数，失败则设为 NULL
    TRY_CAST(
        REGEXP_REPLACE(age, '[^0-9]', '', 'g') AS INTEGER
    ) AS age,

    -- 薪资：尝试转数值，失败则设为 NULL
    TRY_CAST(
        REGEXP_REPLACE(salary, '[^0-9.]', '', 'g') AS DOUBLE
    ) AS salary,

    COALESCE(TRIM(department), 'Unassigned') AS department

FROM read_csv_auto('employees.csv');
```

**结果：**

| name | age | salary | department |
|------|-----|--------|------------|
| Alice | 30 | 85000.0 | Engineering |
| Bob | NULL | 72000.5 | Sales |
| Charlie | 28 | 65000.0 | Marketing |
| Diana | 35 | NULL | Engineering |
| Unknown | 42 | 91000.0 | Sales |
| Eve | NULL | 55000.0 | HR |
| Frank | 25 | NULL | Marketing |
| Grace | 33 | 78000.0 | Unassigned |

---

## 🧠 关键函数解析

### `TRY_CAST(value AS type)`
**这是 DuckDB 的杀手锏。** 普通 `CAST` 遇到无法转换的值会报错中断整个查询。`TRY_CAST` 则优雅地返回 `NULL`，不会崩溃。

```sql
-- 普通 CAST：遇到 "abc" 直接报错
SELECT CAST('abc' AS INTEGER);
-- ERROR: Could not convert string 'abc' to integer

-- TRY_CAST：返回 NULL
SELECT TRY_CAST('abc' AS INTEGER);
-- NULL
```

### `REGEXP_REPLACE(str, pattern, replacement, flags)`
正则替换，清洗非数字字符：
- `[^0-9]` — 匹配所有非数字字符
- `'g'` — 全局替换（去掉所有非数字字符）

### `COALESCE(a, b)`
返回第一个非 NULL 值，填充缺失数据。

### `TRIM(str)`
去除前后空格。

---

## 🚀 进阶：直接写入清洗后的文件

清洗完数据后，你可以直接导出为新的 CSV：

```sql
COPY (
    SELECT
        CASE
            WHEN TRIM(name) = '' OR name IS NULL THEN 'Unknown'
            ELSE name
        END AS name,
        TRY_CAST(REGEXP_REPLACE(age, '[^0-9]', '', 'g') AS INTEGER) AS age,
        TRY_CAST(REGEXP_REPLACE(salary, '[^0-9.]', '', 'g') AS DOUBLE) AS salary,
        COALESCE(TRIM(department), 'Unassigned') AS department
    FROM read_csv_auto('employees.csv')
) TO 'employees_cleaned.csv' (HEADER, DELIMITER ',');
```

**就这么简单。** 不需要写循环、不需要异常处理、不需要调试 Pandas 的 inplace 参数。

---

## 🐍 在 Python 中使用

```python
import duckdb

# 直接执行 SQL
result = duckdb.sql("""
    SELECT
        CASE
            WHEN TRIM(name) = '' OR name IS NULL THEN 'Unknown'
            ELSE name
        END AS name,
        TRY_CAST(REGEXP_REPLACE(age, '[^0-9]', '', 'g') AS INTEGER) AS age,
        TRY_CAST(REGEXP_REPLACE(salary, '[^0-9.]', '', 'g') AS DOUBLE) AS salary,
        COALESCE(TRIM(department), 'Unassigned') AS department
    FROM read_csv_auto('employees.csv')
""").df()

print(result)
```

或者直接用 `read_csv_auto` 的内置清洗参数：

```python
import duckdb

df = duckdb.sql("""
    SELECT * FROM read_csv_auto('employees.csv', 
        auto_detect=True,
        columns={
            'name': 'VARCHAR',
            'age': 'INTEGER',
            'salary': 'DOUBLE',
            'department': 'VARCHAR'
        }
    )
""").df()
```

`read_csv_auto` 会自动尝试推断类型并处理部分脏数据。

---

## 📝 小结

| 场景 | DuckDB 方案 | 传统 Pandas 方案 |
|------|-------------|-----------------|
| `TRY_CAST()` | `pd.to_numeric(..., errors='coerce')` |
| `REGEXP_REPLACE()` | `str.replace(regex=True)` |
| `COALESCE()` | `fillna()` |
| `TRIM()` | `str.strip()` |
| **一条 SQL** | 多步 Python 代码 |

**DuckDB 的核心优势：把数据处理变成 SQL。** 你不需要学新的 API，只需要用好 SQL 函数。

---

## 💬 互动

你工作中最常见的脏数据问题是什么？留言告诉我，下期专门写一篇文章解决！

---

*📌 收藏这条笔记，下次遇到脏 CSV 数据时直接回来参考。*

---

*© 2026 DuckDB 实战笔记 ｜ 每天进步一点点*
