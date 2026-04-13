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


def _parse_date(s: Optional[str]) -> Optional[datetime]:
    """Parse an ISO-format date string (YYYY-MM-DD or full ISO) to datetime."""
    if not s:
        return None
    try:
        if len(s) == 10:
            return datetime.strptime(s, "%Y-%m-%d")
        return datetime.fromisoformat(s.replace("Z", "+00:00").replace("+00:00", ""))
    except (ValueError, TypeError):
        return None


def _date_range_query(
    field: str,
    days: int,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
) -> Dict:
    """Build a MongoDB date range filter for *field*.

    If from_date/to_date are provided they take priority over days.
    to_date is inclusive (end of that day).
    """
    fd = _parse_date(from_date)
    td = _parse_date(to_date)

    if fd or td:
        cond: Dict = {}
        if fd:
            cond["$gte"] = fd
        if td:
            cond["$lte"] = td.replace(hour=23, minute=59, second=59)
        return {field: cond}

    return {field: {"$gte": datetime.utcnow() - timedelta(days=days)}}


def _iso_dates(docs: list, *fields: str) -> list:
    """Convert datetime fields to ISO-8601 strings in-place."""
    for d in docs:
        for f in fields:
            val = d.get(f)
            if isinstance(val, datetime):
                d[f] = val.isoformat()
    return docs


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
        self.tickets.create_index([("is_bug", ASCENDING)])
        self.tickets.create_index([("qa_feature_area", ASCENDING)])
        self.tickets.create_index([("qa_platform", ASCENDING)])
        self.tickets.create_index([("qa_status", ASCENDING)])
        self.tickets.create_index([("qa_dismissed", ASCENDING)])

        self._migrate_qa_status()

    def _migrate_qa_status(self):
        """Backfill qa_status and qa_dismissed on existing bug tickets."""
        try:
            result = self.tickets.update_many(
                {"is_bug": True, "qa_status": {"$exists": False}},
                {"$set": {"qa_status": "not_tested", "qa_dismissed": False}},
            )
            if result.modified_count:
                logger.info(
                    f"QA status migration: set qa_status on {result.modified_count} tickets"
                )
        except Exception as e:
            logger.warning(f"QA status migration skipped: {e}")

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

    def get_recent_analyses(
        self,
        limit: int = 30,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> List[Dict]:
        try:
            query = _date_range_query("run_date", 9999, from_date, to_date) if (from_date or to_date) else {}
            cursor = self.analyses.find(query).sort("run_date", DESCENDING)
            if not (from_date or to_date):
                cursor = cursor.limit(limit)
            docs = list(cursor)
            for d in docs:
                d["_id"] = str(d["_id"])
            _iso_dates(docs, "run_date")
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
            _iso_dates(docs, "created_at", "supportpal_created_at")
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

    def get_sentiment_stats(
        self,
        days: int = 7,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> Dict:
        """Aggregate sentiment/urgency/churn across the given date range."""
        try:
            date_filter = _date_range_query("run_date", days, from_date, to_date)

            analysis_ids = [
                a["_id"]
                for a in self.analyses.find(date_filter, {"_id": 1})
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

            sentiment_dist = _to_dict(data["sentiment"])
            urgency_dist = _to_dict(data["urgency"])
            churn_dist = _to_dict(data["churn_risk"])

            health_score, health_label = self._compute_health_score(
                sentiment_dist, urgency_dist, churn_dist, total,
            )

            return {
                "period_days": days,
                "total_scored": total,
                "sentiment": sentiment_dist,
                "urgency": urgency_dist,
                "churn_risk": churn_dist,
                "high_churn_tickets": [
                    {k: str(v) if k == "_id" else v for k, v in doc.items()}
                    for doc in data["high_churn"]
                ],
                "health_score": health_score,
                "health_label": health_label,
            }
        except Exception as e:
            logger.error(f"Error aggregating sentiment data: {e}")
            return {}

    @staticmethod
    def _compute_health_score(
        sentiment: Dict, urgency: Dict, churn: Dict, total: int
    ) -> tuple:
        if total == 0:
            return 100, "Healthy"

        sent_weights = {"positive": 0, "neutral_confused": 10, "frustrated": 30, "angry": 40}
        urg_weights = {"low": 0, "medium": 10, "high": 20, "critical": 30}
        churn_weights = {"low": 0, "medium": 15, "high": 30}

        def _wavg(dist: Dict, weights: Dict, max_pen: float) -> float:
            t = sum(dist.values())
            if t == 0:
                return 0.0
            raw = sum(weights.get(k, 0) * v for k, v in dist.items()) / t
            cap = max(weights.values()) if weights else 1
            return (raw / cap) * max_pen

        penalty = (
            _wavg(sentiment, sent_weights, 40)
            + _wavg(urgency, urg_weights, 30)
            + _wavg(churn, churn_weights, 30)
        )
        score = max(0, min(100, round(100 - penalty)))

        if score >= 80:
            label = "Healthy"
        elif score >= 60:
            label = "Stable"
        elif score >= 40:
            label = "Concerning"
        else:
            label = "Critical"

        return score, label

    # ── QA helpers ────────────────────────────────────────────────────────

    def get_qa_clusters(self, days: int = 7, min_count: int = 1) -> Dict:
        """Aggregate bug tickets by platform over the last *days*."""
        try:
            cutoff = datetime.utcnow() - timedelta(days=days)

            analysis_ids = [
                a["_id"]
                for a in self.analyses.find(
                    {"run_date": {"$gte": cutoff}}, {"_id": 1}
                )
            ]
            if not analysis_ids:
                return {"period_days": days, "clusters": [], "total_bugs": 0}

            pipeline = [
                {
                    "$match": {
                        "analysis_id": {"$in": analysis_ids},
                        "is_bug": True,
                    }
                },
                {
                    "$group": {
                        "_id": "$qa_platform",
                        "count": {"$sum": 1},
                        "tickets": {
                            "$push": {
                                "ticket_number": "$ticket_number",
                                "supportpal_id": "$supportpal_id",
                                "subject": "$subject",
                                "feature_area": "$qa_feature_area",
                                "error_pattern": "$qa_error_pattern",
                            }
                        },
                    }
                },
                {"$match": {"count": {"$gte": min_count}}},
                {"$sort": {"count": -1}},
            ]

            clusters_raw = list(self.tickets.aggregate(pipeline))

            total_bugs_pipeline = [
                {
                    "$match": {
                        "analysis_id": {"$in": analysis_ids},
                        "is_bug": True,
                    }
                },
                {"$count": "n"},
            ]
            total_result = list(self.tickets.aggregate(total_bugs_pipeline))
            total_bugs = total_result[0]["n"] if total_result else 0

            clusters = []
            for c in clusters_raw:
                clusters.append({
                    "platform": c["_id"],
                    "count": c["count"],
                    "tickets": c["tickets"][:20],
                })

            return {
                "period_days": days,
                "total_bugs": total_bugs,
                "clusters": clusters,
            }
        except Exception as e:
            logger.error(f"Error aggregating QA data: {e}")
            return {"period_days": days, "clusters": [], "total_bugs": 0}

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

    # ── Sentiment dashboard helpers ────────────────────────────────────

    VALID_SENTIMENTS = {"positive", "neutral_confused", "frustrated", "angry"}
    VALID_URGENCIES = {"low", "medium", "high", "critical"}
    VALID_CHURN = {"low", "medium", "high"}

    def get_sentiment_tickets(
        self,
        days: int = 30,
        sentiment: Optional[str] = None,
        urgency: Optional[str] = None,
        churn_risk: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> List[Dict]:
        """Return individual tickets with sentiment data for the dashboard table."""
        try:
            date_filter = _date_range_query("created_at", days, from_date, to_date)
            query: Dict = {
                "sentiment": {"$ne": None},
                **date_filter,
            }
            if sentiment and sentiment in self.VALID_SENTIMENTS:
                query["sentiment"] = sentiment
            if urgency and urgency in self.VALID_URGENCIES:
                query["urgency"] = urgency
            if churn_risk and churn_risk in self.VALID_CHURN:
                query["churn_risk"] = churn_risk

            projection = {
                "_id": 1,
                "ticket_number": 1,
                "supportpal_id": 1,
                "subject": 1,
                "sentiment": 1,
                "urgency": 1,
                "churn_risk": 1,
                "sentiment_summary": 1,
                "created_at": 1,
            }

            docs = list(
                self.tickets.find(query, projection)
                .sort("created_at", DESCENDING)
                .limit(500)
            )
            for d in docs:
                d["_id"] = str(d["_id"])
            _iso_dates(docs, "created_at")
            return docs
        except Exception as e:
            logger.error(f"Error fetching sentiment tickets: {e}")
            return []

    # ── QA dashboard helpers ─────────────────────────────────────────────

    VALID_QA_STATUSES = {"not_tested", "reproduced", "escalated"}

    def get_qa_tickets(
        self,
        days: int = 30,
        platform: Optional[str] = None,
        status: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> List[Dict]:
        """Return individual bug tickets for the QA dashboard table."""
        try:
            date_filter = _date_range_query("created_at", days, from_date, to_date)
            query: Dict = {
                "is_bug": True,
                "qa_dismissed": {"$ne": True},
                **date_filter,
            }
            if platform:
                query["qa_platform"] = platform
            if status and status in self.VALID_QA_STATUSES:
                query["qa_status"] = status

            projection = {
                "_id": 1,
                "ticket_number": 1,
                "supportpal_id": 1,
                "subject": 1,
                "qa_feature_area": 1,
                "qa_platform": 1,
                "qa_error_pattern": 1,
                "qa_status": 1,
                "created_at": 1,
            }

            docs = list(
                self.tickets.find(query, projection)
                .sort("created_at", DESCENDING)
                .limit(500)
            )
            for d in docs:
                d["_id"] = str(d["_id"])
            _iso_dates(docs, "created_at")
            return docs
        except Exception as e:
            logger.error(f"Error fetching QA tickets: {e}")
            return []

    def get_qa_stats(
        self,
        days: int = 30,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> Dict:
        """Aggregate QA dashboard stats."""
        try:
            date_filter = _date_range_query("created_at", days, from_date, to_date)
            base_match = {
                "is_bug": True,
                **date_filter,
            }

            pipeline = [
                {"$match": base_match},
                {
                    "$facet": {
                        "by_status": [
                            {"$match": {"qa_dismissed": {"$ne": True}}},
                            {"$group": {"_id": "$qa_status", "count": {"$sum": 1}}},
                        ],
                        "dismissed": [
                            {"$match": {"qa_dismissed": True}},
                            {"$count": "n"},
                        ],
                        "by_platform": [
                            {"$match": {"qa_dismissed": {"$ne": True}}},
                            {"$group": {"_id": "$qa_platform", "count": {"$sum": 1}}},
                        ],
                        "total": [
                            {"$match": {"qa_dismissed": {"$ne": True}}},
                            {"$count": "n"},
                        ],
                    }
                },
            ]

            result = list(self.tickets.aggregate(pipeline))
            if not result:
                return self._empty_qa_stats(days)

            data = result[0]
            total = data["total"][0]["n"] if data["total"] else 0
            dismissed = data["dismissed"][0]["n"] if data["dismissed"] else 0

            status_map = {b["_id"]: b["count"] for b in data["by_status"] if b["_id"]}
            platform_map = {b["_id"]: b["count"] for b in data["by_platform"] if b["_id"]}

            return {
                "period_days": days,
                "total_bugs": total,
                "not_tested": status_map.get("not_tested", 0),
                "reproduced": status_map.get("reproduced", 0),
                "escalated": status_map.get("escalated", 0),
                "dismissed": dismissed,
                "by_platform": platform_map,
            }
        except Exception as e:
            logger.error(f"Error aggregating QA stats: {e}")
            return self._empty_qa_stats(days)

    @staticmethod
    def _empty_qa_stats(days: int) -> Dict:
        return {
            "period_days": days,
            "total_bugs": 0,
            "not_tested": 0,
            "reproduced": 0,
            "escalated": 0,
            "dismissed": 0,
            "by_platform": {},
        }

    def update_qa_status(self, ticket_id: str, new_status: str) -> bool:
        """Set qa_status on a single ticket. Returns True on success."""
        if new_status not in self.VALID_QA_STATUSES:
            return False
        try:
            result = self.tickets.update_one(
                {"_id": ObjectId(ticket_id)},
                {"$set": {"qa_status": new_status}},
            )
            return result.modified_count == 1
        except Exception as e:
            logger.error(f"Error updating QA status for {ticket_id}: {e}")
            return False

    def dismiss_qa_ticket(self, ticket_id: str) -> bool:
        """Soft-delete a QA ticket by setting qa_dismissed=True."""
        try:
            result = self.tickets.update_one(
                {"_id": ObjectId(ticket_id)},
                {"$set": {"qa_dismissed": True}},
            )
            return result.modified_count == 1
        except Exception as e:
            logger.error(f"Error dismissing QA ticket {ticket_id}: {e}")
            return False

    # ── Cleanup ─────────────────────────────────────────────────────────────

    def close(self):
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")
