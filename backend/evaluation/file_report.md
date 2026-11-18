# File-handling report

20 files: 20 pass, 0 warn, 0 fail

| File | Status | Result | Detail |
|---|---|---|---|
| clean one-page PDF | 200 | PASS | 279 characters read |
| uppercase extension | 200 | PASS | 279 characters read |
| spaces and accents in file name | 200 | PASS | 279 characters read |
| two-column layout (interleaved) | 200 | PASS | 432 characters read |
| Canva-style design, normal headings | 200 | PASS | 475 characters read |
| Canva-style design, unusual headings | 200 | PASS | 496 characters read |
| long 3-page resume | 200 | PASS | 8128 characters read |
| Word resume (.docx) | 200 | PASS | 240 characters read |
| Word resume with a two-column table | 200 | PASS | 240 characters read |
| empty file | 422 | PASS | The uploaded file is empty. |
| random bytes named .pdf | 422 | PASS | This file is not a valid PDF. |
| truncated PDF (must not crash) | 200 | PASS | 122 characters read |
| password-protected PDF | 422 | PASS | Could not read this file. It may be corrupt or password-protected. |
| scanned PDF (image only) | 422 | PASS | Could not read text from this file. It may be a scanned image. |
| text file renamed .pdf | 422 | PASS | This file is not a valid PDF. |
| PNG image renamed .docx | 422 | PASS | This file is not a valid DOCX. |
| corrupt .docx | 422 | PASS | Could not read this file. It may be corrupt or password-protected. |
| plain text file (.txt) is supported | 200 | PASS | 449 characters read |
| unsupported type (.exe) | 415 | PASS | Only PDF, DOCX and TXT files are supported. |
| file over the size limit (6 MB) | 413 | PASS | File exceeds 5 MB limit. |
