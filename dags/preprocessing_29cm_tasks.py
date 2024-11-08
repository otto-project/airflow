# 29cm_preprocessing_task.py

from airflow.hooks.postgres_hook import PostgresHook
import pandas as pd
import re
import random
import json


def fetch_data_from_redshift(**kwargs):
    redshift_hook = PostgresHook(postgres_conn_id="otto_redshift")
    conn = redshift_hook.get_conn()
    sql_product = """
        SELECT product_name, size, category, platform, brand
        FROM otto.product_table
        WHERE platform = '29cm';
    """
    sql_reviews = """
        SELECT product_name, size, height, weight, gender, size_comment
        FROM otto.reviews
        WHERE product_name IN (
            SELECT product_name
            FROM otto.product_table
            WHERE platform = '29cm'
        );
    """

    product_df = pd.read_sql(sql_product, conn)
    reviews_df = pd.read_sql(sql_reviews, conn)

    # Push DataFrames to XCom
    ti = kwargs["ti"]
    ti.xcom_push(key="product_df", value=product_df.to_json())
    ti.xcom_push(key="reviews_df", value=reviews_df.to_json())


def process_data(**kwargs):
    ti = kwargs["ti"]
    product_df_json = ti.xcom_pull(key="product_df")
    reviews_df_json = ti.xcom_pull(key="reviews_df")

    product_df = pd.read_json(product_df_json)
    reviews_df = pd.read_json(reviews_df_json)

    def clean_size_column(size_str):
        size_list_upper = ["XXS", "XS", "S", "M", "L", "XL", "XXL"]
        if isinstance(size_str, str):
            if re.match(r"[가-힣\s]+$", size_str) or "상세" in size_str:
                return "none"
            if (
                size_str.lower() in ["free", "f", "one size"]
                or "chest" in size_str.lower()
            ):
                return ["F"]
            if "~" in size_str:
                pattern = re.compile(r"\b(?:" + "|".join(size_list_upper) + r")\b")
                found_sizes = pattern.findall(size_str.upper())
                if found_sizes:
                    start_size = found_sizes[0]
                    end_size = found_sizes[-1]
                    if start_size in size_list_upper and end_size in size_list_upper:
                        start_index = size_list_upper.index(start_size)
                        end_index = size_list_upper.index(end_size)
                        return size_list_upper[start_index : end_index + 1]
            if "," in size_str:
                size_str = size_str.split(",")
            elif "/" in size_str:
                size_str = size_str.split("/")
            else:
                size_str = ["F"]
        if isinstance(size_str, list):
            cleaned_sizes = []
            for s in size_str:
                s = re.sub(r"\s*\(.*?\)\s*", "", s).strip()
                s = re.split(r"\s+", s, maxsplit=1)[0].strip()
                match = re.search(r"(S|M|L|F)", s)
                if match:
                    s = s[: match.end()].strip()
                cleaned_sizes.append(s)
            size_str = list(dict.fromkeys(cleaned_sizes))
        return size_str

    def select_last_smlf(size_str):
        size_patterns = [
            "3XS",
            "2XS",
            "XXS",
            "XS",
            "S",
            "M",
            "L",
            "XL",
            "XXL",
            "2XL",
            "3XL",
            "F",
        ]
        pattern = re.compile("|".join(size_patterns), re.IGNORECASE)
        size_strip = re.sub(r"\s*\(.*?\)\s*", "", size_str).strip()
        matches = pattern.findall(size_strip)
        if matches:
            size_str = matches[-1].upper()
        else:
            size_str = size_strip
        return size_str

    def convert_size_string_to_list(size_str):
        if isinstance(size_str, str):
            try:
                size_list = eval(size_str)
                if isinstance(size_list, list):
                    return size_list
            except:
                pass
        return []

    size_ranges = {
        "XXXS": {
            "남성": {"height": (140, 150), "weight": (35, 45)},
            "여성": {"height": (130, 140), "weight": (30, 40)},
        },
        "3XS": {
            "남성": {"height": (140, 150), "weight": (35, 45)},
            "여성": {"height": (130, 140), "weight": (30, 40)},
        },
        "XXS": {
            "남성": {"height": (150, 160), "weight": (45, 55)},
            "여성": {"height": (140, 150), "weight": (40, 50)},
        },
        "2XS": {
            "남성": {"height": (150, 160), "weight": (45, 55)},
            "여성": {"height": (140, 150), "weight": (40, 50)},
        },
        "XS": {
            "남성": {"height": (160, 165), "weight": (50, 60)},
            "여성": {"height": (150, 155), "weight": (45, 55)},
        },
        "0": {
            "남성": {"height": (160, 165), "weight": (50, 60)},
            "여성": {"height": (150, 155), "weight": (45, 55)},
        },
        "S": {
            "남성": {"height": (165, 170), "weight": (55, 65)},
            "여성": {"height": (155, 160), "weight": (50, 60)},
        },
        "0.5": {
            "남성": {"height": (165, 170), "weight": (55, 65)},
            "여성": {"height": (155, 160), "weight": (50, 60)},
        },
        "M": {
            "남성": {"height": (170, 175), "weight": (60, 70)},
            "여성": {"height": (160, 165), "weight": (55, 65)},
        },
        "1": {
            "남성": {"height": (170, 175), "weight": (60, 70)},
            "여성": {"height": (160, 165), "weight": (55, 65)},
        },
        "L": {
            "남성": {"height": (175, 180), "weight": (70, 80)},
            "여성": {"height": (165, 170), "weight": (60, 70)},
        },
        "1.5": {
            "남성": {"height": (175, 180), "weight": (70, 80)},
            "여성": {"height": (165, 170), "weight": (60, 70)},
        },
        "XL": {
            "남성": {"height": (180, 185), "weight": (80, 90)},
            "여성": {"height": (170, 175), "weight": (70, 80)},
        },
        "2": {
            "남성": {"height": (180, 185), "weight": (80, 90)},
            "여성": {"height": (170, 175), "weight": (70, 80)},
        },
        "XXL": {
            "남성": {"height": (185, 190), "weight": (90, 100)},
            "여성": {"height": (175, 180), "weight": (80, 90)},
        },
        "2XL": {
            "남성": {"height": (185, 190), "weight": (90, 100)},
            "여성": {"height": (175, 180), "weight": (80, 90)},
        },
        "XXXL": {
            "남성": {"height": (190, 200), "weight": (100, 110)},
            "여성": {"height": (180, 190), "weight": (90, 100)},
        },
        "3XL": {
            "남성": {"height": (190, 200), "weight": (100, 110)},
            "여성": {"height": (180, 190), "weight": (90, 100)},
        },
        "F": {
            "남성": {"height": (165, 185), "weight": (55, 85)},
            "여성": {"height": (155, 175), "weight": (50, 75)},
        },
    }

    def generate_random_value(size, gender, attribute):
        if size in size_ranges and gender in size_ranges[size]:
            min_val, max_val = size_ranges[size][gender][attribute]
        else:
            min_val, max_val = size_ranges["F"][gender][attribute]
        return round(random.uniform(min_val, max_val))

    # Processing product and review data
    product_df["size"] = product_df["size"].apply(clean_size_column)
    reviews_df["size"] = reviews_df["size"].apply(select_last_smlf)
    reviews_df["size_comment"] = reviews_df["size_comment"].apply(
        lambda x: -1 if "작아요" in x else (1 if "커요" in x else 0)
    )

    # Convert size column to lists where needed
    product_df["size"] = product_df["size"].apply(
        lambda x: convert_size_string_to_list(x) if isinstance(x, str) else []
    )

    # Fill empty sizes in the review data based on product sizes
    for index, product_row in product_df.iterrows():
        product_name = product_row["product_name"]
        product_size_list = product_row["size"]

        if not product_size_list:
            product_size_list = []

        review_rows = reviews_df[reviews_df["product_name"] == product_name]

        for review_index, review_row in review_rows.iterrows():
            review_size = review_row["size"]

            if product_size_list:
                if review_size not in product_size_list:
                    reviews_df.at[review_index, "size"] = "none"
            else:
                if pd.notna(review_size) and review_size != "none":
                    product_size_list.append(review_size)

        product_df.at[index, "size"] = (
            str(product_size_list) if product_size_list else None
        )

    # Fill empty sizes with sizes from similar branded products
    for index, product_row in product_df.iterrows():
        if not product_row["size"]:
            brand = product_row["brand"]
            similar_branded_products = product_df[
                (product_df["brand"] == brand) & (product_df["size"].notna())
            ]
            if not similar_branded_products.empty:
                non_empty_size_str = similar_branded_products.iloc[0]["size"]
                product_df.at[index, "size"] = non_empty_size_str
            else:
                product_df.at[index, "size"] = str(["S", "M", "L", "XL"])

    # Replace "none" sizes with actual sizes
    for index, review_row in reviews_df[reviews_df["size"] == "none"].iterrows():
        product_name = review_row["product_name"]
        similar_product = product_df[product_df["product_name"] == product_name]
        if not similar_product.empty:
            size_str = similar_product.iloc[0]["size"]
            size_list = convert_size_string_to_list(size_str)
            if size_list:
                random_size = random.choice(size_list)
                reviews_df.at[index, "size"] = random_size
            else:
                random_size = random.choice(["S", "M", "L", "XL"])
                reviews_df.at[index, "size"] = random_size

    # Update height if it is "none"
    reviews_df.loc[reviews_df["height"] == "none", "height"] = reviews_df.apply(
        lambda row: (
            generate_random_value(row["size"], row["gender"], "height")
            if row["height"] == "none"
            else row["height"]
        ),
        axis=1,
    )

    # Update weight if it is "none"
    reviews_df.loc[reviews_df["weight"] == "none", "weight"] = reviews_df.apply(
        lambda row: (
            generate_random_value(row["size"], row["gender"], "weight")
            if row["weight"] == "none"
            else row["weight"]
        ),
        axis=1,
    )

    # Push processed data back to XCom
    ti.xcom_push(key="processed_product_df", value=product_df.to_json())
    ti.xcom_push(key="processed_reviews_df", value=reviews_df.to_json())


