# Security Notes

## Known Vulnerabilities

### pdfminer.six - Insecure Deserialization (pickle) in CMap Loader

**Severity:** Moderate  
**Version Affected:** <= 20251107 (currently using 20251107)  
**Status:** No patch available as of 2025-12-18

#### Description
The pdfminer.six library has a vulnerability related to insecure deserialization (pickle) in the CMap loader component, which could lead to local privilege escalation.

#### Impact on This Application
The risk to this application is **LOW** because:

1. **Optional Dependency**: pdfminer.six is used as an optional fallback for PDF text extraction, wrapped in a try/except block
2. **Limited Usage**: Only used via the high-level `extract_text()` function for extracting text from user-uploaded PDFs
3. **Fallback Available**: If pdfminer.six fails or is unavailable, the application falls back to pypdf for PDF parsing
4. **No Direct CMap Manipulation**: The application does not directly interact with CMap loading functionality

#### Mitigation
- The vulnerability requires loading malicious CMap files, which is not part of normal PDF text extraction workflows
- The application processes user-uploaded files in a sandboxed manner
- Consider the following additional mitigations:
  1. Remove pdfminer.six from requirements.txt and rely solely on pypdf (less feature-rich but secure)
  2. Monitor for security updates to pdfminer.six
  3. Implement additional input validation on uploaded PDF files

#### Recommendation
Monitor the pdfminer.six project for security updates. If a patched version becomes available, update immediately. In the meantime, the risk is acceptable given the limited usage and available fallback.

## Security Best Practices Implemented

1. **Input Sanitization**: All user inputs are sanitized using regex patterns to remove potentially harmful content
2. **Union/Non-Union Language Filtering**: Banned terms are filtered from generated content
3. **File Size Limits**: Streamlit's default file upload limits apply
4. **No External API Calls**: Application operates entirely in-browser with no external API dependencies
5. **DOCX Template Security**: Templates use docxtpl with safe context rendering

## Last Reviewed
2025-12-18
