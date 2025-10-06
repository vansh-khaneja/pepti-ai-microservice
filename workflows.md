# Pepti Wiki AI - User Workflows Documentation

## Table of Contents
1. [System Overview](#system-overview)
2. [User Journey Workflows](#user-journey-workflows)
3. [Chatbot Decision Flows](#chatbot-decision-flows)
4. [Search & Discovery Workflows](#search--discovery-workflows)
5. [Technical Implementation Flows](#technical-implementation-flows)
6. [Error Handling & Fallbacks](#error-handling--fallbacks)

---

## System Overview

Pepti Wiki AI is an intelligent chatbot system that helps users find information about peptides through multiple pathways:
- **General Chatbot** - Answers any peptide-related questions
- **Peptide-Specific Chat** - Deep dive into specific peptides
- **Web Search Integration** - Finds latest information from the web
- **Similarity Recommendations** - Suggests related peptides

---

## User Journey Workflows

### 1. General Chatbot Workflow
**When user asks any peptide-related question:**

```
1. User asks: "What peptides help with muscle recovery?"
2. System generates embedding for the question
3. Search in Qdrant database for similar peptides
4. If found → Get best matching peptide
5. If not found → Trigger web search workflow
6. Generate AI response using found information
7. Apply chat restrictions (no medical advice, etc.)
8. Return response to user
9. Log interaction for analytics
```

**Example User Flow:**
- User: "What peptides help with muscle recovery?"
- System: Searches database → Finds BPC-157, TB-500 → Returns detailed info
- User: "Tell me more about BPC-157"
- System: Switches to peptide-specific workflow

### 2. Peptide-Specific Chat Workflow
**When user asks about a specific peptide:**

```
1. User asks: "Tell me about BPC-157"
2. Extract peptide name from query
3. Search Qdrant database for exact peptide match
4. If found → Get peptide details (overview, mechanism, research fields)
5. Generate AI response using peptide context
6. Apply chat restrictions
7. Return detailed peptide information
8. Log interaction
```

**Example User Flow:**
- User: "What is BPC-157?"
- System: Finds BPC-157 in database → Returns comprehensive overview
- User: "How does BPC-157 work?"
- System: Uses mechanism of action data → Explains working mechanism
- User: "What are similar peptides?"
- System: Triggers recommendation workflow

### 3. Web Search Fallback Workflow
**When database doesn't have the information:**

```
1. User asks about unknown peptide or topic
2. Database search returns no results
3. Trigger web search using SerpAPI
4. Scrape content from top search results
5. Break content into chunks
6. Generate embeddings for query and chunks
7. Calculate cosine similarity for each chunk
8. Filter chunks by confidence score (70%+)
9. Generate AI response from relevant chunks
10. Return response with source citations
11. Log web search interaction
```

**Example User Flow:**
- User: "Tell me about new peptide XYZ-123"
- System: Searches database → Not found
- System: Searches web → Finds research papers → Returns latest info
- User: "Is this peptide safe?"
- System: Applies restrictions → "I cannot provide medical advice"

### 4. Recommendation Workflow
**When user wants similar peptides:**

```
1. User asks: "What peptides are similar to BPC-157?"
2. Get BPC-157 from database
3. Extract BPC-157's embedding vector
4. Search for similar peptides using vector similarity
5. Filter out the original peptide
6. Return top 4 similar peptides with similarity scores
7. Log recommendation request
```

**Example User Flow:**
- User: "Show me peptides like BPC-157"
- System: Finds TB-500, Thymosin Alpha-1, etc. → Returns with similarity scores
- User: "Tell me about TB-500"
- System: Switches to peptide-specific workflow

---

## Chatbot Decision Flows

### 5. Smart Routing Decision Tree
**How the system decides which workflow to use:**

```
User Input → Analyze Query Type:

├── Contains specific peptide name (BPC-157, TB-500, etc.)
│   └── Route to: Peptide-Specific Chat Workflow
│
├── Asks for similar/recommended peptides
│   └── Route to: Recommendation Workflow
│
├── General peptide question (no specific peptide)
│   ├── Search database first
│   ├── If found → Use General Chatbot Workflow
│   └── If not found → Use Web Search Fallback Workflow
│
└── Unknown/ambiguous query
    └── Use General Chatbot Workflow with web search
```

### 6. Confidence Score Decision Flow
**How similarity scores determine response quality:**

```
Similarity Score → Action:

├── 0.8 - 1.0 (High Confidence)
│   └── Use database result directly
│
├── 0.6 - 0.8 (Medium Confidence)
│   └── Use database result + mention uncertainty
│
├── 0.4 - 0.6 (Low Confidence)
│   └── Use database result + suggest web search
│
└── 0.0 - 0.4 (Very Low Confidence)
    └── Trigger web search workflow
```

### 7. Chat Restrictions Decision Flow
**How the system applies safety restrictions:**

```
User Query → Check Restrictions:

├── Asks for medical advice/dosage
│   └── Apply restriction: "I cannot provide medical advice"
│
├── Asks for illegal/controlled substances
│   └── Apply restriction: "I cannot discuss illegal substances"
│
├── Asks for personal health recommendations
│   └── Apply restriction: "Consult a healthcare professional"
│
└── General information request
    └── Provide information normally
```

---

## Search & Discovery Workflows

### 8. Database Search Workflow
**How the system searches the peptide database:**

```
1. User query received
2. Generate embedding for query using OpenAI
3. Search Qdrant vector database using cosine similarity
4. Get top results with similarity scores
5. If similarity > 0.6 → Use database result
6. If similarity < 0.6 → Trigger web search
7. Return best matching peptide information
8. Log search results and performance
```

### 9. Web Search Integration Workflow
**When database search fails or needs additional info:**

```
1. Database search returns low confidence
2. Use SerpAPI to search web for peptide information
3. Scrape content from top 4 search results
4. Break content into 1000-character chunks
5. Generate embeddings for query and each chunk
6. Calculate cosine similarity for each chunk
7. Filter chunks with similarity > 70%
8. Group chunks by source URL
9. Use best similarity score per URL
10. Generate AI response from relevant chunks
11. Return response with source citations
```

### 10. Chunk Processing Workflow
**How web content is processed for relevance:**

```
1. Raw web content received
2. Clean HTML and extract text
3. Split into overlapping chunks (1000 chars, 200 overlap)
4. Limit to 5 chunks per website
5. Generate embedding for each chunk
6. Calculate cosine similarity with query
7. Sort chunks by similarity score
8. Group by parent URL
9. Select best chunk per URL
10. Pass to AI for response generation
```

---

## Technical Implementation Flows

### 11. AI Response Generation Workflow
**How the system generates intelligent responses:**

```
1. Context gathered (database or web search)
2. Get chat restrictions from database
3. Create prompt with:
   - System instructions
   - Context information
   - User query
   - Safety restrictions
4. Send to OpenAI GPT-4o-mini
5. Receive AI response
6. Clean and truncate response
7. Apply final safety checks
8. Return response to user
9. Log AI interaction
```

### 12. Embedding Generation Workflow
**How text is converted to vectors for similarity:**

```
1. Text input received (query or content)
2. Send to OpenAI text-embedding-3-small API
3. Receive 1536-dimensional vector
4. Truncate to 768 dimensions for Qdrant
5. Store or use for similarity calculation
6. Log embedding generation
```

### 13. Cosine Similarity Calculation
**How similarity between vectors is calculated:**

```
1. Two embedding vectors received
2. Convert to numpy arrays
3. Calculate dot product: A · B
4. Calculate vector norms: ||A|| and ||B||
5. Compute cosine similarity: (A · B) / (||A|| × ||B||)
6. Return similarity score (-1 to 1)
7. Log similarity calculation
```

---

## Error Handling & Fallbacks

### 14. Database Connection Failure
**What happens when database is unavailable:**

```
1. Database connection fails
2. Log error and continue
3. Disable analytics functionality
4. Show warning: "Analytics unavailable"
5. Continue with core functionality
6. Retry connection on next request
```

### 15. OpenAI API Failure
**When AI services are down:**

```
1. OpenAI API returns error
2. Log error details
3. Return fallback message: "AI service temporarily unavailable"
4. Suggest user try again later
5. Continue logging for monitoring
```

### 16. Web Search Failure
**When SerpAPI or web scraping fails:**

```
1. Web search fails
2. Log error details
3. Return message: "Unable to find latest information"
4. Suggest user check database results
5. Continue with available data
```

### 17. Low Confidence Results
**When similarity scores are too low:**

```
1. All similarity scores < 70%
2. Log low confidence warning
3. Return message: "Limited information available"
4. Suggest user refine their query
5. Provide best available results
```

---

## User Experience Flows

### 18. Complete User Journey Example
**Real conversation flow:**

```
User: "What peptides help with muscle recovery?"
System: Searches database → Finds BPC-157 (0.85 similarity)
Response: "BPC-157 is excellent for muscle recovery. It promotes tissue repair..."

User: "Tell me more about BPC-157"
System: Switches to peptide-specific workflow
Response: "BPC-157 (Body Protection Compound) is a synthetic peptide..."

User: "What are similar peptides?"
System: Triggers recommendation workflow
Response: "Similar peptides include TB-500 (0.78 similarity), Thymosin Alpha-1..."

User: "Tell me about TB-500"
System: Switches to peptide-specific workflow
Response: "TB-500 is a synthetic version of thymosin beta-4..."
```

### 19. Fallback User Journey
**When database doesn't have information:**

```
User: "Tell me about new peptide XYZ-123"
System: Searches database → Not found
System: Triggers web search → Finds research papers
Response: "Based on recent research, XYZ-123 appears to be..."

User: "Is it safe to use?"
System: Applies chat restrictions
Response: "I cannot provide medical advice. Please consult a healthcare professional."
```

### 20. Error Recovery Flow
**When something goes wrong:**

```
User: "What peptides help with sleep?"
System: Database search fails
System: Shows error message
Response: "I'm having trouble accessing the database right now. Please try again in a moment."

User: "What peptides help with sleep?" (retry)
System: Database search succeeds
Response: "Several peptides may help with sleep, including..."
```

---

## Summary

### Key Workflow Types in Pepti Wiki AI:

1. **General Chatbot** - Handles any peptide-related questions
2. **Peptide-Specific Chat** - Deep dive into known peptides  
3. **Web Search Fallback** - Finds latest information when database lacks data
4. **Recommendation Engine** - Suggests similar peptides
5. **Smart Routing** - Automatically chooses the right workflow
6. **Error Recovery** - Graceful handling of failures

### Decision Points:
- **Similarity Score > 0.6** → Use database result
- **Similarity Score < 0.6** → Trigger web search
- **Specific Peptide Name** → Peptide-specific workflow
- **"Similar peptides"** → Recommendation workflow
- **Medical/Safety Questions** → Apply restrictions

### User Experience:
- **Seamless transitions** between different workflows
- **Intelligent fallbacks** when services fail
- **Safety restrictions** prevent harmful advice
- **Source citations** for web-sourced information
- **Confidence indicators** show result quality

This chatbot system provides a comprehensive, intelligent, and safe way for users to discover and learn about peptides through multiple pathways, with robust error handling and user-friendly interactions.
