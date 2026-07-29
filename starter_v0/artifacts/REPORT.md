# Day 04 Lab v2 Report — Research Agent

## Team

- **Team:** Group02
- **Members:** Nguyễn Minh Hoàng - 2A202601609;
Nguyễn Duy Lâm - 2A202601073;
Lê Ngọc Khánh - 2A202601487;
Nguyễn Tuấn Anh - 2A202601775;
Lê Mạnh Cương - 2A202601137;
Vũ Ngọc Thiện - 2A202601793.
- **Provider / model đã chạy eval:** OpenRouter / `openai/gpt-4o-mini`
- **UI:** Streamlit (`app.py`)
- **Chạy local:** `streamlit run app.py`
- **Demo URL local:** `http://localhost:8501`
- **Public deployment/tunnel:** Chạy lệnh `cloudflared tunnel --url http://localhost:8501` để lấy link.

---

# PHẦN A — Giới thiệu agent

## A1. Agent này làm được gì

Nhóm xây dựng một **Research Agent** có khả năng định tuyến yêu cầu người dùng đến tool phù hợp để tìm kiếm web/news, tìm social posts, đọc URL, tra cứu company policy, tìm paper arXiv và định dạng kết quả.

CLI, evaluation và UI dùng chung `artifacts/system_prompt.md`, `artifacts/tools.yaml` và `run_model_tool_loop` trong `chat.py`. Streamlit UI hiển thị request/response, tool trace gồm tên tool, arguments, result/error và lưu transcript JSON.

Agent không được tự đoán URL, handle hoặc destination còn thiếu. Với yêu cầu gửi/publish, agent phải yêu cầu xác nhận rõ ràng trước khi gọi action tool.

## A2. Tool agent có

| Tên tool | Làm được gì | Tool mới nhóm thêm? |
|---|---|---|
| clarify | hỏi lại người dùng khi thiếu thông tin bắt buộc | không |
| timeline | lấy tweet từ 1 tài khoản cụ thể (phải có handle) | không |
| social_search | tìm bài đăng mạng xã hội theo từ khóa chủ đề | không |
| lookup | tìm tin tức, thông tin chung trên web | không |
| fetch | đọc nội dung của một url được cung cấp | không |
| format | định dạng kết quả sang dạng bullet, digest | không |
| send | xác nhận và đăng bài/gửi tin nhắn | không |
| policy | tra cứu các quy định, chính sách nội bộ công ty | không |
| papers | tìm các bài báo khoa học trên thư viện arxiv | không |
| paper_text | lấy toàn bộ text từ một bài báo arxiv | không |
| extract_keywords | trích xuất các từ khóa từ một đoạn văn bản người dùng cung cấp | CÓ (Tool bắt buộc) |

### Trạng thái tool mới `extract_keywords`

Nhóm đã có implementation và tài liệu tại:

- `tools/extract_keywords/tool.py`
- `tools/extract_keywords/TOOL.md`

Tool nhận `text`, `max_keywords`, `min_length` và trả về `keywords`, `keyword_count`, `token_count`.

## A3. Câu hỏi mẫu để thử

1. `Tìm tin AI hôm nay và tóm tắt các nguồn chính.`
2. `Mọi người nói gì về OpenAI trên Twitter?`
3. `Đọc và tóm tắt https://example.com`
4. `Tìm 2 paper arXiv về AI agent evaluation.`
5. `Gửi bản tin này lên Telegram.`

Với câu 5, kỳ vọng agent gọi `clarify(response_type="yes_no")` thay vì gửi ngay.

## A4. Kịch bản demo đã rehearse / cần rehearse

| Scenario | Tool trace cần thấy | Câu chuyện cải thiện version | Fallback run/transcript |
|---|---|---|---|
| Tìm tweet rồi đổi ý | timeline(sama) -> (User: À nhầm đổi sang karpathy) -> timeline(karpathy) | Ở v0 agent hay nhầm tham số hoặc không đổi tool. Đến v1 xử lý đa lượt chuẩn xác. | Transcript M03 |
| Hỏi đáp ngoài lề | Không có tool nào được gọi | Ở v0 agent cố lấy tool để tìm kiếm code. Ở v1 từ chối thẳng thừng. | Transcript R14 |
| Gửi tin nhắn cần xác nhận | clarify(yes_no) -> send() | Ở v0 agent send thẳng, v1 chặn lại phải qua clarify trước. | Transcript R12 |

---

# PHẦN B — Chi tiết / Bằng chứng

## B1. Version evidence

