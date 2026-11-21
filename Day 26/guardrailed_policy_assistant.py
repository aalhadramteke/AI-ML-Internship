import re
from typing import Dict, Tuple

# STAGE 1: VERIFIED KNOWLEDGE STORE
VERIFIED_POLICIES: Dict[str, str] = {
    "remote_work": (
        "Employees are permitted to work remotely up to 2 days per week "
        "with prior manager approval. Remote work equipment allowances are capped "
        "at $500 for home office setup."
    ),
    "paid_time_off": (
        "Full-time employees accrue 15 days of Paid Time Off (PTO) per calendar year. "
        "A maximum of 5 unused PTO days may be carried over into the following year."
    ),
    "expense_reimbursement": (
        "Travel expenses must be submitted within 30 days of the expense date. "
        "Meals during business travel are reimbursed up to a maximum daily limit of $75. "
        "Itemized receipts are required for all transactions exceeding $25."
    ),
}

UNAUTHORIZED_PATTERNS = [
    r"\bguarantee\b",
    r"\bunlimited\b",
    r"\blegal obligation\b",
    r"\bpromise\b",
    r"\b100% reimbursement\b",
]

# STAGE 2: INPUT PII SANITIZATION
def redact_pii(text: str) -> Tuple[str, bool]:
    pii_patterns = {
        "[REDACTED_SSN]": r"\b\d{3}-\d{2}-\d{4}\b",
        "[REDACTED_EMAIL]": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "[REDACTED_CREDIT_CARD]": r"\b(?:\d[ -]*?){13,16}\b",
    }
    redacted_text = text
    pii_detected = False
    for replacement, pattern in pii_patterns.items():
        if re.search(pattern, redacted_text):
            pii_detected = True
            redacted_text = re.sub(pattern, replacement, redacted_text)
    return redacted_text, pii_detected

# STAGE 3: GROUNDED ABSTENTION PROMPTING
def build_grounded_prompt(sanitized_query: str, context_dict: Dict[str, str]) -> str:
    context_str = "\n".join([f"- {k}: {v}" for k, v in context_dict.items()])
    return (
        "SYSTEM INSTRUCTION:\n"
        "Answer queries strictly using the VERIFIED KNOWLEDGE CONTEXT below.\n"
        "If the query cannot be answered from the context, respond with:\n"
        "'I am sorry, but I do not have access to information regarding that request in my verified policy knowledge base.'\n\n"
        f"VERIFIED KNOWLEDGE CONTEXT:\n{context_str}\n\n"
        f"USER QUERY:\n{sanitized_query}\n\nANSWER:"
    )

# STAGE 4: POST-GENERATION OUTPUT VALIDATION
def verify_response(llm_response: str) -> Tuple[str, bool]:
    for pattern in UNAUTHORIZED_PATTERNS:
        if re.search(pattern, llm_response, re.IGNORECASE):
            return (
                "SECURITY GUARDRAIL TRIGGERED: Unauthorized policy commitment intercepted. Escalating to human agent.",
                False,
            )
    _, pii_found = redact_pii(llm_response)
    if pii_found:
        return "SECURITY GUARDRAIL TRIGGERED: Potential PII detected in output. Response blocked.", False
    return llm_response, True
