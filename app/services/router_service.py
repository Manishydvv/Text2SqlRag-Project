"""
Query Router Service
Determines whether a query should be routed to SQL, Documents, or both (HYBRID).
Uses keyword-based classification for intelligent routing.
"""

from typing import Literal


QueryType = Literal["SQL", "DOCUMENTS", "HYBRID"]


class QueryRouter:
    """
    Simple rule-based router for classifying queries.
    Determines whether to use Text-to-SQL, Document RAG, or both.
    """

    # Keywords that indicate a SQL/database query
    SQL_KEYWORDS = [
        # Aggregation keywords
        'how many', 'count', 'total', 'sum', 'average', 'avg', 'mean',
        'maximum', 'max', 'minimum', 'min', 'highest', 'lowest',

        # List/retrieval keywords
        'list all', 'show all', 'find all', 'get all', 'display all',
        'list', 'show', 'find', 'get', 'display',

        # Data-specific keywords
        'revenue', 'sales', 'orders', 'customers', 'products', 'order',
        'customer', 'product', 'price', 'cost', 'amount', 'quantity',

        # Time-based keywords
        'last', 'recent', 'past', 'previous', 'this month', 'this year',
        'today', 'yesterday', 'week', 'month', 'year',

        # Comparison keywords
        'more than', 'less than', 'greater than', 'top', 'bottom',
        'rank', 'ranking', 'best', 'worst',

        # Group/segment keywords
        'by segment', 'by category', 'by status', 'group by', 'per',
        'each', 'every',

        # Database-specific terms
        'database', 'table', 'record', 'row', 'data',
    ]

    # Keywords that indicate a document/knowledge query
    DOCUMENT_KEYWORDS = [
        # Information keywords
        'what is', 'what are', 'define', 'definition', 'explain',
        'describe', 'tell me about', 'information about',

        # Policy/procedure keywords
        'policy', 'policies', 'procedure', 'procedures', 'process',
        'guideline', 'guidelines', 'rule', 'rules', 'regulation',

        # Documentation keywords
        'guide', 'manual', 'handbook', 'documentation', 'document',
        'reference', 'instruction', 'instructions',

        # Question keywords
        'how to', 'how do', 'how can', 'how should', 'why',
        'when should', 'where can', 'who should',

        # Context keywords
        'according to', 'based on', 'mentioned in', 'stated in',
        'document says', 'documentation states',

        # Understanding keywords
        'understand', 'clarify', 'elaborate', 'detail', 'overview',
        'summary', 'summarize',
    ]

    # Keywords that suggest both SQL and documents might be needed
    HYBRID_KEYWORDS = [
        # Combined requests
        'and explain', 'and describe', 'and tell me',
        'also explain', 'also describe', 'also tell me',

        # Context + data keywords
        'sales and policy', 'revenue and guideline', 'data and procedure',
        'show data and explain', 'list and describe',

        # Comparison with context
        'compare and explain', 'analyze and describe',
    ]

    @staticmethod
    def route(question: str) -> QueryType:
        """
        Determine the appropriate route for a query.

        Args:
            question: The user's natural language question

        Returns:
            QueryType: 'SQL', 'DOCUMENTS', or 'HYBRID'

        Examples:
            >>> QueryRouter.route("How many customers do we have?")
            'SQL'
            >>> QueryRouter.route("What is our return policy?")
            'DOCUMENTS'
            >>> QueryRouter.route("Show total sales and explain our pricing strategy")
            'HYBRID'
        """
        # Normalize question to lowercase for matching
        question_lower = question.lower()

        # Check for hybrid keywords first (most specific)
        has_hybrid_keywords = any(
            keyword in question_lower
            for keyword in QueryRouter.HYBRID_KEYWORDS
        )

        # Check for SQL keywords
        has_sql_keywords = any(
            keyword in question_lower
            for keyword in QueryRouter.SQL_KEYWORDS
        )

        # Check for document keywords
        has_doc_keywords = any(
            keyword in question_lower
            for keyword in QueryRouter.DOCUMENT_KEYWORDS
        )

        # Routing logic
        if has_hybrid_keywords or (has_sql_keywords and has_doc_keywords):
            return "HYBRID"
        elif has_sql_keywords:
            return "SQL"
        elif has_doc_keywords:
            return "DOCUMENTS"
        else:
            # Default to documents for ambiguous queries
            # (safer than running SQL on unclear intent)
            return "DOCUMENTS"

    @staticmethod
    def get_routing_confidence(question: str) -> dict:
        """
        Get confidence scores for each routing option.
        Useful for debugging and understanding routing decisions.

        Args:
            question: The user's natural language question

        Returns:
            Dictionary with scores for SQL, DOCUMENTS, and HYBRID,
            plus the final routing decision
        """
        question_lower = question.lower()

        # Count matching keywords for each category
        sql_matches = sum(
            1 for keyword in QueryRouter.SQL_KEYWORDS
            if keyword in question_lower
        )

        doc_matches = sum(
            1 for keyword in QueryRouter.DOCUMENT_KEYWORDS
            if keyword in question_lower
        )

        hybrid_matches = sum(
            1 for keyword in QueryRouter.HYBRID_KEYWORDS
            if keyword in question_lower
        )

        # Calculate confidence scores (0-1 range)
        total_matches = max(sql_matches + doc_matches + hybrid_matches, 1)

        sql_confidence = sql_matches / total_matches
        doc_confidence = doc_matches / total_matches
        hybrid_confidence = hybrid_matches / total_matches

        # Get routing decision
        route_decision = QueryRouter.route(question)

        return {
            "question": question,
            "route": route_decision,
            "confidence_scores": {
                "sql": round(sql_confidence, 3),
                "documents": round(doc_confidence, 3),
                "hybrid": round(hybrid_confidence, 3)
            },
            "keyword_matches": {
                "sql_keywords": sql_matches,
                "document_keywords": doc_matches,
                "hybrid_keywords": hybrid_matches
            }
        }

    @staticmethod
    def explain_routing(question: str) -> str:
        """
        Provide a human-readable explanation of why a question
        was routed to a particular destination.

        Args:
            question: The user's natural language question

        Returns:
            Explanation string
        """
        route = QueryRouter.route(question)
        confidence = QueryRouter.get_routing_confidence(question)

        explanation = f"Question routed to: {route}\n\n"
        explanation += f"Keyword matches:\n"
        explanation += f"- SQL keywords: {confidence['keyword_matches']['sql_keywords']}\n"
        explanation += f"- Document keywords: {confidence['keyword_matches']['document_keywords']}\n"
        explanation += f"- Hybrid keywords: {confidence['keyword_matches']['hybrid_keywords']}\n"

        if route == "SQL":
            explanation += "\nThis appears to be a data/analytics query about the database."
        elif route == "DOCUMENTS":
            explanation += "\nThis appears to be a knowledge/information query about documentation."
        else:
            explanation += "\nThis appears to require both data retrieval and contextual information."

        return explanation
