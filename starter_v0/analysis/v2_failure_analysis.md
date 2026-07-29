# V2 Failure Analysis

## 1. Run được phân tích

- V2 run: `runs/v2_B_base_openrouter_20260729T114249985512.json`
- V1 run so sánh: `runs/v1_B_base_openrouter_20260729T112838983525.json`
- V0 baseline: `runs/v0_B_base_openrouter_20260729T110118551256.json`
- Provider: `openrouter`
- Model: `openai/gpt-4o-mini`
- Suite: `base`
- Version: `v2`
- Artifact version: `v2+p85aa5bd8fca4+t631b2950896f`
- Prompt hash: `85aa5bd8fca4c38f1388891904a304154a78e5af542c931faa4758fa0f6ab36f`
- Tools hash: `631b2950896fa2423a7e7fc4d20312426c9cca75f3f46ee9f8ddd24e965ee34b`

## 2. Gate validation

| Gate | Kết quả | Trạng thái |
|---|---:|---|
| Total cases | 20 | PASS |
| Measured cases | 20 | PASS |
| Provider error cases | 0 | PASS |
| Tool execution errors | 0 | PASS |

V2 là một run sạch: toàn bộ 20 case được đo, không có provider error và không có `tool_results` error.

## 3. So sánh metrics v0 → v1 → v2

| Metric | V0 | V1 | V2 | V1 → V2 |
|---|---:|---:|---:|---:|
| Passed cases | 14/20 | 18/20 | 20/20 | +2 case |
| Case accuracy | 0.70 | 0.90 | 1.00 | +0.10 |
| Tool routing accuracy | 0.75 | 0.95 | 1.00 | +0.05 |
| Argument accuracy | 0.70 | 0.90 | 1.00 | +0.10 |
| Multiturn accuracy | 1.00 | 0.6667 | 1.00 | +0.3333 |
| Provider error cases | 0 | 0 | 0 | Không đổi |
| Tool execution errors | 0 | 1 | 0 | -1 lỗi |

Kết luận metric:

- V2 sửa được cả hai regression multi-turn của v1.
- Multiturn accuracy phục hồi từ `0.6667` lên `1.00`.
- Không làm regression bất kỳ case nào đang PASS ở v1.
- Base suite đạt toàn bộ metric tự động bằng `1.00`.

## 4. Thay đổi artifact v1 → v2

V2 tập trung vào hypothesis multi-turn correction/switching.

Thay đổi chính trong `artifacts/system_prompt.md`:

- Lượt correction mới hơn ghi đè entity và source cũ.
- Khi user nói “bỏ”, “stop”, “skip” hoặc “switch away”, agent không được gọi lại source/tool cũ.
- Thêm canonical account mappings:
  - `Sam Altman` → `sama`
  - `Andrej Karpathy` → `karpathy`
- Thêm ví dụ chuyển từ Twitter sang web news chỉ được gọi `lookup`.

Thay đổi chính trong `artifacts/tools.yaml`:

- `timeline` nêu rõ correction phải dùng account mới nhất và thêm canonical handle mapping.
- `screenname` nêu rõ dùng `karpathy` cho Andrej Karpathy.
- `social_search` không được gọi nếu user đã chuyển khỏi Twitter/social sang web/news.

Đây là thay đổi có phạm vi tập trung và khớp với hai failure của v1.

## 5. Case transition v1 → v2

| Case | V1 | V2 | Transition | Evidence v2 |
|---|---|---|---|---|
| M03_correction_handle | FAIL | PASS | FIXED | `timeline(screenname="karpathy", limit=3)` |
| M06_switch_tool | FAIL | PASS | FIXED | Chỉ gọi `lookup(query="OpenAI", topic="news")` |

18 case còn lại giữ trạng thái PASS. Không có:

- `STILL_FAIL`
- regression
- unexpected tool call
- missing tool call
- wrong argument
- provider error
- tool execution error

## 6. Xác minh hypothesis v2

### 6.1. M03_correction_handle

Input:

```text
User: Tweet mới nhất của Sam Altman
User: À nhầm, của Andrej Karpathy
User: Lấy 3 tweet mới nhất nhé
```

Expected và actual ở v2:

```json
{
  "name": "timeline",
  "args": {
    "screenname": "karpathy",
    "limit": 3
  }
}
```

Kết quả:

- Corrected person được ưu tiên đúng.
- Canonical handle đúng.
- `limit=3` được carry over đúng.
- Tool thực thi thành công và trả ba tweet.
- `JSONDecodeError` của v1 không còn xuất hiện.

### 6.2. M06_switch_tool

Input:

```text
User: Mọi người nói gì về OpenAI trên Twitter?
User: Bỏ Twitter, chuyển sang tìm trên web tin tức đi
User: Giữ chủ đề OpenAI
```

Expected và actual ở v2:

```json
{
  "name": "lookup",
  "args": {
    "query": "OpenAI",
    "topic": "news"
  }
}
```

Kết quả:

- `OpenAI` được carry over đúng.
- Source Twitter đã bị hủy đúng theo instruction mới.
- Chỉ gọi `lookup`.
- Không còn extra `social_search`.
- Tool thực thi thành công.

