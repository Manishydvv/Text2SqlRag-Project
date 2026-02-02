"""
RAGAS Evaluation Script
Evaluates the Multi-Source RAG + Text-to-SQL system using RAGAS metrics.
Runs test queries and measures faithfulness and answer relevancy.
"""

import json
import asyncio
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from datasets import Dataset
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy

from app.config import settings
from app.services.embedding_service import EmbeddingService
from app.services.vector_service import VectorService
from app.services.rag_service import RAGService
from app.services.sql_service import TextToSQLService
from app.services.router_service import QueryRouter


class RAGEvaluator:
    """Evaluates RAG system using RAGAS metrics."""

    def __init__(self):
        """Initialize evaluator and services."""
        self.test_queries_path = Path("tests/test_queries.json")
        self.results_path = Path("evaluation_results.json")

        # Initialize services
        self.embedding_service = None
        self.vector_service = None
        self.rag_service = None
        self.sql_service = None

        self._initialize_services()

    def _initialize_services(self):
        """Initialize RAG and SQL services if API keys are available."""
        try:
            if settings.OPENAI_API_KEY and settings.PINECONE_API_KEY:
                print("Initializing RAG services...")
                self.embedding_service = EmbeddingService()
                self.vector_service = VectorService()
                self.vector_service.connect_to_index()
                self.rag_service = RAGService()
                print("✓ RAG services initialized")
            else:
                print("WARNING: OpenAI/Pinecone API keys not configured.")
                print("Document RAG evaluation will be skipped.")
        except Exception as e:
            print(f"WARNING: Failed to initialize RAG services: {e}")

        try:
            if settings.DATABASE_URL and settings.OPENAI_API_KEY:
                print("Initializing SQL service...")
                self.sql_service = TextToSQLService()
                self.sql_service.complete_training()
                print("✓ SQL service initialized and trained")
            else:
                print("WARNING: DATABASE_URL not configured.")
                print("SQL evaluation will be skipped.")
        except Exception as e:
            print(f"WARNING: Failed to initialize SQL service: {e}")

    def load_test_queries(self) -> List[Dict[str, Any]]:
        """Load test queries from JSON file."""
        if not self.test_queries_path.exists():
            raise FileNotFoundError(f"Test queries file not found: {self.test_queries_path}")

        with open(self.test_queries_path, 'r') as f:
            data = json.load(f)

        return data['test_queries']

    async def run_query(self, test_query: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run a single test query through the system.

        Args:
            test_query: Test query dictionary with id, type, question, ground_truth

        Returns:
            Result dictionary with question, answer, contexts, ground_truth
        """
        query_type = test_query['type']
        question = test_query['question']
        ground_truth = test_query['ground_truth']

        result = {
            "query_id": test_query['id'],
            "question": question,
            "ground_truth": ground_truth,
            "query_type": query_type,
            "answer": None,
            "contexts": [],
            "error": None
        }

        try:
            # Route based on query type
            if query_type == "SQL":
                if not self.sql_service:
                    result['error'] = "SQL service not initialized"
                    result['answer'] = "N/A - SQL service unavailable"
                    return result

                # Generate and execute SQL
                sql_result = self.sql_service.generate_sql_for_approval(question)
                execution_result = self.sql_service.execute_approved_query(
                    sql_result['query_id'],
                    approved=True
                )

                # Format answer from SQL results
                answer_parts = [
                    f"SQL Query: {execution_result['sql']}",
                    f"Results: {json.dumps(execution_result['results'][:5])}",  # First 5 rows
                    f"Total rows: {execution_result['result_count']}"
                ]
                result['answer'] = "\n".join(answer_parts)
                result['contexts'] = [execution_result['sql']]  # SQL as context

            elif query_type == "DOCUMENTS":
                if not self.rag_service:
                    result['error'] = "RAG service not initialized"
                    result['answer'] = "N/A - RAG service unavailable"
                    return result

                # Query documents using RAG
                rag_result = await self.rag_service.generate_answer(
                    question=question,
                    top_k=3,
                    namespace="default",
                    include_sources=True
                )

                result['answer'] = rag_result['answer']
                result['contexts'] = [
                    chunk['text'] for chunk in rag_result.get('sources', [])
                ]

            elif query_type == "HYBRID":
                if not self.sql_service or not self.rag_service:
                    result['error'] = "Both SQL and RAG services required for HYBRID"
                    result['answer'] = "N/A - Services unavailable"
                    return result

                # Get SQL results
                sql_result = self.sql_service.generate_sql_for_approval(question)
                execution_result = self.sql_service.execute_approved_query(
                    sql_result['query_id'],
                    approved=True
                )

                # Get document context
                rag_result = await self.rag_service.generate_answer(
                    question=question,
                    top_k=3,
                    namespace="default",
                    include_sources=True
                )

                # Combine both
                answer_parts = [
                    f"SQL Results: {json.dumps(execution_result['results'][:5])}",
                    f"Context from Documents: {rag_result['answer']}"
                ]
                result['answer'] = "\n".join(answer_parts)
                result['contexts'] = [
                    execution_result['sql'],
                    *[chunk['text'] for chunk in rag_result.get('sources', [])]
                ]

        except Exception as e:
            result['error'] = str(e)
            result['answer'] = f"Error: {str(e)}"

        return result

    async def run_all_queries(self) -> List[Dict[str, Any]]:
        """Run all test queries and collect results."""
        test_queries = self.load_test_queries()
        results = []

        print(f"\nRunning {len(test_queries)} test queries...")
        print("=" * 60)

        for i, test_query in enumerate(test_queries, 1):
            print(f"\n[{i}/{len(test_queries)}] Running query: {test_query['id']}")
            print(f"Type: {test_query['type']}")
            print(f"Question: {test_query['question']}")

            result = await self.run_query(test_query)
            results.append(result)

            if result['error']:
                print(f"ERROR: {result['error']}")
            else:
                print(f"✓ Query completed")

        print("\n" + "=" * 60)
        return results

    def evaluate_with_ragas(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Evaluate results using RAGAS metrics.

        Args:
            results: List of query results

        Returns:
            Evaluation scores and metrics
        """
        # Filter out results with errors
        valid_results = [r for r in results if not r['error'] and r['answer'] != "N/A - Services unavailable"]

        if not valid_results:
            print("\nWARNING: No valid results to evaluate (services not initialized)")
            return {
                "error": "No valid results - services not initialized",
                "evaluated_queries": 0,
                "skipped_queries": len(results)
            }

        print(f"\nEvaluating {len(valid_results)} queries with RAGAS...")

        # Convert to RAGAS Dataset format
        dataset_dict = {
            "question": [r['question'] for r in valid_results],
            "answer": [r['answer'] for r in valid_results],
            "contexts": [r['contexts'] for r in valid_results],
            "ground_truth": [r['ground_truth'] for r in valid_results]
        }

        dataset = Dataset.from_dict(dataset_dict)

        # Evaluate with RAGAS metrics
        try:
            evaluation_result = evaluate(
                dataset,
                metrics=[faithfulness, answer_relevancy]
            )

            scores = {
                "faithfulness": float(evaluation_result['faithfulness']),
                "answer_relevancy": float(evaluation_result['answer_relevancy']),
                "evaluated_queries": len(valid_results),
                "skipped_queries": len(results) - len(valid_results)
            }

            print("\n" + "=" * 60)
            print("RAGAS Evaluation Results:")
            print("=" * 60)
            print(f"Faithfulness:      {scores['faithfulness']:.4f} (target: > 0.7)")
            print(f"Answer Relevancy:  {scores['answer_relevancy']:.4f} (target: > 0.8)")
            print(f"Evaluated Queries: {scores['evaluated_queries']}")
            print(f"Skipped Queries:   {scores['skipped_queries']}")
            print("=" * 60)

            return scores

        except Exception as e:
            print(f"\nERROR during RAGAS evaluation: {e}")
            return {
                "error": str(e),
                "evaluated_queries": 0,
                "skipped_queries": len(results)
            }

    def save_results(self, results: List[Dict[str, Any]], scores: Dict[str, Any]):
        """Save evaluation results to JSON file."""
        output = {
            "evaluation_date": datetime.utcnow().isoformat(),
            "total_queries": len(results),
            "ragas_scores": scores,
            "query_results": results,
            "summary": {
                "faithfulness_target": 0.7,
                "answer_relevancy_target": 0.8,
                "faithfulness_met": scores.get('faithfulness', 0) > 0.7,
                "answer_relevancy_met": scores.get('answer_relevancy', 0) > 0.8
            }
        }

        with open(self.results_path, 'w') as f:
            json.dump(output, f, indent=2)

        print(f"\n✓ Results saved to: {self.results_path}")

    async def run_evaluation(self):
        """Main evaluation workflow."""
        print("=" * 60)
        print("Starting RAGAS Evaluation")
        print("=" * 60)

        # Run all test queries
        results = await self.run_all_queries()

        # Evaluate with RAGAS
        scores = self.evaluate_with_ragas(results)

        # Save results
        self.save_results(results, scores)

        print("\n✓ Evaluation complete!")

        return scores


async def main():
    """Main entry point for evaluation script."""
    evaluator = RAGEvaluator()
    await evaluator.run_evaluation()


if __name__ == "__main__":
    asyncio.run(main())
