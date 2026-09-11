# ============================================================================
# PRITHU BACKEND - DATABASE CONNECTION MODULE
# ============================================================================
# Manages MongoDB connection and database operations with error handling
# ============================================================================

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, OperationFailure
from bson import ObjectId

from app.core.config import Config
from app.exceptions import (
    DatabaseConnectionException,
    DatabaseException,
    ResourceNotFoundException,
    ErrorCode
)
from app.core.logger_setup import get_logger


logger = get_logger(__name__)


class DatabaseManager:
    """
    Singleton database manager for MongoDB operations.
    Handles connection pooling, error handling, and query execution.
    """

    _instance: Optional['DatabaseManager'] = None
    _client: Optional[MongoClient] = None
    _db = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize database manager."""
        if self._initialized:
            return
        self._connect()
        self._initialized = True

    def _connect(self) -> None:
        """
        Establish connection to MongoDB.

        Raises:
            DatabaseConnectionException: If connection fails
        """
        try:
            logger.info("🔌 Connecting to MongoDB Atlas...")

            self._client = MongoClient(
                Config.MONGODB_URI,
                serverSelectionTimeoutMS=Config.MONGODB_TIMEOUT,
                connectTimeoutMS=Config.MONGODB_TIMEOUT,
                socketTimeoutMS=20000,
            )

            # Test connection
            self._client.admin.command("ping")
            self._db = self._client[Config.MONGODB_DATABASE]

            logger.info(f"✅ MongoDB connected successfully")
            logger.info(f"📚 Database: {Config.MONGODB_DATABASE}")

        except ServerSelectionTimeoutError as e:
            error_msg = f"MongoDB connection timeout: {str(e)}"
            logger.error(error_msg)
            raise DatabaseConnectionException(error_msg)

        except OperationFailure as e:
            error_msg = f"MongoDB authentication failed: {str(e)}"
            logger.error(error_msg)
            raise DatabaseConnectionException(error_msg)

        except Exception as e:
            error_msg = f"MongoDB connection failed: {str(e)}"
            logger.error(error_msg)
            raise DatabaseConnectionException(error_msg)

    def get_database(self):
        """
        Get database instance.

        Returns:
            Database instance

        Raises:
            DatabaseConnectionException: If not connected
        """
        if self._db is None:
            raise DatabaseConnectionException("Database not initialized")
        return self._db

    def get_collection(self, collection_name: str):
        """
        Get collection instance with error handling.

        Args:
            collection_name: Name of collection

        Returns:
            Collection instance

        Raises:
            DatabaseConnectionException: If database not connected
        """
        try:
            db = self.get_database()
            return db[collection_name]
        except Exception as e:
            logger.error(f"Error getting collection {collection_name}: {e}")
            raise

    def find_one(
        self,
        collection_name: str,
        query: Dict[str, Any],
        projection: Optional[Dict] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Find single document.

        Args:
            collection_name: Collection name
            query: Query filter
            projection: Fields to return

        Returns:
            Document or None

        Raises:
            DatabaseException: If query fails
        """
        try:
            collection = self.get_collection(collection_name)
            result = collection.find_one(query, projection)
            return result

        except Exception as e:
            logger.error(f"Error finding document in {collection_name}: {e}")
            raise DatabaseException(
                f"Failed to query {collection_name}",
                details={"error": str(e)}
            )

    def find_many(
        self,
        collection_name: str,
        query: Dict[str, Any],
        projection: Optional[Dict] = None,
        limit: int = 1000,
        sort: Optional[List] = None
    ) -> List[Dict[str, Any]]:
        """
        Find multiple documents.

        Args:
            collection_name: Collection name
            query: Query filter
            projection: Fields to return
            limit: Max documents to return
            sort: Sort specification

        Returns:
            List of documents

        Raises:
            DatabaseException: If query fails
        """
        try:
            collection = self.get_collection(collection_name)
            cursor = collection.find(query, projection)

            if sort:
                cursor = cursor.sort(sort)

            cursor = cursor.limit(limit)
            results = list(cursor)

            logger.debug(f"Found {len(results)} documents in {collection_name}")
            return results

        except Exception as e:
            logger.error(f"Error finding documents in {collection_name}: {e}")
            raise DatabaseException(
                f"Failed to query {collection_name}",
                details={"error": str(e)}
            )

    def insert_one(
        self,
        collection_name: str,
        document: Dict[str, Any]
    ) -> str:
        """
        Insert single document.

        Args:
            collection_name: Collection name
            document: Document to insert

        Returns:
            Inserted document ID

        Raises:
            DatabaseException: If insert fails
        """
        try:
            collection = self.get_collection(collection_name)

            # Add timestamp if not present
            if "createdAt" not in document:
                document["createdAt"] = datetime.now(timezone.utc)

            result = collection.insert_one(document)
            logger.debug(f"Inserted document in {collection_name}: {result.inserted_id}")
            return str(result.inserted_id)

        except Exception as e:
            logger.error(f"Error inserting into {collection_name}: {e}")
            raise DatabaseException(
                f"Failed to insert into {collection_name}",
                details={"error": str(e)}
            )

    def update_one(
        self,
        collection_name: str,
        query: Dict[str, Any],
        update: Dict[str, Any]
    ) -> int:
        """
        Update single document.

        Args:
            collection_name: Collection name
            query: Query filter
            update: Update operations

        Returns:
            Number of modified documents

        Raises:
            DatabaseException: If update fails
        """
        try:
            collection = self.get_collection(collection_name)

            # Add updatedAt timestamp
            update["$set"] = update.get("$set", {})
            update["$set"]["updatedAt"] = datetime.now(timezone.utc)

            result = collection.update_one(query, update)
            logger.debug(f"Updated {result.modified_count} documents in {collection_name}")
            return result.modified_count

        except Exception as e:
            logger.error(f"Error updating {collection_name}: {e}")
            raise DatabaseException(
                f"Failed to update {collection_name}",
                details={"error": str(e)}
            )

    def delete_one(
        self,
        collection_name: str,
        query: Dict[str, Any]
    ) -> int:
        """
        Delete single document.

        Args:
            collection_name: Collection name
            query: Query filter

        Returns:
            Number of deleted documents

        Raises:
            DatabaseException: If delete fails
        """
        try:
            collection = self.get_collection(collection_name)
            result = collection.delete_one(query)
            logger.debug(f"Deleted {result.deleted_count} documents in {collection_name}")
            return result.deleted_count

        except Exception as e:
            logger.error(f"Error deleting from {collection_name}: {e}")
            raise DatabaseException(
                f"Failed to delete from {collection_name}",
                details={"error": str(e)}
            )

    def count_documents(
        self,
        collection_name: str,
        query: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Count documents in collection.

        Args:
            collection_name: Collection name
            query: Query filter

        Returns:
            Number of documents

        Raises:
            DatabaseException: If count fails
        """
        try:
            collection = self.get_collection(collection_name)
            count = collection.count_documents(query or {})
            return count

        except Exception as e:
            logger.error(f"Error counting documents in {collection_name}: {e}")
            raise DatabaseException(
                f"Failed to count documents in {collection_name}",
                details={"error": str(e)}
            )

    def get_distinct(
        self,
        collection_name: str,
        field: str,
        query: Optional[Dict[str, Any]] = None
    ) -> List[Any]:
        """
        Get distinct values for a field.

        Args:
            collection_name: Collection name
            field: Field name
            query: Query filter

        Returns:
            List of distinct values

        Raises:
            DatabaseException: If query fails
        """
        try:
            collection = self.get_collection(collection_name)
            results = collection.distinct(field, query or {})
            return results

        except Exception as e:
            logger.error(f"Error getting distinct values from {collection_name}: {e}")
            raise DatabaseException(
                f"Failed to get distinct values from {collection_name}",
                details={"error": str(e)}
            )

    def health_check(self) -> bool:
        """
        Check database connection health.

        Returns:
            True if connected, False otherwise
        """
        try:
            if self._client:
                self._client.admin.command("ping")
                return True
            return False
        except Exception as e:
            logger.warning(f"Database health check failed: {e}")
            return False

    def close(self) -> None:
        """Close database connection."""
        try:
            if self._client:
                self._client.close()
                self._client = None
                self._db = None
                logger.info("📌 MongoDB connection closed")
        except Exception as e:
            logger.error(f"Error closing database connection: {e}")


# Singleton instance accessor
def get_db_manager() -> DatabaseManager:
    """
    Get database manager singleton instance.

    Returns:
        DatabaseManager: Global database manager instance
    """
    return DatabaseManager()
