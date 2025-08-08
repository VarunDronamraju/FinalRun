#!/bin/bash

echo "=== TESTING PHASES 9 & 10 INTEGRATION ==="
echo ""

BASE_URL="http://localhost:8000/api/v1"

# Test 1: Check capabilities
echo "1. Testing search capabilities..."
curl -s "$BASE_URL/search/capabilities" | python -m json.tool
echo ""
echo ""

# Test 2: Upload document for testing
echo "2. Uploading test document..."
UPLOAD_RESPONSE=$(curl -s -X POST "$BASE_URL/documents/upload" \
  -H "Content-Type: multipart/form-data" \
  -F "file=@requirements.txt")

DOC_ID=$(echo $UPLOAD_RESPONSE | python -c "import sys, json; print(json.load(sys.stdin)['id'])")
echo "Document ID: $DOC_ID"
echo ""

# Test 3: Process document
echo "3. Processing document into chunks..."
curl -s -X POST "$BASE_URL/documents/$DOC_ID/process" \
  -H "Content-Type: application/json" \
  -d '{"chunk_size": 500}' | python -m json.tool
echo ""
echo ""

# Test 4: Generate embeddings
echo "4. Generating embeddings..."
curl -s -X POST "$BASE_URL/documents/$DOC_ID/embeddings" | python -m json.tool
echo ""
echo ""

# Test 5: Store in vector database
echo "5. Storing in vector database..."
curl -s -X POST "$BASE_URL/documents/$DOC_ID/store" | python -m json.tool
echo ""
echo ""

# Test 6: Test local semantic search
echo "6. Testing local semantic search..."
curl -s -X POST "$BASE_URL/search/semantic" \
  -H "Content-Type: application/json" \
  -d '{"query": "fastapi framework", "limit": 3}' | python -m json.tool
echo ""
echo ""

# Test 7: Test web search (if available)
echo "7. Testing web search..."
curl -s -X POST "$BASE_URL/search/web" \
  -H "Content-Type: application/json" \
  -d '{"query": "Python web frameworks 2025", "max_results": 2}' | python -m json.tool
echo ""
echo ""

# Test 8: Test RAG with fallback
echo "8. Testing RAG with fallback..."
curl -s -X POST "$BASE_URL/rag/answer-with-fallback" \
  -H "Content-Type: application/json" \
  -d '{"query": "what are the latest Python features in 2025?", "use_fallback": true}' | python -m json.tool
echo ""
echo ""

# Test 9: Test database persistence - list documents
echo "9. Testing database persistence - list documents..."
curl -s "$BASE_URL/documents" | python -m json.tool
echo ""
echo ""

# Test 10: Test LLM status
echo "10. Testing LLM status..."
curl -s "$BASE_URL/llm/status" | python -m json.tool
echo ""

echo "=== TESTING COMPLETE ==="