Kết luận: hypothesis “later correction/replacement/cancellation must override older intent” được v2 evidence xác nhận.

## 7. Manual review ngoài automatic score

### 7.1. Không có tool execution error

Tất cả tool call trong v2 đều thực thi không có trường `error`.

Đặc biệt:

- M03 `timeline("karpathy", limit=3)` trả dữ liệu thành công.
- M06 chỉ thực thi `lookup`.
- Các case missing-info trả `awaiting_user=true`.
- Không có action `send` nào được thực hiện khi chưa xác nhận.

### 7.2. R14 vẫn có vấn đề semantic dù automatic PASS

R14 được automatic grader đánh dấu PASS vì agent không gọi tool. Tuy nhiên actual text vẫn cung cấp đầy đủ code Fibonacci:

```text
Yêu cầu của bạn nằm ngoài phạm vi hỗ trợ của tôi. Tuy nhiên, bạn có thể tham khảo đoạn mã sau...
```

Sau đó agent đưa ra toàn bộ implementation Python. Điều này mâu thuẫn với expected behavior `"refuse"` và với scope policy của agent.

Kết luận:

- Automatic routing score: PASS.
- Manual behavioral review: chưa đạt hoàn toàn.
- Đây là evidence phù hợp để tạo một cải tiến thật cho v3 dù base metric tự động đã đạt 1.00.

## 8. Đề xuất hypothesis cho v3

### Hypothesis

Scope rule hiện ngăn tool call ngoài phạm vi nhưng chưa ngăn model trả lời đầy đủ yêu cầu ngoài phạm vi bằng text, nên automatic grader PASS trong khi behavior thực tế vẫn vi phạm policy.

### Thay đổi đề xuất

Chỉ sửa `artifacts/system_prompt.md`:

- Với request ngoài phạm vi, trả lời từ chối ngắn gọn.
- Không cung cấp lời giải, code, nội dung sáng tạo hoặc hướng dẫn hoàn chỉnh sau câu từ chối.
- Có thể hướng user về một nguồn/phạm vi phù hợp, nhưng không thực hiện task ngoài scope.

### Acceptance criteria cho v3

- Base suite vẫn đạt 20/20.
- R14 không gọi tool và actual text không chứa implementation Fibonacci.
- R08 tiếp tục từ chối ngắn gọn, không giải bài toán.
- Không regression M03/M06.
- `provider_error_cases=0`.
- Không có `tool_results` error.
- Group eval được đo đủ 10 case sau khi artifact v3 được khóa.

## 9. Kiểm tra deliverable tool mới

Base v2 đạt 20/20 không chứng minh tool mới của Role 2 đã hoàn tất.

Hiện repo có:

```text
tools/extract_keywords/TOOL.md
tools/extract_keywords/tool.py
```

Nhưng chưa tìm thấy `extract_keywords` trong:

- `tools/__init__.py`
- `artifacts/tools.yaml`

Do đó tool mới hiện chưa được model nhìn thấy và chưa thể được gọi qua agent registry.

Role 2 cần:

1. Đăng ký implementation trong `TOOL_FUNCTIONS`.
2. Thêm declaration/schema vào `artifacts/tools.yaml`.
3. Phối hợp Role 1 thêm routing rule phù hợp.
4. Chạy smoke test trực tiếp.
5. Phối hợp Role 4 thêm group eval case nếu nhóm muốn đo routing của tool mới.

Không được dùng điểm 20/20 của base v2 làm bằng chứng rằng tool mới đã PASS.

## 10. Git evidence check

Run v2 hiện đang bị `.gitignore` bỏ qua vì có rule:

```gitignore
runs/
```

Trước khi handoff/nộp bài, Role 4 cần bảo đảm file sau được Git track:

```text
runs/v2_B_base_openrouter_20260729T114249985512.json
```

Có thể force-add file hoặc sửa `.gitignore` để `runs/*.json` và `transcripts/*.transcript.json` được commit.

## 11. Handoff

### Gửi Role 1

V2 đạt 20/20 và sửa đúng M03/M06 mà không có regression. Hypothesis multi-turn correction/switching được xác nhận. Đề xuất v3 xử lý semantic out-of-scope refusal ở R14: không chỉ tránh tool call mà còn không cung cấp code/lời giải ngoài phạm vi.

### Gửi Role 2

Không có tool execution error trong v2. Tuy nhiên `extract_keywords` mới chỉ có `TOOL.md` và `tool.py`; chưa đăng ký registry/declaration nên chưa hoàn thành contract tool mới.

### Gửi Role 4

V2 run sạch và đủ evidence metrics, nhưng file run đang bị Git ignore. Cần track/push file v2. Sau khi v3 được khóa, chạy cả base suite và group suite.

### Gửi Role 6

Dùng mục 3–8 cho Report B1/B2. V2 có automatic metrics hoàn hảo, nhưng manual review R14 là bằng chứng quan trọng cho cải tiến v3. Evidence:

- `runs/v1_B_base_openrouter_20260729T112838983525.json`
- `runs/v2_B_base_openrouter_20260729T114249985512.json`

