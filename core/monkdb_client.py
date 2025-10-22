"""
MonkDB Client Module
Production-ready wrapper for MonkDB native client.
Handles all database operations for the agent system.
"""

import logging
from typing import List, Dict, Any, Optional
import monkdb.client
import pandas as pd
import monkdb

try:
    # Try to import MonkDB native client
    from monkdb import connect
    MONKDB_AVAILABLE = True
except ImportError:
    # Fallback to psycopg2 if monkdb not available
    import psycopg2
    from psycopg2 import pool
    MONKDB_AVAILABLE = False

logger = logging.getLogger(__name__)


class MonkDBClient:
    """
    Production-grade MonkDB client with connection management,
    error handling, and comprehensive CRUD operations.

    Supports both MonkDB native client and PostgreSQL compatibility mode.
    """

    def __init__(self, host: str, port: int, user: str,
                 password: str, schema: str = "monkdb"):
        """
        Initialize MonkDB client.

        Args:
            host: MonkDB server hostname
            port: MonkDB API port (default: 4200)
            user: Database user
            password: Database password
            schema: Database schema/database name (default: monkdb)
        """
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.schema = schema
        self.connection = None
        self.cursor = None

        # Initialize connection
        self._connect()

    def _connect(self):
        """Establish connection to MonkDB."""
        try:
            if MONKDB_AVAILABLE:
                # Use native MonkDB client
                logger.info(
                    f"🔌 Connecting to MonkDB (native) at {self.host}:{self.port}...")
                connection_string = f"monkdb://{self.user}:{self.password}@{self.host}:{self.port}/{self.schema}"
                self.connection = connect(connection_string)
                self.cursor = self.connection.cursor()
                logger.info(f"✅ MonkDB native connection established")
            else:
                # Use PostgreSQL-compatible mode
                logger.info(
                    f"🔌 Connecting to MonkDB (PostgreSQL mode) at {self.host}:{self.port}...")
                self.connection = monkdb.client.connect(
                    f"http://{self.user}:{self.password}@{self.host}:{self.port}",
                    username=self.user,
                    password=self.password,
                    schema=self.schema
                )

                self.cursor = self.connection.cursor()
                logger.info(f"✅ MonkDB PostgreSQL connection established")
        except Exception as e:
            logger.error(f"❌ Failed to connect to MonkDB: {e}")
            # Try fallback connection
            self._fallback_connect()

    def _fallback_connect(self):
        """Fallback connection method."""
        try:
            logger.info("⚠️ Trying fallback connection method...")
            import psycopg2
            self.connection = psycopg2.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                dbname=self.schema,
                connect_timeout=10
            )
            self.cursor = self.connection.cursor()
            logger.info("✅ Fallback connection successful")
        except Exception as e:
            logger.error(f"❌ All connection methods failed: {e}")
            raise ConnectionError(
                f"Cannot connect to MonkDB at {self.host}:{self.port}")

    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check on MonkDB server.

        Returns:
            Dict with status and message
        """
        try:
            if not self.cursor:
                self._connect()

            self.cursor.execute("SELECT 1")
            result = self.cursor.fetchone()

            if result and result[0] == 1:
                logger.info("✅ MonkDB health check: OK")
                return {"status": "ok", "message": "Database is healthy"}
            else:
                return {"status": "error", "message": "Unexpected response"}
        except Exception as e:
            logger.error(f"❌ Health check failed: {e}")
            return {"status": "error", "message": str(e)}

    def get_server_version(self) -> str:
        """
        Get MonkDB server version.

        Returns:
            Server version string
        """
        try:
            self.cursor.execute("SELECT version()")
            version = self.cursor.fetchone()[0]
            logger.info(f"MonkDB version: {version}")
            return version
        except Exception as e:
            logger.error(f"❌ Failed to get version: {e}")
            return f"Error: {e}"

    def create_table_if_not_exists(self, table_name: str = "products") -> bool:
        """
        Create products table if it doesn't exist.

        Args:
            table_name: Name of the table to create

        Returns:
            True if successful, False otherwise
        """
        # Try without schema prefix first
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            product_id        BIGINT PRIMARY KEY,
            style_id          INTEGER,
            title             TEXT,
            brand             TEXT,
            price             DOUBLE PRECISION,
            mrp               DOUBLE PRECISION,
            discount_percent  DOUBLE PRECISION,
            rating            REAL,
            rating_total      INTEGER,
            img_primary       TEXT,
            img_count         INTEGER,
            created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """

        try:
            self.cursor.execute(create_table_sql)
            self.connection.commit()
            logger.info(f"✅ Table {table_name} created/verified")
            return True
        except Exception as e:
            logger.warning(f"⚠️ First attempt failed: {e}")
            # Try with schema prefix
            try:
                create_table_sql_with_schema = f"""
                CREATE TABLE IF NOT EXISTS {self.schema}.{table_name} (
                    product_id        BIGINT PRIMARY KEY,
                    style_id          INTEGER,
                    title             TEXT,
                    brand             TEXT,
                    price             DOUBLE PRECISION,
                    mrp               DOUBLE PRECISION,
                    discount_percent  DOUBLE PRECISION,
                    rating            REAL,
                    rating_total      INTEGER,
                    img_primary       TEXT,
                    img_count         INTEGER,
                    created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
                self.cursor.execute(create_table_sql_with_schema)
                self.connection.commit()
                logger.info(
                    f"✅ Table {self.schema}.{table_name} created/verified")
                return True
            except Exception as e2:
                logger.error(f"❌ Failed to create table: {e2}")
                return False

    def list_tables(self) -> List[str]:
        """
        List all tables in the database.

        Returns:
            List of table names
        """
        queries = [
            # Standard PostgreSQL information_schema
            """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
            """,
            # Alternative query
            """
            SELECT tablename 
            FROM pg_tables 
            WHERE schemaname = 'public'
            """,
            # Simple query for all tables
            """
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_type = 'BASE TABLE'
            """
        ]

        for query in queries:
            try:
                self.cursor.execute(query)
                tables = [row[0] for row in self.cursor.fetchall()]
                logger.info(f"Found {len(tables)} tables")
                return tables
            except Exception as e:
                logger.debug(f"Query failed, trying next: {e}")
                continue

        logger.warning("❌ All list_tables queries failed")
        return []

    def insert_products_from_csv(self, csv_path: str, table_name: str = "products") -> Dict[str, Any]:
        """
        Insert products from CSV file in batches, handling errors gracefully.
        """
        try:
            # Read CSV
            df = pd.read_csv(csv_path)
            logger.info(f"📊 Read {len(df)} rows from {csv_path}")

            # Validate required columns
            required_cols = ['product_id', 'title', 'brand', 'price']
            missing_cols = [
                col for col in required_cols if col not in df.columns]
            if missing_cols:
                raise ValueError(f"Missing required columns: {missing_cols}")

            # Fill missing data
            df = df.fillna({
                'style_id': 0,
                'mrp': 0.0,
                'discount_percent': 0.0,
                'rating': 0.0,
                'rating_total': 0,
                'img_primary': '',
                'img_count': 0
            })

            # Convert to list of dicts
            records = df.to_dict('records')

            inserted_count = 0
            batch_size = 1000
            batch = []

            for idx, record in enumerate(records):
                try:
                    # Cast and sanitize data
                    product_id = int(record['product_id'])
                    style_id = int(record.get('style_id', 0))
                    title = str(record['title']).replace("'", "''")
                    brand = str(record['brand']).replace("'", "''")
                    price = float(record['price'])
                    mrp = float(record.get('mrp', 0.0))
                    discount_percent = float(
                        record.get('discount_percent', 0.0))
                    rating = float(record.get('rating', 0.0))
                    rating_total = int(record.get('rating_total', 0))
                    img_primary = str(record.get(
                        'img_primary', '')).replace("'", "''")
                    img_count = int(record.get('img_count', 0))
                except Exception as e:
                    logger.warning(
                        f"Data casting error for record {record.get('product_id')}: {e}")
                    continue

                # Append value string for insertion
                value_str = f"({product_id}, {style_id}, '{title}', '{brand}', {price}, {mrp}, {discount_percent}, {rating}, {rating_total}, '{img_primary}', {img_count})"
                batch.append(value_str)

                # Execute batch when reaching batch_size
                if len(batch) >= batch_size or idx == len(records) - 1:
                    sql_insert = f"""
                    INSERT INTO {table_name} (
                        product_id, style_id, title, brand, price, mrp, discount_percent,
                        rating, rating_total, img_primary, img_count
                    ) VALUES {', '.join(batch)}
                    ON CONFLICT (product_id) DO UPDATE SET
                        title = EXCLUDED.title,
                        brand = EXCLUDED.brand,
                        price = EXCLUDED.price,
                        mrp = EXCLUDED.mrp,
                        discount_percent = EXCLUDED.discount_percent,
                        rating = EXCLUDED.rating,
                        rating_total = EXCLUDED.rating_total,
                        img_primary = EXCLUDED.img_primary,
                        img_count = EXCLUDED.img_count,
                        updated_at = CURRENT_TIMESTAMP
                    """
                    try:
                        self.cursor.execute(sql_insert)
                        self.connection.commit()
                        inserted_count += len(batch)
                        logger.info(f"📥 Batch inserted: {len(batch)} rows")
                    except Exception as e:
                        logger.error(f"❌ Batch insertion error: {e}")
                        self.connection.rollback()
                    finally:
                        batch.clear()

            result = {
                "status": "success",
                "file": csv_path,
                "total_rows": len(df),
                "inserted": inserted_count,
                "message": f"Successfully processed {inserted_count} products"
            }
            logger.info(f"✅ {result['message']}")
            return result

        except Exception as e:
            logger.error(f"❌ Failed to insert products: {e}")
            try:
                self.connection.rollback()
            except:
                pass
            return {
                "status": "error",
                "file": csv_path,
                "message": str(e)
            }

    def execute_query(self, query: str, params: Optional[tuple] = None) -> pd.DataFrame:
        """
        Execute SELECT query and return results as DataFrame.

        Args:
            query: SQL query
            params: Query parameters

        Returns:
            Query results as DataFrame
        """
        try:
            if params:
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(query)

            # Fetch all results
            rows = self.cursor.fetchall()

            # Get column names from cursor description
            if self.cursor.description:
                columns = [desc[0] for desc in self.cursor.description]
                df = pd.DataFrame(rows, columns=columns)
            else:
                df = pd.DataFrame(rows)

            logger.info(f"📊 Query returned {len(df)} rows")
            return df
        except Exception as e:
            logger.error(f"❌ Query failed: {e}")
            return pd.DataFrame()

    # Analytics Queries

    def query_top_brands(self, limit: int = 10) -> pd.DataFrame:
        """Get top brands by product count."""
        queries = [
            f"""
            SELECT brand, COUNT(*) as product_count,
                   AVG(rating) as avg_rating,
                   AVG(price) as avg_price
            FROM products
            WHERE brand IS NOT NULL AND brand != ''
            GROUP BY brand
            ORDER BY product_count DESC
            LIMIT ?
            """,
            f"""
            SELECT brand, COUNT(*) as product_count,
                   AVG(rating) as avg_rating,
                   AVG(price) as avg_price
            FROM {self.schema}.products
            WHERE brand IS NOT NULL AND brand != ''
            GROUP BY brand
            ORDER BY product_count DESC
            LIMIT ?
            """
        ]

        for query in queries:
            try:
                return self.execute_query(query, (limit,))
            except:
                continue

        return pd.DataFrame()

    def query_price_discount_correlation(self) -> pd.DataFrame:
        """Get price and discount correlation data."""
        queries = [
            """
            SELECT price, discount_percent, rating, brand
            FROM products
            WHERE price > 0 AND discount_percent >= 0
            ORDER BY price
            LIMIT 1000
            """,
            f"""
            SELECT price, discount_percent, rating, brand
            FROM {self.schema}.products
            WHERE price > 0 AND discount_percent >= 0
            ORDER BY price
            LIMIT 1000
            """
        ]

        for query in queries:
            try:
                return self.execute_query(query)
            except:
                continue

        return pd.DataFrame()

    def query_rating_distribution(self) -> pd.DataFrame:
        """Get rating distribution."""
        queries = [
            """
            SELECT 
                FLOOR(rating) as rating_bucket,
                COUNT(*) as count
            FROM products
            WHERE rating > 0
            GROUP BY rating_bucket
            ORDER BY rating_bucket
            """,
            f"""
            SELECT 
                FLOOR(rating) as rating_bucket,
                COUNT(*) as count
            FROM {self.schema}.products
            WHERE rating > 0
            GROUP BY rating_bucket
            ORDER BY rating_bucket
            """
        ]

        for query in queries:
            try:
                return self.execute_query(query)
            except:
                continue

        return pd.DataFrame()

    def query_outliers(self) -> pd.DataFrame:
        """Identify price outliers."""
        queries = [
            """
            WITH stats AS (
                SELECT 
                    AVG(price) as avg_price,
                    STDDEV(price) as stddev_price
                FROM products
                WHERE price > 0
            )
            SELECT p.product_id, p.title, p.brand, p.price, p.rating
            FROM products p, stats s
            WHERE p.price > (s.avg_price + 2 * s.stddev_price)
               OR p.price < (s.avg_price - 2 * s.stddev_price)
            ORDER BY p.price DESC
            LIMIT 20
            """,
            f"""
            WITH stats AS (
                SELECT 
                    AVG(price) as avg_price,
                    STDDEV(price) as stddev_price
                FROM {self.schema}.products
                WHERE price > 0
            )
            SELECT p.product_id, p.title, p.brand, p.price, p.rating
            FROM {self.schema}.products p, stats s
            WHERE p.price > (s.avg_price + 2 * s.stddev_price)
               OR p.price < (s.avg_price - 2 * s.stddev_price)
            ORDER BY p.price DESC
            LIMIT 20
            """
        ]

        for query in queries:
            try:
                return self.execute_query(query)
            except:
                continue

        return pd.DataFrame()

    def query_product_segments(self) -> pd.DataFrame:
        """Segment products by price and rating."""
        queries = [
            """
            SELECT 
                CASE 
                    WHEN price < 1000 THEN 'Budget'
                    WHEN price BETWEEN 1000 AND 3000 THEN 'Mid-Range'
                    ELSE 'Premium'
                END as price_segment,
                CASE 
                    WHEN rating < 3 THEN 'Low Rated'
                    WHEN rating BETWEEN 3 AND 4 THEN 'Medium Rated'
                    ELSE 'High Rated'
                END as rating_segment,
                COUNT(*) as count,
                AVG(price) as avg_price,
                AVG(rating) as avg_rating
            FROM products
            WHERE price > 0 AND rating > 0
            GROUP BY price_segment, rating_segment
            ORDER BY price_segment, rating_segment
            """,
            f"""
            SELECT 
                CASE 
                    WHEN price < 1000 THEN 'Budget'
                    WHEN price BETWEEN 1000 AND 3000 THEN 'Mid-Range'
                    ELSE 'Premium'
                END as price_segment,
                CASE 
                    WHEN rating < 3 THEN 'Low Rated'
                    WHEN rating BETWEEN 3 AND 4 THEN 'Medium Rated'
                    ELSE 'High Rated'
                END as rating_segment,
                COUNT(*) as count,
                AVG(price) as avg_price,
                AVG(rating) as avg_rating
            FROM {self.schema}.products
            WHERE price > 0 AND rating > 0
            GROUP BY price_segment, rating_segment
            ORDER BY price_segment, rating_segment
            """
        ]

        for query in queries:
            try:
                return self.execute_query(query)
            except:
                continue

        return pd.DataFrame()

    def get_summary_stats(self) -> Dict[str, Any]:
        """Get overall summary statistics."""
        queries = [
            """
            SELECT 
                COUNT(*) as total_products,
                COUNT(DISTINCT brand) as total_brands,
                AVG(price) as avg_price,
                MAX(price) as max_price,
                MIN(price) as min_price,
                AVG(rating) as avg_rating,
                AVG(discount_percent) as avg_discount
            FROM products
            WHERE price > 0
            """,
            f"""
            SELECT 
                COUNT(*) as total_products,
                COUNT(DISTINCT brand) as total_brands,
                AVG(price) as avg_price,
                MAX(price) as max_price,
                MIN(price) as min_price,
                AVG(rating) as avg_rating,
                AVG(discount_percent) as avg_discount
            FROM {self.schema}.products
            WHERE price > 0
            """
        ]

        for query in queries:
            try:
                df = self.execute_query(query)
                if not df.empty:
                    return df.iloc[0].to_dict()
            except:
                continue

        return {}

    def close(self):
        """Close the database connection."""
        try:
            if self.cursor:
                self.cursor.close()
            if self.connection:
                self.connection.close()
            logger.info("✅ MonkDB connection closed")
        except Exception as e:
            logger.error(f"❌ Error closing connection: {e}")
