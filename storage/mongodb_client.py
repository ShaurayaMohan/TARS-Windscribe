"""
MongoDB storage client for TARS (v2 schema).

Collections:
  analyses  – one document per pipeline run (summary + category breakdown)
  tickets   – one document per ticket (raw data + AI classification)
  config    – application settings (prompt templates, etc.)
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from bson import ObjectId
from pymongo import MongoClient, DESCENDING, ASCENDING
from pymongo.errors import ConnectionFailure, OperationFailure

logger = logging.getLogger(__name__)

_SCHEMA_VERSION = "2.0"


class MongoDBStorage:
    """MongoDB storage for TARS analysis results (v2 schema)."""

    def __init__(self, connection_string: str, database_name: str = "tars"):
        try:
            self.client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
            self.client.admin.command("ping")
            logger.info("MongoDB connection successful")

            self.db = self.client[database_name]

            self._migrate_v1_if_needed()

            self.analyses = self.db["analyses"]
            self.tickets = self.db["tickets"]
            self.config_collection = self.db["config"]

            self._ensure_indexes()

        except ConnectionFailure as e:
            logger.error(f"MongoDB connection failed: {e}")
            raise
        except Exception as e:
            logger.error(f"MongoDB initialization error: {e}")
            raise

    # ── One-time migration ──────────────────────────────────────────────────

    def _migrate_v1_if_needed(self):
        """Rename the old v1 analyses collection if it still exists."""
        existing = self.db.list_collection_names()
        if "analyses" in existing and "analyses_v1_archived" not in existing:
            old = self.db["analyses"]
            sample = old.find_one()
            if sample and "version" in sample and sample.get("version") == "1.0":
                old.rename("analyses_v1_archived")
                logger.info(
                    "Migrated old v1 'analyses' collection → 'analyses_v1_archived'"
                )

    # ── Indexes ─────────────────────────────────────────────────────────────

    def _ensure_indexes(self):
        self.analyses.create_index([("run_date", DESCENDING)])

        self.tickets.create_index([("analysis_id", ASCENDING)])
        self.tickets.create_index([("category_id", ASCENDING)])
        self.tickets.create_index([("ticket_number", ASCENDING)])
        self.tickets.create_index([("created_at", DESCENDING)])
        self.tickets.create_index([("is_new_trend", ASCENDING)])
        self.tickets.create_index([("sentiment", ASCENDING)])
        self.tickets.create_index([("churn_risk", ASCENDING)])
        self.tickets.create_index([("urgency", ASCENDING)])

    # ── Write ───────────────────────────────────────────────────────────────

    def save_analysis(self, analysis_doc: Dict) -> str:
        """Insert an analysis summary document. Returns inserted _id as str."""
        try:
            analysis_doc.setdefault("run_date", datetime.utcnow())
            analysis_doc["schema_version"] = _SCHEMA_VERSION
            result = self.analyses.insert_one(analysis_doc)
            logger.info(f"Analysis saved: {result.inserted_id}")
            return str(result.inserted_id)
        except OperationFailure as e:
            logger.error(f"Failed to save analysis: {e}")
            raise

    def save_tickets(self, ticket_docs: List[Dict]) -> int:
        """Bulk-insert ticket documents. Returns count inserted."""
        if not ticket_docs:
            return 0
        try:
            now = datetime.utcnow()
            for doc in ticket_docs:
                doc.setdefault("created_at", now)
            result = self.tickets.insert_many(ticket_docs, ordered=False)
            count = len(result.inserted_ids)
            logger.info(f"{count} tickets saved")
            return count
        except OperationFailure as e:
            logger.error(f"Failed to save tickets: {e}")
            raise

    # ── Read: analyses ──────────────────────────────────────────────────────

    def get_recent_analyses(self, limit: int = 30) -> List[Dict]:
        try:
            docs = list(
                self.analyses.find()
                .sort("run_date", DESCENDING)
                .limit(limit)
            )
            for d in docs:
                d["_id"] = str(d["_id"])
            return docs
        except Exception as e:
            logger.error(f"Error retrieving analyses: {e}")
            return []

    def get_analysis_by_id(self, analysis_id: str) -> Optional[Dict]:
        try:
            doc = self.analyses.find_one({"_id": ObjectId(analysis_id)})
            if doc:
                doc["_id"] = str(doc["_id"])
            return doc
        except Exception as e:
            logger.error(f"Error retrieving analysis {analysis_id}: {e}")
            return None

    # ── Read: tickets ───────────────────────────────────────────────────────

    def get_tickets_by_analysis(self, analysis_id: str) -> List[Dict]:
        try:
            docs = list(
                self.tickets.find({"analysis_id": ObjectId(analysis_id)})
                .sort("ticket_number", ASCENDING)
            )
            for d in docs:
                d["_id"] = str(d["_id"])
                d["analysis_id"] = str(d["analysis_id"])
            return docs
        except Exception as e:
            logger.error(f"Error retrieving tickets for analysis {analysis_id}: {e}")
            return []

    def get_tickets_by_category(
        self, category_id: str, days: int = 30, limit: int = 200
    ) -> List[Dict]:
        try:
            since = datetime.utcnow() - timedelta(days=days)
            docs = list(
                self.tickets.find({
                    "category_id": category_id,
                    "created_at": {"$gte": since},
                })
                .sort("created_at", DESCENDING)
                .limit(limit)
            )
            for d in docs:
                d["_id"] = str(d["_id"])
                d["analysis_id"] = str(d["analysis_id"])
            return docs
        except Exception as e:
            logger.error(f"Error retrieving tickets for category {category_id}: {e}")
            return []

    # ── Dashboard stats ─────────────────────────────────────────────────────

    def get_dashboard_stats(self) -> Dict:
        try:
            latest = self.analyses.find_one(sort=[("run_date", DESCENDING)])

            today_start = datetime.utcnow().replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            today_count = self.analyses.count_documents(
                {"run_date": {"$gte": today_start}}
            )
            total_analyses = self.analyses.count_documents({})

            week_ago = datetime.utcnow() - timedelta(days=7)
            pipeline = [
                {"$match": {"created_at": {"$gte": week_ago}}},
                {"$group": {"_id": None, "total": {"$sum": 1}}},
            ]
            agg = list(self.tickets.aggregate(pipeline))
            week_tickets = agg[0]["total"] if agg else 0

            top_category = None
            if latest:
                cats = latest.get("categories", {})
                if cats:
                    top_id = max(cats, key=lambda k: cats[k].get("count", 0))
                    top_cat = cats[top_id]
                    top_category = {
                        "category_id": top_id,
                        "title": top_cat.get("title", top_id),
                        "count": top_cat.get("count", 0),
                    }

            return {
                "latest_analysis": {
                    "date": latest["run_date"].isoformat()
                    if latest and latest.get("run_date")
                    else None,
                    "tickets": latest.get("total_tickets", 0) if latest else 0,
                    "categories": len(latest.get("categories", {}))
                    if latest
                    else 0,
                    "top_category": top_category,
                }
                if latest
                else None,
                "today_analyses": today_count,
                "total_analyses": total_analyses,
                "last_7_days_tickets": week_tickets,
            }
        except Exception as e:
            logger.error(f"Error getting dashboard stats: {e}")
            return {}

    # ── Trend data for charts ───────────────────────────────────────────────

    def get_trend_data(self, days: int = 30) -> Dict:
        try:
            since = datetime.utcnow() - timedelta(days=days)

            analyses = list(
                self.analyses.find({"run_date": {"$gte": since}})
                .sort("run_date", DESCENDING)
            )

            total_analyses = len(analyses)
            total_tickets = sum(a.get("total_tickets", 0) for a in analyses)
            total_categories = sum(
                len(a.get("categories", {})) for a in analyses
            )

            daily_data: Dict[str, Dict] = {}
            for a in analyses:
                date_key = a["run_date"].strftime("%Y-%m-%d")
                if date_key not in daily_data:
                    daily_data[date_key] = {
                        "tickets": 0,
                        "categories": 0,
                        "analyses": 0,
                    }
                daily_data[date_key]["tickets"] += a.get("total_tickets", 0)
                daily_data[date_key]["categories"] += len(
                    a.get("categories", {})
                )
                daily_data[date_key]["analyses"] += 1

            cat_frequency: Dict[str, int] = {}
            for a in analyses:
                for cat_id, cat_data in a.get("categories", {}).items():
                    title = cat_data.get("title", cat_id)
                    cat_frequency[title] = (
                        cat_frequency.get(title, 0)
                        + cat_data.get("count", 0)
                    )

            top_issues = sorted(
                [{"title": k, "count": v} for k, v in cat_frequency.items()],
                key=lambda x: x["count"],
                reverse=True,
            )[:10]

            return {
                "period_days": days,
                "total_analyses": total_analyses,
                "total_tickets": total_tickets,
                "total_categories": total_categories,
                "avg_tickets_per_analysis": round(
                    total_tickets / total_analyses, 2
                )
                if total_analyses > 0
                else 0,
                "daily_breakdown": daily_data,
                "top_recurring_issues": top_issues,
            }
        except Exception as e:
            logger.error(f"Error calculating trend data: {e}")
            return {}

    # ── Sentiment helpers ──────────────────────────────────────────────────

    def get_sentiment_stats(self, days: int = 7) -> Dict:
        """Aggregate sentiment/urgency/churn across the last *days* days."""
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)

            analysis_ids = [
                a["_id"]
                for a in self.analyses.find(
                    {"run_date": {"$gte": cutoff}}, {"_id": 1}
                )
            ]
            if not analysis_ids:
                return {}

            pipeline = [
                {"$match": {"analysis_id": {"$in": analysis_ids}, "sentiment": {"$ne": None}}},
                {
                    "$facet": {
                        "sentiment": [
                            {"$group": {"_id": "$sentiment", "count": {"$sum": 1}}},
                        ],
                        "urgency": [
                            {"$group": {"_id": "$urgency", "count": {"$sum": 1}}},
                        ],
                        "churn_risk": [
                            {"$group": {"_id": "$churn_risk", "count": {"$sum": 1}}},
                        ],
                        "high_churn": [
                            {"$match": {"churn_risk": "high"}},
                            {
                                "$project": {
                                    "ticket_number": 1,
                                    "subject": 1,
                                    "sentiment_summary": 1,
                                    "sentiment": 1,
                                    "urgency": 1,
                                }
                            },
                        ],
                        "total": [{"$count": "n"}],
                    }
                },
            ]

            result = list(self.tickets.aggregate(pipeline))
            if not result:
                return {}

            data = result[0]
            total = data["total"][0]["n"] if data["total"] else 0

            def _to_dict(bucket_list):
                return {b["_id"]: b["count"] for b in bucket_list if b["_id"]}

            return {
                "period_days": days,
                "total_scored": total,
                "sentiment": _to_dict(data["sentiment"]),
                "urgency": _to_dict(data["urgency"]),
                "churn_risk": _to_dict(data["churn_risk"]),
                "high_churn_tickets": data["high_churn"],
            }
        except Exception as e:
            logger.error(f"Error aggregating sentiment data: {e}")
            return {}

    # ── Config (prompt templates) ───────────────────────────────────────────

    def get_prompt_template(self) -> Optional[str]:
        try:
            doc = self.config_collection.find_one({"key": "prompt_template"})
            return doc.get("value") if doc else None
        except Exception as e:
            logger.error(f"Error reading prompt template: {e}")
            return None

    def save_prompt_template(self, text: str) -> bool:
        try:
            self.config_collection.update_one(
                {"key": "prompt_template"},
                {
                    "$set": {
                        "key": "prompt_template",
                        "value": text,
                        "updated_at": datetime.utcnow(),
                    }
                },
                upsert=True,
            )
            logger.info("Prompt template saved")
            return True
        except Exception as e:
            logger.error(f"Error saving prompt template: {e}")
            return False

    # ── Cleanup ─────────────────────────────────────────────────────────────

    def close(self):
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")