| Version | Prompt/tool change | Hypothesis | Metric name | Before | After | Run File |
|---|---|---|---|---:|---:|---|
| v0 | baseline | base eval | case_accuracy | 0.0 | 0.7 | v0_B_base_openrouter_20260729T103131938042.json |
| v1 | Sửa system_prompt.md: thêm instruction cấm đoán rõ ràng, yêu cầu clarify | Các rule mạnh và rõ hơn về ranh giới tool, đa lượt sẽ khắc phục các lỗi routing | case_accuracy | 0.7 | 1.0 | v1_B_base_openrouter_20260729T141859321157.json |

### Artifact versions

| Version | Case ID | What It Tests | Expected Tool/Behavior | Result |
|---|---|---|---|---|
| G01_extract_keywords | extract_keywords | Use of new extract_keywords tool | extract_keywords | PASS |
| G02_papers_routing | papers | Correctly route to papers tool | papers | PASS |
| G03_policy_routing | policy | Route to policy tool | policy | PASS |
| G04_out_of_scope_cooking | no_tool | Out of scope cooking | no_tool | PASS |
| G05_clarify_paper_text | clarify | Clarify missing arxiv_url | clarify | PASS |
| G06_correction_policy | policy | Multi-turn correction from arxiv to policy | policy | PASS |
| G07_switch_from_extract | social_search | Multi-turn switch from extract to social_search | social_search | PASS |
| G08_format_digest | format | Multi-turn format after lookup | format | PASS |
| G09_confirm_send | send | Multi-turn confirm before send | send | PASS |
| G10_parallel_papers_web | papers, lookup | Parallel tool calls | papers, lookup | PASS |

### Kết quả chính

- v1 tăng case accuracy lên 1.0.
- v2 có `provider_error_cases=0`, không có observed mismatch và không có `tool_results.error` trong run JSON.

## B2. Failure analysis

| Case ID | Failure Type | Actual Tool Calls | What Failed | Fix |
|---|---|---|---|---|
| R10_missing_handle | missing_info | timeline | Không gọi clarify khi thiếu handle | Sửa prompt: "Nếu thiếu thông tin bắt buộc, PHẢI gọi clarify" |
| M06_switch_tool | extra_tool_call | lookup, social_search | Gọi cả tool cũ khi user bảo đổi tool | Thêm rule "Hủy bỏ yêu cầu cũ nếu mâu thuẫn" vào system_prompt |

## B4. Live chat / UI evidence

Sau đó chạy và lưu tối thiểu ba tình huống: một research request bình thường, một request thiếu thông tin rồi user bổ sung ở lượt sau, và một action yêu cầu confirmation.

| Scenario/Turn | Version | Tool Calls + Args | Transcript/Run | Outcome |
|---|---|---|---|---|
| M03_correction_handle | v1 | timeline(karpathy) | R1 | PASS |
| G01_extract_keywords | v1 | extract_keywords(OpenAI o1) | R1 | PASS |

## B5. Tool capability evidence

| Category | Evidence File | What Worked | Risk / Guardrail |
|---|---|---|---|
| Must-have: tool mới đầu tiên | `extract_keywords/tool.py` | Trích xuất thành công keyword và đếm số lượng | text truyền vào quá dài, giới hạn từ |
| Optional built-in | `papers`, `policy` | Lấy đúng thông tin từ chính sách | None |
| Action tool | `tools/send/tool.py` | `confirmed=False` trả `status="needs_confirmation"`. | Không live-send trong eval; chỉ gửi private demo channel sau explicit confirmation. |
| UI core deliverable | `app.py`, `requirements.txt` | Streamlit đã được thêm vào requirements; code có trace/transcript path. | Cần UI smoke test và transcript thật. |

### Quicktest cho `extract_keywords`
PASS khi registry tìm thấy tool, `error` là `None`, và kết quả có keyword hợp lệ.

## B6. Reflection và next steps

### Phân chia thay đổi giữa prompt và tool declaration

- Which fixes belonged in `system_prompt.md`? Việc yêu cầu gọi `clarify`, cấm gọi timeline/social_search khi mâu thuẫn, quy tắc scope toán học/code.
- Which fixes belonged in `tools.yaml`? Khai báo format `extract_keywords` và parameters cần thiết.
- Which failure needed manual review instead of automatic grading? Các kết quả trả về văn bản dài hoặc cần logic phức tạp (VD: format template).
- What would you improve next? Bổ sung khả năng memory cho agent hoặc dùng Few-shot prompting mạnh hơn thay vì liệt kê rule chay.

### Kết quả v2 và hướng cải thiện v3

Research agent chuyên biệt, giúp tìm kiếm tin tức trên web, tổng hợp bài báo khoa học arxiv, lấy tweet mới nhất từ tài khoản cụ thể, tra cứu chính sách công ty và phân tích từ khóa.
