"""
MongoDB storage client for TARS
Stores and retrieves historical analysis data
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pymongo import MongoClient, DESCENDING
from pymongo.errors import ConnectionFailure, OperationFailure

logger = logging.getLogger(__name__)


class MongoDBStorage:
    """MongoDB storage for TARS analysis results"""
    
    def __init__(self, connection_string: str, database_name: str = "tars"):
        """
        Initialize MongoDB connection
        
        Args:
            connection_string: MongoDB connection URI
            database_name: Database name (default: "tars")
        """
        try:
            self.client = MongoClient(connection_string, serverSelectionTimeoutMS=5000)
            # Test connection
            self.client.admin.command('ping')
            logger.info("✅ MongoDB connection successful")
            
            self.db = self.client[database_name]
            self.analyses_collection = self.db['analyses']
            
            # Create indexes for better query performance
            self.analyses_collection.create_index([("analysis_date", DESCENDING)])
            self.analyses_collection.create_index([("created_at", DESCENDING)])
            
        except ConnectionFailure as e:
            logger.error(f"❌ MongoDB connection failed: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ MongoDB initialization error: {e}")
            raise
    
    def save_analysis(self, analysis_results: Dict) -> str:
        """
        Save analysis results to MongoDB
        
        Args:
            analysis_results: Analysis data from TARSAnalyzer
            
        Returns:
            Inserted document ID as string
        """
        try:
            # Add metadata
            document = {
                **analysis_results,
                "created_at": datetime.utcnow(),
                "version": "1.0"
            }
            
            result = self.analyses_collection.insert_one(document)
            logger.info(f"✅ Analysis saved to MongoDB: {result.inserted_id}")
            return str(result.inserted_id)
            
        except OperationFailure as e:
            logger.error(f"❌ Failed to save analysis: {e}")
            raise
    
    def get_recent_analyses(self, limit: int = 30) -> List[Dict]:
        """
        Get most recent analyses
        
        Args:
            limit: Number of analyses to retrieve (default: 30)
            
        Returns:
            List of analysis documents
        """
        try:
            analyses = list(
                self.analyses_collection
                .find()
                .sort("created_at", DESCENDING)
                .limit(limit)
            )
            
            # Convert ObjectId to string for JSON serialization
            for analysis in analyses:
                analysis['_id'] = str(analysis['_id'])
                
            logger.info(f"Retrieved {len(analyses)} analyses from MongoDB")
            return analyses
            
        except Exception as e:
            logger.error(f"Error retrieving analyses: {e}")
            return []
    
    def get_analysis_by_id(self, analysis_id: str) -> Optional[Dict]:
        """
        Get specific analysis by ID
        
        Args:
            analysis_id: MongoDB document ID
            
        Returns:
            Analysis document or None
        """
        try:
            from bson import ObjectId
            analysis = self.analyses_collection.find_one({"_id": ObjectId(analysis_id)})
            
            if analysis:
                analysis['_id'] = str(analysis['_id'])
                
            return analysis
            
        except Exception as e:
            logger.error(f"Error retrieving analysis {analysis_id}: {e}")
            return None
    
    def get_analyses_by_date_range(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """
        Get analyses within date range
        
        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
        Returns:
            List of analysis documents
        """
        try:
            analyses = list(
                self.analyses_collection
                .find({
                    "created_at": {
                        "$gte": start_date,
                        "$lte": end_date
                    }
                })
                .sort("created_at", DESCENDING)
            )
            
            for analysis in analyses:
                analysis['_id'] = str(analysis['_id'])
                
            logger.info(f"Retrieved {len(analyses)} analyses from {start_date} to {end_date}")
            return analyses
            
        except Exception as e:
            logger.error(f"Error retrieving analyses by date range: {e}")
            return []
    
    def get_trend_data(self, days: int = 30) -> Dict:
        """
        Get aggregated trend data for charts
        
        Args:
            days: Number of days to look back (default: 30)
            
        Returns:
            Dictionary with trend statistics
        """
        try:
            start_date = datetime.utcnow() - timedelta(days=days)
            
            analyses = list(
                self.analyses_collection
                .find({
                    "created_at": {"$gte": start_date}
                })
                .sort("created_at", DESCENDING)
            )
            
            # Calculate trends
            total_analyses = len(analyses)
            total_tickets = sum(a.get('total_tickets_analyzed', 0) for a in analyses)
            total_clusters = sum(len(a.get('clusters', [])) for a in analyses)
            
            # Daily breakdown
            daily_data = {}
            for analysis in analyses:
                date_key = analysis.get('analysis_date', analysis['created_at'].strftime('%Y-%m-%d'))
                if date_key not in daily_data:
                    daily_data[date_key] = {
                        'tickets': 0,
                        'clusters': 0,
                        'analyses': 0
                    }
                daily_data[date_key]['tickets'] += analysis.get('total_tickets_analyzed', 0)
                daily_data[date_key]['clusters'] += len(analysis.get('clusters', []))
                daily_data[date_key]['analyses'] += 1
            
            # Top recurring issues
            cluster_frequency = {}
            for analysis in analyses:
                for cluster in analysis.get('clusters', []):
                    title = cluster.get('title', 'Unknown')
                    cluster_frequency[title] = cluster_frequency.get(title, 0) + 1
            
            top_issues = sorted(
                [{'title': k, 'count': v} for k, v in cluster_frequency.items()],
                key=lambda x: x['count'],
                reverse=True
            )[:10]
            
            return {
                'period_days': days,
                'total_analyses': total_analyses,
                'total_tickets': total_tickets,
                'total_clusters': total_clusters,
                'avg_tickets_per_analysis': round(total_tickets / total_analyses, 2) if total_analyses > 0 else 0,
                'avg_clusters_per_analysis': round(total_clusters / total_analyses, 2) if total_analyses > 0 else 0,
                'daily_breakdown': daily_data,
                'top_recurring_issues': top_issues
            }
            
        except Exception as e:
            logger.error(f"Error calculating trend data: {e}")
            return {}
    
    def get_dashboard_stats(self) -> Dict:
        """
        Get summary statistics for dashboard
        
        Returns:
            Dictionary with dashboard stats
        """
        try:
            # Latest analysis
            latest = self.analyses_collection.find_one(sort=[("created_at", DESCENDING)])
            
            # Today's analyses
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            today_count = self.analyses_collection.count_documents({
                "created_at": {"$gte": today_start}
            })
            
            # Total analyses
            total_analyses = self.analyses_collection.count_documents({})
            
            # Last 7 days ticket count
            week_ago = datetime.utcnow() - timedelta(days=7)
            week_analyses = list(self.analyses_collection.find({
                "created_at": {"$gte": week_ago}
            }))
            week_tickets = sum(a.get('total_tickets_analyzed', 0) for a in week_analyses)
            
            return {
                'latest_analysis': {
                    'date': latest.get('analysis_date') if latest else None,
                    'tickets': latest.get('total_tickets_analyzed', 0) if latest else 0,
                    'clusters': len(latest.get('clusters', [])) if latest else 0
                } if latest else None,
                'today_analyses': today_count,
                'total_analyses': total_analyses,
                'last_7_days_tickets': week_tickets
            }
            
        except Exception as e:
            logger.error(f"Error getting dashboard stats: {e}")
            return {}
    
    def close(self):
        """Close MongoDB connection"""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")