def save_data_to_redshift(**kwargs):
    redshift_hook = PostgresHook(postgres_conn_id="otto_redshift")
    conn = redshift_hook.get_conn()
    cursor = conn.cursor()

    ti = kwargs["ti"]
    processed_product_df_json = ti.xcom_pull(key="processed_product_df")
    processed_reviews_df_json = ti.xcom_pull(key="processed_reviews_df")

    processed_product_df = pd.read_json(processed_product_df_json)
    processed_reviews_df = pd.read_json(processed_reviews_df_json)

    # Ensure tables exist and use schema and table names as specified
    cursor.execute(
        """
        DROP TABLE IF EXISTS otto."29cm_product" CASCADE;
        CREATE TABLE IF NOT EXISTS otto."29cm_product" (
            product_name TEXT,
            size TEXT,
            category TEXT,
            platform TEXT,
            brand TEXT
        );
        """
    )

    cursor.execute(
        """
        DROP TABLE IF EXISTS otto."29cm_reviews" CASCADE;
        CREATE TABLE IF NOT EXISTS otto."29cm_reviews" (
            product_name TEXT,
            size TEXT,
            height NUMERIC,
            weight NUMERIC,
            gender TEXT,
            size_comment TEXT
        );
        """
    )

    # Insert data into 29cm_product table
    for _, row in processed_product_df.iterrows():
        cursor.execute(
            """
            INSERT INTO otto."29cm_product" (product_name, size, category, platform, brand)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                row["product_name"],
                json.dumps(row["size"]),
                row["category"],
                row["platform"],
                row["brand"],
            ),
        )

    # Insert data into 29cm_reviews table
    for _, row in processed_reviews_df.iterrows():
        cursor.execute(
            """
            INSERT INTO otto."29cm_reviews" (product_name, size, height, weight, gender, size_comment)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                row["product_name"],
                row["size"],
                row["height"],
                row["weight"],
                row["gender"],
                row["size_comment"],
            ),
        )

    conn.commit()
    cursor.close()
    conn.close()
