"""
Grounding Service — verificação de que respostas estão fundamentadas em citações.

Implementa os controles de grounding da Fase 2:
- Verificação de citação: cada claim da resposta tem citação?
- Coverage: quanto do texto da resposta está citado?
- Flagging: respostas sem citação são marcadas

Ref: 0016-backlog-priorizado.md (P2 - Grounding controls)
     0011-contratos-de-avaliacao.md (Contrato 3: Grounded Answer)
"""
import re
from typing import Optional
from models.schemas import Citation


# Frases que indicam claims factuais (precisam de citação)
FACTUAL_PATTERNS = [
    r"\d+ (dias|horas|minutos|segundos|meses|anos)",
    r"R\$\s*[\d.,]+",
    r"\d+[%º°]",
    r"(taxa|tarifa|prazo|valor|montante|percentual)",
    r"(aprovado|rejeitado|bloqueado|processado)",
    r"(válido|expirado|cancelado|ativo|inativo)",
    r"https?://",
    r"\d{2}/\d{2}/\d{4}",
]

# Frases que NÃO são claims (não precisam de citação)
NON_CLAIM_PATTERNS = [
    r"^blé$",
    r"não sei",
    r"não tenho",
    r"informação suficiente",
    r"não consigo",
    r"não tenho certeza",
    r"vou verificar",
    r"pode ser que",
    r"talvez",
    r"é possível que",
]


def is_factual_claim(sentence: str) -> bool:
    """Check if a sentence contains factual claims that need citation."""
    sentence_lower = sentence.lower().strip()

    # Check non-claim patterns first
    for pattern in NON_CLAIM_PATTERNS:
        if re.search(pattern, sentence_lower, re.IGNORECASE):
            return False

    # Check factual patterns
    for pattern in FACTUAL_PATTERNS:
        if re.search(pattern, sentence, re.IGNORECASE):
            return True

    # Most declarative answer sentences still require grounding even without
    # explicit numbers or percentages.
    content_tokens = re.findall(r"\b[\wÀ-ÿ]{3,}\b", sentence_lower)
    return len(content_tokens) >= 2


def calculate_citation_coverage(
    answer: str,
    citations: list[Citation]
) -> float:
    """
    Calculate what fraction of the answer text is covered by citations.

    Returns a value between 0.0 and 1.0.
    """
    if not answer or not citations:
        return 0.0

    # Simple approach: check if key factual phrases from answer
    # appear in any citation text
    answer_lower = answer.lower()

    # Split answer into sentences
    sentences = re.split(r"[.!?]\s+", answer)
    cited_sentences = 0

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        # If this sentence has factual claims, check if it's cited
        if is_factual_claim(sentence):
            # Check if any citation covers this sentence
            sentence_cited = False
            for citation in citations:
                citation_text_lower = citation.text.lower()
                citation_text = citation.text

                # Check word overlap
                words = set(re.findall(r"\b\w{4,}\b", sentence.lower()))
                citation_words = set(re.findall(r"\b\w{4,}\b", citation_text_lower))
                overlap = words & citation_words

                # Also check for number/percentage overlap (for short claims like "1,99%")
                numbers_in_sentence = set(re.findall(r"[\d,.]+", sentence))
                numbers_in_citation = set(re.findall(r"[\d,.]+", citation_text))
                number_overlap = numbers_in_sentence & numbers_in_citation

                # Citation covers sentence if:
                # - 3+ word overlap, OR
                # - 1+ word overlap AND 1+ number overlap (for short factual claims)
                if len(overlap) >= 3:
                    sentence_cited = True
                elif len(overlap) >= 1 and len(number_overlap) >= 1:
                    sentence_cited = True
                elif _sentence_contains_context(citation_text, sentence):
                    # Check if key context words appear
                    sentence_cited = True

            if sentence_cited:
                cited_sentences += 1

    total_sentences = len([s for s in sentences if s.strip()])
    if total_sentences == 0:
        return 1.0  # No sentences to cite

    return cited_sentences / total_sentences


def _sentence_contains_context(citation_text: str, sentence: str) -> bool:
    """
    Check if the citation text contains enough context from the sentence.
    Used for short factual claims where word overlap is minimal.
    """
    citation_lower = citation_text.lower()
    sentence_lower = sentence.lower()

    # Extract key context words (exclude common stopwords)
    stopwords = {'a', 'o', 'é', 'de', 'da', 'do', 'em', 'para', 'com', 'um', 'uma', 'que', 'e', 'os', 'as', 'no', 'na', 'nos', 'nas'}
    words = [w for w in re.findall(r"\b\w{4,}\b", sentence_lower) if w not in stopwords]

    # Check if at least 2 key words appear in citation
    key_words_found = sum(1 for w in words if w in citation_lower)
    return key_words_found >= 2


def verify_grounding(
    answer: str,
    citations: list[Citation],
    threshold: float = 0.8
) -> dict:
    """
    Verify that an answer is properly grounded in citations.

    Returns a dict with:
    - grounded: bool (True if coverage >= threshold)
    - citation_coverage: float (0.0-1.0)
    - uncited_claims: list of sentences without citation
    - needs_review: bool (True if grounded=False)
    """
    if not answer:
        return {
            "grounded": False,
            "citation_coverage": 0.0,
            "uncited_claims": [],
            "needs_review": True,
            "reason": "Empty answer"
        }

    if not citations:
        return {
            "grounded": False,
            "citation_coverage": 0.0,
            "uncited_claims": [answer],
            "needs_review": True,
            "reason": "No citations provided"
        }

    # Calculate coverage
    coverage = calculate_citation_coverage(answer, citations)

    # Find uncited factual claims
    sentences = re.split(r"[.!?]\s+", answer)
    uncited = []

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue

        if is_factual_claim(sentence):
            # Check if this sentence is covered by any citation
            is_cited = False
            for citation in citations:
                citation_text_lower = citation.text.lower()

                words = set(re.findall(r"\b\w{4,}\b", sentence.lower()))
                citation_words = set(re.findall(r"\b\w{4,}\b", citation_text_lower))
                overlap = words & citation_words

                # Also check number overlap
                numbers_in_sentence = set(re.findall(r"[\d,.]+", sentence))
                numbers_in_citation = set(re.findall(r"[\d,.]+", citation.text))
                number_overlap = numbers_in_sentence & numbers_in_citation

                if len(overlap) >= 3:
                    is_cited = True
                elif len(overlap) >= 1 and len(number_overlap) >= 1:
                    is_cited = True
                elif _sentence_contains_context(citation.text, sentence):
                    is_cited = True

            if not is_cited:
                uncited.append(sentence)

    grounded = coverage >= threshold

    return {
        "grounded": grounded,
        "citation_coverage": round(coverage, 3),
        "uncited_claims": uncited,
        "needs_review": not grounded,
        "reason": None if grounded else f"Citation coverage {coverage:.0%} < {threshold:.0%}"
    }


def enrich_citations_with_filename(
    citations: list[Citation],
    document_metadata: dict[str, str]
) -> list[Citation]:
    """
    Enrich citations with document filenames from metadata.

    Args:
        citations: List of Citation objects
        document_metadata: Dict mapping document_id -> filename

    Returns:
        Citations with document_filename populated
    """
    enriched = []
    for citation in citations:
        if citation.document_id and citation.document_id in document_metadata:
            citation.document_filename = document_metadata[citation.document_id]
        enriched.append(citation)
    return enriched
